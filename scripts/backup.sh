#!/bin/bash
# MiLyfe Brain — Automated Backup Script
# Backs up database, workspace, and configuration

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="milyfe_backup_${TIMESTAMP}"

echo "=== MiLyfe Brain Backup ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Backup dir: ${BACKUP_DIR}"

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup database
echo "Backing up database..."
if docker compose exec -T backend test -f /data/milyfe.db 2>/dev/null; then
    docker compose cp backend:/data/milyfe.db "${BACKUP_DIR}/${BACKUP_NAME}/milyfe.db"
    echo "  Database backed up"
else
    echo "  No database found (skipped)"
fi

# Backup workspace
echo "Backing up workspace..."
if docker compose exec -T backend test -d /workspace 2>/dev/null; then
    docker compose exec -T backend tar czf - /workspace > "${BACKUP_DIR}/${BACKUP_NAME}/workspace.tar.gz"
    echo "  Workspace backed up"
else
    echo "  No workspace found (skipped)"
fi

# Backup .env
echo "Backing up configuration..."
if [ -f .env ]; then
    cp .env "${BACKUP_DIR}/${BACKUP_NAME}/.env.backup"
    echo "  .env backed up"
fi

# Create archive
echo "Creating archive..."
cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
rm -rf "${BACKUP_NAME}/"

echo ""
echo "=== Backup Complete ==="
echo "File: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: $(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)"
