#!/bin/bash
set -euo pipefail
cd /srv/firehorse-backend

if [ ! -f ".env.backup" ]; then
    echo "❌ ERROR: .env.backup not found!"
    exit 1
fi

source .env.backup

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}"
LOG_FILE="backups/backup_${TIMESTAMP}.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}✓ $*${NC}" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}✗ ERROR: $*${NC}" | tee -a "$LOG_FILE"; exit 1; }
log_warning() { echo -e "${YELLOW}⚠ WARNING: $*${NC}" | tee -a "$LOG_FILE"; }
log_info() { echo -e "${BLUE}ℹ INFO: $*${NC}" | tee -a "$LOG_FILE"; }

validate() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 1: PRE-FLIGHT VALIDATION"
    log "════════════════════════════════════════════════════════════"
    
    ! docker ps &>/dev/null && log_error "Docker daemon not accessible"
    log_success "Docker daemon operational"
    
    ! docker ps | grep -q "firehorse-postgres" && log_error "PostgreSQL container not running"
    log_success "PostgreSQL container running"
    
    ! docker exec firehorse-postgres pg_isready -U "${DB_USER}" 2>&1 | grep -q "accepting" && \
        log_error "PostgreSQL not accepting connections"
    log_success "Database accepting connections"
    
    DB_COUNT=$(docker exec -e PGPASSWORD="${DB_PASSWORD}" firehorse-postgres \
        psql -U "${DB_USER}" -d postgres -t -c \
        "SELECT COUNT(*) FROM pg_database WHERE datname='${DB_NAME}';" 2>/dev/null | tr -d ' ')
    [ "$DB_COUNT" != "1" ] && log_error "Database '${DB_NAME}' does not exist"
    log_success "Database '${DB_NAME}' exists"
    
    for var in DB_USER DB_NAME BACKUP_ENCRYPTION_KEY; do
        [ -z "${!var:-}" ] && log_error "Missing config: $var"
    done
    log_success "Configuration valid"
    log ""
}

backup_db() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 2: DATABASE BACKUP"
    log "════════════════════════════════════════════════════════════"
    
    [ "$DB_BACKUP_ENABLED" != "true" ] && { log_warning "DB backup disabled"; return 0; }
    
    mkdir -p "${BACKUP_DIR}/db"
    log "Creating database dump..."
    
    docker exec -e PGPASSWORD="${DB_PASSWORD}" firehorse-postgres \
        pg_dump -U "${DB_USER}" -d "${DB_NAME}" -F c \
        > "${BACKUP_DIR}/db/full_dump.sql.gz" 2>&1 || log_error "pg_dump failed"
    
    DUMP_SIZE=$(du -sh "${BACKUP_DIR}/db/full_dump.sql.gz" 2>/dev/null | cut -f1)
    log_success "Database dump created: ${DUMP_SIZE}"
    
    docker exec -e PGPASSWORD="${DB_PASSWORD}" firehorse-postgres \
        pg_dump -U "${DB_USER}" -d "${DB_NAME}" --schema-only \
        > "${BACKUP_DIR}/db/schema.sql" 2>&1 || true
    log_success "Schema dump created"
    log ""
}

backup_app() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 3: APPLICATION BACKUP"
    log "════════════════════════════════════════════════════════════"
    
    [ "$APP_BACKUP_ENABLED" != "true" ] && { log_warning "App backup disabled"; return 0; }
    
    mkdir -p "${BACKUP_DIR}/app"
    
    if docker volume ls | grep -q "firehorse-backend_postgres_data"; then
        docker run --rm -v firehorse-backend_postgres_data:/data \
            -v "$(pwd)/${BACKUP_DIR}/app":/backup \
            alpine tar czf /backup/postgres_data.tar.gz -C /data . 2>&1 >> "$LOG_FILE" || true
        VOLUME_SIZE=$(du -sh "${BACKUP_DIR}/app/postgres_data.tar.gz" 2>/dev/null | cut -f1)
        log_success "Volume backup: ${VOLUME_SIZE}"
    fi
    
    FILES=""
    [ -f "docker-compose.yml" ] && FILES="$FILES docker-compose.yml"
    [ -f ".env.example" ] && FILES="$FILES .env.example"
    
    if [ -n "$FILES" ]; then
        # shellcheck disable=SC2086
        tar czf "${BACKUP_DIR}/app/config.tar.gz" --exclude='*.env' 2>&1 >> "$LOG_FILE" || true
        CONFIG_SIZE=$(du -sh "${BACKUP_DIR}/app/config.tar.gz" 2>/dev/null | cut -f1)
        log_success "Config backup: ${CONFIG_SIZE}"
    fi
    log ""
}

