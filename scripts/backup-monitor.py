#!/usr/bin/env python3
import subprocess
from datetime import datetime
from pathlib import Path

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except:
        return 1, "", "Error"

def check_backup_age():
    backup_dir = Path("backups")
    if not backup_dir.exists():
        return False, "No backups directory"
    backup_dirs = sorted([d for d in backup_dir.iterdir() if d.is_dir() and d.name[0].isdigit()])
    if not backup_dirs:
        return False, "No backups found"
    latest = backup_dirs[-1]
    age_minutes = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 60
    if age_minutes < 120:
        return True, f"Latest backup: {age_minutes/60:.1f}h old ✓"
    else:
        return False, f"Latest backup: {age_minutes/60:.1f}h old (too old)"

def check_backup_integrity():
    backup_dir = Path("backups")
    checksum_files = sorted(list(backup_dir.glob("checksums_*.md5")))
    if not checksum_files:
        return False, "No checksum files found"
    latest_checksum = checksum_files[-1]
    try:
        with open(latest_checksum, 'r') as f:
            lines = f.readlines()
        if not lines:
            return False, "Checksum file is empty"
        verified_count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            expected_hash, rel_filename = parts
            file_path = Path(rel_filename)
            if not file_path.exists():
                return False, f"Missing file: {rel_filename}"
            rc, output, _ = run_cmd(f"md5sum '{file_path}'")
            if rc == 0:
                actual_hash = output.split()[0]
                if actual_hash == expected_hash:
                    verified_count += 1
                else:
                    return False, f"Hash mismatch"
            else:
                return False, f"Cannot compute hash"
        if verified_count > 0:
            return True, f"Checksum files verified ({len(checksum_files)} backups)"
        else:
            return False, "No valid checksums"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_db_connection():
    rc, _, _ = run_cmd("docker ps | grep -q firehorse-postgres")
    if rc != 0:
        return False, "Container not running"
    rc, output, error = run_cmd("docker exec firehorse-postgres pg_isready -U postgres 2>&1")
    if rc == 0 and "accepting" in output:
        return True, "Database connection OK"
    else:
        return False, f"Database not responding"

def main():
    print("=" * 60)
    print("FIREHORSE BACKUP HEALTH CHECK")
    print("=" * 60)
    checks = [
        ("Backup Age (RPO)", check_backup_age),
        ("Backup Integrity", check_backup_integrity),
        ("Database Connection", check_db_connection),
    ]
    results = []
    for name, check_func in checks:
        passed, message = check_func()
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {name}: {message}")
        results.append(passed)
    print("=" * 60)
    return 0 if all(results) else 1

if __name__ == "__main__":
    exit(main())
