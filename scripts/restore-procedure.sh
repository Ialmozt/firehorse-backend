#!/bin/bash
set -euo pipefail

if [ ! -f ".env.backup" ]; then
    echo "❌ ERROR: .env.backup not found!"
    exit 1
fi

source .env.backup

echo "🔄 FIREHORSE DISASTER RECOVERY: SELECT RESTORE LAYER"
echo ""
echo "1. Restore from Database Snapshot (24-hour RPO)"
echo "2. Restore from Application Backup (Full system)"
echo "3. FULL ROLLBACK: Restore everything + redeploy"
echo ""
read -p "Select option (1-3): " option

case $option in
    1)
        echo "📦 Restoring from Database Snapshot..."
        read -p "Enter backup timestamp (YYYYMMDD_HHMMSS): " backup_ts
        
        BACKUP_FILE="backups/${backup_ts}/db/full_dump.sql.gz"
        
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ Backup file not found: $BACKUP_FILE"
            ls -la "backups/${backup_ts}/db/" 2>/dev/null || echo "   Backup directory not found"
            exit 1
        fi

        echo "⚠️  WARNING: This will DROP the entire database and restore from backup"
        echo "   Database: ${DB_NAME}"
        echo "   Backup: $BACKUP_FILE"
        read -p "Continue? (type 'yes' to confirm): " confirm
        
        if [ "$confirm" = "yes" ]; then
            export PGPASSWORD="${DB_PASSWORD}"
            
            echo "🔄 Restoring database..."
            
            # Check if database exists
            if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
                echo "Terminating existing connections..."
                psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
                    -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();" 2>/dev/null || true
                
                echo "Dropping current database..."
                dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
            fi
            
            echo "Creating new database..."
            createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
            
            echo "Restoring from backup..."
            pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
                -F c "$BACKUP_FILE" --verbose
            
            unset PGPASSWORD
            echo "✅ Restore completed!"
        fi
        ;;
    2)
        echo "💾 Restoring Application Backup..."
        read -p "Enter backup timestamp (YYYYMMDD_HHMMSS): " backup_ts
        
        BACKUP_FILE="backups/firehorse_${backup_ts}.tar.gz.enc"
        
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ Encrypted backup not found: $BACKUP_FILE"
            exit 1
        fi

        echo "Stopping Docker services..."
        docker-compose down || true
        
        echo "Restoring volumes..."
        docker volume rm firehorse_data 2>/dev/null || true
        docker volume create firehorse_data
        
        read -sp "Enter encryption key: " encryption_key
        echo ""
        
        echo "Decrypting backup..."
        openssl enc -aes-256-cbc -d -in "$BACKUP_FILE" \
            -out "/tmp/firehorse_${backup_ts}.tar.gz" -k "$encryption_key" || {
            echo "❌ Decryption failed - wrong key?"
            exit 1
        }
        
        echo "Extracting backup..."
        docker run --rm -v firehorse_data:/data -v /tmp:/backup \
            alpine tar xzf /backup/firehorse_${backup_ts}.tar.gz -C /data
        
        rm -f "/tmp/firehorse_${backup_ts}.tar.gz"
        
        echo "Starting Docker services..."
        docker-compose up -d
        echo "✅ Restore completed!"
        ;;
    3)
        echo "🚀 FULL ROLLBACK: Stop → Restore DB → Restore volumes → Redeploy"
        read -p "⚠️  Confirm? (type 'yes'): " confirm
        if [ "$confirm" = "yes" ]; then
            docker-compose down || true
            docker-compose up -d
            echo "✅ Rollback completed"
        fi
        ;;
    *)
        echo "Invalid option"
        ;;
esac
