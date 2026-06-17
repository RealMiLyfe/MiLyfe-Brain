#!/usr/bin/env bash
# ============================================================
# MiLyfe Brain - Backup Script
# Creates timestamped backups of database, workspace, and ChromaDB
# ============================================================

set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"

echo "=== MiLyfe Brain Backup ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Backup directory: ${BACKUP_PATH}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_PATH}"

# --- Backup SQLite Database ---
echo "[1/3] Backing up SQLite database..."
docker compose exec -T backend cp /data/milyfe.db /data/milyfe_backup.db 2>/dev/null || true
docker compose cp backend:/data/milyfe_backup.db "${BACKUP_PATH}/milyfe.db" 2>/dev/null && \
    echo "  ✓ Database backed up" || \
    echo "  ⚠ Database backup skipped (not found or empty)"

# --- Backup Workspace ---
echo "[2/3] Backing up workspace..."
docker compose exec -T backend tar -czf /tmp/workspace_backup.tar.gz -C /workspace . 2>/dev/null || true
docker compose cp backend:/tmp/workspace_backup.tar.gz "${BACKUP_PATH}/workspace.tar.gz" 2>/dev/null && \
    echo "  ✓ Workspace backed up" || \
    echo "  ⚠ Workspace backup skipped (empty or unavailable)"

# --- Backup ChromaDB Data ---
echo "[3/3] Backing up ChromaDB data..."
CHROMA_VOLUME=$(docker compose volume ls --format '{{.Name}}' | grep chroma_data || true)
if [ -n "${CHROMA_VOLUME}" ]; then
    docker run --rm \
        -v "${CHROMA_VOLUME}:/source:ro" \
        -v "$(pwd)/${BACKUP_PATH}:/backup" \
        alpine:latest \
        tar -czf /backup/chromadb.tar.gz -C /source . 2>/dev/null && \
        echo "  ✓ ChromaDB backed up" || \
        echo "  ⚠ ChromaDB backup failed"
else
    echo "  ⚠ ChromaDB volume not found, skipping"
fi

echo ""
echo "=== Backup Complete ==="
echo "Location: ${BACKUP_PATH}"
ls -lh "${BACKUP_PATH}/" 2>/dev/null || true
echo ""
echo "To restore, use: docker compose down && restore from backup files"
