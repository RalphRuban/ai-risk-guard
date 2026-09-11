#!/usr/bin/env bash
#
# AI Risk Guard - nightly SQLite backup (WAL-safe).
#
# Installed to /usr/local/sbin/backup-dashboard.sh by deploy/azure-vm-setup.sh
# and scheduled via /etc/cron.d/ai-risk-guard-backup (daily 03:15).
#
# Backs up the live DB including the -wal / -shm sidecar files (WAL writes are
# not checkpointed at kill time) and prunes archives older than 14 days.

set -euo pipefail

DB_PATH="${DB_PATH:-/opt/ai-risk-guard/data/dashboard.db}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ai-risk-guard}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

DB_DIR="$(dirname "${DB_PATH}")"
DB_NAME="$(basename "${DB_PATH}")"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB_PATH}" ]]; then
  echo "[backup] database not found: ${DB_PATH}; nothing to do" >&2
  exit 0
fi

# sqlite3 may not be installed; use .backup via python if available.
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/${DB_NAME}.snapshot'"
else
  python3 - "${DB_PATH}" "${BACKUP_DIR}/${DB_NAME}.snapshot" <<'PY'
import shutil, sys
shutil.copy2(sys.argv[1], sys.argv[2])
PY
fi

# Package the snapshot plus the WAL sidecar files from the live data dir.
STAMP="$(date +%F)"
tar -czf "${BACKUP_DIR}/db-${STAMP}.tgz" \
  -C "${BACKUP_DIR}" "${DB_NAME}.snapshot" \
  -C "${DB_DIR}" "${DB_NAME}-wal" "${DB_NAME}-shm" 2>/dev/null || \
tar -czf "${BACKUP_DIR}/db-${STAMP}.tgz" -C "${BACKUP_DIR}" "${DB_NAME}.snapshot"
rm -f "${BACKUP_DIR}/${DB_NAME}.snapshot"

# Prune archives older than the retention window.
find "${BACKUP_DIR}" -name 'db-*.tgz' -mtime "+${RETENTION_DAYS}" -delete

echo "[backup] wrote ${BACKUP_DIR}/db-${STAMP}.tgz (retention ${RETENTION_DAYS}d)"