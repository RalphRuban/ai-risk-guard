#!/usr/bin/env bash
#
# AI Risk Guard - Azure VM bootstrap (idempotent). Run as root on a fresh
# Ubuntu 24.04 VM. Safe to re-run: every step checks whether it already ran.
#
#   HOSTNAME=<public-host> ./deploy/azure-vm-setup.sh
#
# Secrets are NOT accepted on the CLI. Export them in the calling shell or
# point REQUIRED_ENV_FILE at a root-only file (mode 600, never committed):
#
#   GITHUB_APP_ID / GITHUB_PRIVATE_KEY / GITHUB_WEBHOOK_SECRET /
#   GITHUB_APP_CLIENT_ID / GITHUB_APP_CLIENT_SECRET / FLASK_SECRET_KEY /
#   GEMINI_API_KEY (optional) / GITHUB_APP_SLUG (optional) /
#   APP_DASHBOARD_URL (optional) / METRICS_SCRAPE_TOKEN (optional) /
#   CI_VALIDATION_SECRET / CI_VALIDATION_BASE_URL / CI_VALIDATION_TOKEN
#
# The vars are written to /etc/ai-risk-guard.env (root-only, mode 600), which
# the systemd unit loads via EnvironmentFile.
#
# Options:
#   HOSTNAME            Public hostname (A record pointing at this VM).
#   ADMIN_SSH_IPS       Space-separated CIDRs allowed on SSH (default: none
#                       restricted, ufw SSH rule skipped).
#   CI_IMAGE            Skip building the Docker sandbox image when "no"
#                       (already built / Docker unavailable).
#   DEPLOY_USER         Login-capable user used by the GitHub deploy workflow
#                       (default: "deploy"). Must differ from APP_USER, which
#                       keeps /usr/sbin/nologin and runs the service.
#   DEPLOY_SSH_PUBKEY   Public key (authorized_keys line) permitting SSH login
#                       for the deploy user. Required for CI deploy to work.
#   REQUIRED_ENV_FILE   Path to a file exporting the required env vars.

set -euo pipefail

APP_USER="${APP_USER:-airiskguard}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/ai-risk-guard}"
DATA_DIR="${APP_DIR}/data"
DB_PATH="${DB_PATH:-${DATA_DIR}/dashboard.db}"
SANDBOX_IMAGE="${SANDBOX_IMAGE:-ai-risk-guard:sandbox}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)" >&2
  exit 1
fi

if [[ -z "${HOSTNAME:-}" ]]; then
  echo "ERROR: set HOSTNAME=<public-host> (e.g. arg.example.com)" >&2
  exit 1
fi

if [[ -n "${REQUIRED_ENV_FILE:-}" ]]; then
  if [[ -f "${REQUIRED_ENV_FILE}" ]]; then
    set -a; source "${REQUIRED_ENV_FILE}"; set +a
  else
    echo "ERROR: REQUIRED_ENV_FILE not found: ${REQUIRED_ENV_FILE}" >&2
    exit 1
  fi
fi

required=(
  GITHUB_APP_ID GITHUB_PRIVATE_KEY GITHUB_WEBHOOK_SECRET
  GITHUB_APP_CLIENT_ID GITHUB_APP_CLIENT_SECRET FLASK_SECRET_KEY
)
for v in "${required[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "ERROR: required env var missing: ${v}" >&2
    exit 1
  fi
done

log() { echo "[azure-vm-setup] $*"; }

# --- 1. System packages ------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  curl ca-certificates gnupg git rsync python3 python3-venv python3-pip \
  nginx certbot python3-certbot-nginx ufw >/dev/null

# --- 2. Docker CE (official repo) -------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null
fi
systemctl enable --now docker
systemctl restart docker

# --- 3. Sandbox image --------------------------------------------------------
if [[ "${CI_IMAGE:-}" != "no" ]]; then
  if ! docker image inspect "${SANDBOX_IMAGE}" >/dev/null 2>&1; then
    log "building sandbox image ${SANDBOX_IMAGE}"
    docker build -f "${REPO_ROOT}/sandbox/Dockerfile.sandbox" -t "${SANDBOX_IMAGE}" "${REPO_ROOT}"
  else
    log "sandbox image already present; skipping build"
  fi
fi

# --- 4. App code, venv, data dir ---------------------------------------------
id "${APP_USER}" >/dev/null 2>&1 || useradd --system --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p "${APP_DIR}" "${DATA_DIR}"

if [[ -f "${APP_DIR}/app/app.py" ]]; then
  log "app code present; refreshing from repo"
fi
rsync -a --delete \
  --exclude '.git' --exclude 'venv' --exclude 'frontend/node_modules' \
  --exclude 'data' --exclude '.env' \
  "${REPO_ROOT}/" "${APP_DIR}/"

if [[ ! -d "${APP_DIR}/venv" ]]; then
  log "creating venv"
  python3 -m venv "${APP_DIR}/venv"
fi
"${APP_DIR}/venv/bin/pip" install --quiet --upgrade pip
"${APP_DIR}/venv/bin/pip" install --quiet -r "${APP_DIR}/requirements.txt"

# --- 5. Systemd service + env file -------------------------------------------
install -o root -g root -m 0644 \
  "${REPO_ROOT}/deploy/ai-risk-guard.service" /etc/systemd/system/ai-risk-guard.service

ENV_FILE=/etc/ai-risk-guard.env
if [[ ! -f "${ENV_FILE}" ]]; then
  cat > "${ENV_FILE}" <<EOF