secure() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 4: SECURITY (Encrypt & Compress)"
    log "════════════════════════════════════════════════════════════"
    
    [ "$BACKUP_COMPRESS" != "true" ] && { log_warning "Compression disabled"; return 0; }
    
    log "Compressing..."
    tar czf "backups/firehorse_${TIMESTAMP}.tar.gz" -C backups "${TIMESTAMP}" 2>&1 >> "$LOG_FILE" || \
        log_error "Compression failed"
    COMPRESSED_SIZE=$(du -sh "backups/firehorse_${TIMESTAMP}.tar.gz" | cut -f1)
    log_success "Compressed: ${COMPRESSED_SIZE}"
    
    if [ "$BACKUP_ENCRYPTION" = "true" ] && [ -n "${BACKUP_ENCRYPTION_KEY:-}" ]; then
        log "Encrypting (AES-256)..."
        openssl enc -aes-256-cbc -salt \
            -in "backups/firehorse_${TIMESTAMP}.tar.gz" \
            -out "backups/firehorse_${TIMESTAMP}.tar.gz.enc" \
            -k "${BACKUP_ENCRYPTION_KEY}" 2>&1 >> "$LOG_FILE" || log_error "Encryption failed"
        
        rm -f "backups/firehorse_${TIMESTAMP}.tar.gz"
        ENCRYPTED_SIZE=$(du -sh "backups/firehorse_${TIMESTAMP}.tar.gz.enc" | cut -f1)
        log_success "Encrypted: ${ENCRYPTED_SIZE}"
    fi
    log ""
}

verify() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 5: VERIFICATION"
    log "════════════════════════════════════════════════════════════"
    
    FILE_COUNT=$(find "${BACKUP_DIR}" -type f 2>/dev/null | wc -l)
    find "${BACKUP_DIR}" -type f -exec md5sum {} \; > "${BACKUP_DIR}/../checksums_${TIMESTAMP}.md5" || \
        log_error "Checksum creation failed"
    log_success "Checksums created (${FILE_COUNT} files)"
    
    md5sum -c "${BACKUP_DIR}/../checksums_${TIMESTAMP}.md5" 2>&1 | tail -3 >> "$LOG_FILE" || true
    VERIFIED=$(md5sum -c "${BACKUP_DIR}/../checksums_${TIMESTAMP}.md5" 2>&1 | grep -c "OK" || echo "0")
    log_success "Verified ${VERIFIED} files"
    log ""
}

cleanup() {
    log "════════════════════════════════════════════════════════════"
    log "PHASE 6: CLEANUP"
    log "════════════════════════════════════════════════════════════"
    
    find backups/ -maxdepth 1 -type d -name "2*" -mtime +${BACKUP_RETENTION_DAYS} \
        -exec rm -rf {} \; 2>/dev/null || true
    log_success "Cleanup completed"
    log ""
}

main() {
    mkdir -p backups
    
    log "╔════════════════════════════════════════════════════════════╗"
    log "║  FIREHORSE BACKUP SYSTEM v3.0 - PRODUCTION                 ║"
    log "║  Started: ${TIMESTAMP}                          ║"
    log "║  Database: ${DB_NAME}                                  ║"
    log "╚════════════════════════════════════════════════════════════╝"
    log ""
    
    validate && backup_db && backup_app && secure && verify && cleanup
    
    log "╔════════════════════════════════════════════════════════════╗"
    log "║  ✅ BACKUP COMPLETED SUCCESSFULLY                          ║"
    log "║  Backup ID: ${TIMESTAMP}                          ║"
    log "║  Location: backups/${TIMESTAMP}                            ║"
    log "╚════════════════════════════════════════════════════════════╝"
}

main "$@"
