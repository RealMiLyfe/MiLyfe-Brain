#!/bin/bash
# MiLyfe Brain Backup Script
# Backs up database and workspace data

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="milyfe_backup_${TIMESTAMP}"

echo "=== MiLyfe Brain Backup ==="
echo "Timestamp: ${TIMESTAMP}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Backup SQLite database
echo "[1/3] Backing up database..."
docker compose exec -T backend cp /data/milyfe.db /tmp/milyfe_backup.db 2>/dev/null || true
docker compose cp backend:/tmp/milyfe_backup.db "${BACKUP_DIR}/${BACKUP_NAME}.db" 2>/dev/null || echo "  Warning: No database found (first run?)"

# Backup workspace
echo "[2/3] Backing up workspace..."
docker compose exec -T backend tar czf /tmp/workspace_backup.tar.gz /workspace 2>/dev/null || true
docker compose cp backend:/tmp/workspace_backup.tar.gz "${BACKUP_DIR}/${BACKUP_NAME}_workspace.tar.gz" 2>/dev/null || echo "  Warning: No workspace data found"

# Backup ChromaDB
echo "[3/3] Backing up vector store..."
docker compose exec -T chromadb tar czf /tmp/chroma_backup.tar.gz /chroma/chroma 2>/dev/null || true
docker compose cp chromadb:/tmp/chroma_backup.tar.gz "${BACKUP_DIR}/${BACKUP_NAME}_chroma.tar.gz" 2>/dev/null || echo "  Warning: No ChromaDB data found"

echo ""
echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}*"
ls -lh "${BACKUP_DIR}/${BACKUP_NAME}"* 2>/dev/null || echo "No files created (services may not be running)"