GITHUB_APP_ID=${GITHUB_APP_ID}
GITHUB_PRIVATE_KEY=${GITHUB_PRIVATE_KEY}
GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
GITHUB_APP_CLIENT_ID=${GITHUB_APP_CLIENT_ID}
GITHUB_APP_CLIENT_SECRET=${GITHUB_APP_CLIENT_SECRET}
FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
APP_ENV=production
DB_PATH=${DB_PATH}
SESSION_COOKIE_SECURE=true
GITHUB_APP_SLUG=${GITHUB_APP_SLUG:-}
APP_DASHBOARD_URL=${APP_DASHBOARD_URL:-https://${HOSTNAME}/dashboard}
METRICS_SCRAPE_TOKEN=${METRICS_SCRAPE_TOKEN:-}
CI_VALIDATION_SECRET=${CI_VALIDATION_SECRET:-}
CI_VALIDATION_BASE_URL=${CI_VALIDATION_BASE_URL:-https://${HOSTNAME}}
CI_VALIDATION_TOKEN=${CI_VALIDATION_TOKEN:-}
GEMINI_API_KEY=${GEMINI_API_KEY:-}
EOF
  chmod 600 "${ENV_FILE}"
  chown root:root "${ENV_FILE}"
  log "wrote ${ENV_FILE} (mode 600)"
else
  log "${ENV_FILE} already exists; leaving unchanged"
fi

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
systemctl daemon-reload
systemctl enable ai-risk-guard >/dev/null 2>&1 || true

# --- 4b. Deploy user for CI (SSH + sudoers) -----------------------------------
# The GitHub deploy workflow connects over SSH to rsync code and restart the
# service. APP_USER runs the app with a nologin shell (never logs in), so we
# create a separate login-capable DEPLOY_USER and grant it a minimal sudoers
# rule that only permits restarting the ai-risk-guard unit.
if [[ -z "${DEPLOY_SSH_PUBKEY:-}" ]]; then
  log "DEPLOY_SSH_PUBKEY unset; skipping deploy user creation (CI deploy will not work)"
else
  if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --groups docker "${DEPLOY_USER}"
  fi
  if [[ "${DEPLOY_USER}" == "${APP_USER}" ]]; then
    echo "ERROR: DEPLOY_USER must differ from APP_USER" >&2
    exit 1
  fi
  install -d -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" -m 0700 "/home/${DEPLOY_USER}/.ssh"
  install -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" -m 0600 /dev/null "/home/${DEPLOY_USER}/.ssh/authorized_keys"
  printf '%s\n' "${DEPLOY_SSH_PUBKEY}" > "/home/${DEPLOY_USER}/.ssh/authorized_keys"
  chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"
  SYSTEMCTL="$(command -v systemctl)"
  cat > "/etc/sudoers.d/ai-risk-guard-deploy" <<EOF
Defaults:${DEPLOY_USER} !requiretty
${DEPLOY_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} start ai-risk-guard, ${SYSTEMCTL} stop ai-risk-guard, ${SYSTEMCTL} restart ai-risk-guard, ${SYSTEMCTL} status ai-risk-guard
EOF
  chmod 0440 "/etc/sudoers.d/ai-risk-guard-deploy"
  visudo -c >/dev/null || { echo "ERROR: sudoers rule failed validation" >&2; exit 1; }
  # Publish ownership to the deploy user so rsync/pip can update the code,
  # then restore the data dir to the app user (the service writes its SQLite
  # DB there without elevated privileges).
  chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"
  chown -R "${APP_USER}:${APP_USER}" "${DATA_DIR}"
  chmod -R g+w "${APP_DIR}"
  chmod 750 "${DATA_DIR}"
  log "configured deploy user '${DEPLOY_USER}' with restricted sudo for ai-risk-guard"
fi

# --- 6. Nginx + TLS ----------------------------------------------------------
SITE=/etc/nginx/sites-available/ai-risk-guard
if [[ ! -f "${SITE}" ]]; then
  sed "s/YOUR_HOSTNAME/${HOSTNAME}/g" \
    "${REPO_ROOT}/deploy/nginx.conf" > "${SITE}"
  ln -sf "${SITE}" /etc/nginx/sites-enabled/ai-risk-guard
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
fi

if [[ ! -d "/etc/letsencrypt/live/${HOSTNAME}" ]]; then
  log "obtaining Let's Encrypt certificate for ${HOSTNAME}"
  certbot --nginx -d "${HOSTNAME}" --redirect --non-interactive --agree-tos \
    -m "admin@${HOSTNAME#*.}" || log "certbot failed (check DNS/port 80); leaving HTTP-only"
else
  log "certificate already present; skipping certbot"
fi
systemctl reload nginx

# --- 7. Firewall -------------------------------------------------------------
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
if [[ -n "${ADMIN_SSH_IPS:-}" ]]; then
  for ip in ${ADMIN_SSH_IPS}; do
    ufw allow from "${ip}" to any port 22 proto tcp >/dev/null
  done
else
  log "ADMIN_SSH_IPS unset; leaving default SSH access"
fi
ufw --force enable >/dev/null

# --- 8. Nightly backup -------------------------------------------------------
install -o root -g root -m 0755 \
  "${REPO_ROOT}/deploy/backup-dashboard.sh" /usr/local/sbin/backup-dashboard.sh
cat > /etc/cron.d/ai-risk-guard-backup <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * root /usr/local/sbin/backup-dashboard.sh
EOF
chmod 644 /etc/cron.d/ai-risk-guard-backup

# --- 9. Start + verify -------------------------------------------------------
systemctl restart ai-risk-guard
sleep 2
log "--- health checks ---"
curl -fsS "http://127.0.0.1:8000/api/health" && echo
curl -fsS "http://127.0.0.1:8000/api/health/ready" && echo
curl -fsS -I "http://127.0.0.1:8000/dashboard" | head -n 1
log "done. Dashboard: https://${HOSTNAME}/dashboard"