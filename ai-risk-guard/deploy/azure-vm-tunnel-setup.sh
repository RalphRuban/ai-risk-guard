#!/usr/bin/env bash
#
# AI Risk Guard - Azure VM bootstrap for the ngrok tunnel deployment.
# Idempotent; safe to re-run. Run as root (sudo) on a fresh Ubuntu 24.04 VM.
#
# Public HTTPS is terminated by ngrok's edge on a reserved free static domain
# (".ngrok-free.app"), so no nginx/certbot/real-domain is needed: the app just
# binds 127.0.0.1:8000 and a systemd-managed ngrok agent tunnels it out. The
# only inbound port ever opened is SSH (22).
#
# Unlike deploy/azure-vm-setup.sh, the app code is *cloned* from GITHUB_REPO
# into /opt/ai-risk-guard (must be a public URL) instead of rsynced from a
# script directory, so this script may be scp'd to /tmp and run from anywhere.
#
# Required env vars (export in the calling shell or REQUIRED_ENV_FILE):
#   HOSTNAME            ngrok static domain (e.g. my-app.ngrok-free.app)
#   GITHUB_REPO         public clone URL of the repo to run and deploy
#   NGROK_AUTHTOKEN     ngrok agent authtoken (dashboard -> Your Authtoken)
#   GITHUB_APP_ID / GITHUB_PRIVATE_KEY / GITHUB_WEBHOOK_SECRET /
#   GITHUB_APP_CLIENT_ID / GITHUB_APP_CLIENT_SECRET / FLASK_SECRET_KEY
#
# Optional:
#   NGROK_STATIC_DOMAIN default: HOSTNAME
#   DEPLOY_SSH_PUBKEY   authorized_keys line for the CI deploy user
#   CI_IMAGE            "no" skips building the Docker sandbox image
#   ADMIN_SSH_IPS       space-separated CIDRs allowed on SSH (default: anywhere)
#   GEMINI_API_KEY / CI_VALIDATION_SECRET / CI_VALIDATION_TOKEN / other app env
#
# Example:
#   sudo HOSTNAME=my-app.ngrok-free.app \
#        GITHUB_REPO=https://github.com/RalphRuban/ai-risk-guard.git \
#        NGROK_AUTHTOKEN=2abc... \
#        DEPLOY_SSH_PUBKEY="$(cat ~/.ssh/ai-risk-guard-deploy.pub)" \
#        REQUIRED_ENV_FILE=/home/azureuser/env.secrets \
#        bash /tmp/azure-vm-tunnel-setup.sh

set -euo pipefail

APP_USER="${APP_USER:-airiskguard}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/ai-risk-guard}"
DATA_DIR="${APP_DIR}/data"
DB_PATH="${DB_PATH:-${DATA_DIR}/dashboard.db}"
SANDBOX_IMAGE="${SANDBOX_IMAGE:-ai-risk-guard:sandbox}"
HOSTNAME="${HOSTNAME:-}"
NGROK_STATIC_DOMAIN="${NGROK_STATIC_DOMAIN:-${HOSTNAME}}"
NGROK_STATIC_DOMAIN="${NGROK_STATIC_DOMAIN#https://}"
NGROK_STATIC_DOMAIN="${NGROK_STATIC_DOMAIN#http://}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)" >&2
  exit 1
fi

if [[ -z "${HOSTNAME}" ]]; then
  echo "ERROR: set HOSTNAME=<ngrok-static-domain> (e.g. my-app.ngrok-free.app)" >&2
  exit 1
fi
if [[ -z "${GITHUB_REPO:-}" ]]; then
  echo "ERROR: set GITHUB_REPO=<public-clone-url> (e.g. https://github.com/u/repo.git)" >&2
  exit 1
fi
if [[ -z "${NGROK_AUTHTOKEN:-}" ]]; then
  echo "ERROR: set NGROK_AUTHTOKEN=<token> (ngrok dashboard -> Your Authtoken)" >&2
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

log() { echo "[azure-vm-tunnel-setup] $*"; }

# --- 1. System packages ------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  curl ca-certificates gnupg git rsync python3 python3-venv python3-pip \
  ufw >/dev/null

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

# --- 3. App user + code ------------------------------------------------------
id "${APP_USER}" >/dev/null 2>&1 || useradd --system --groups docker \
  --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
usermod -aG docker "${APP_USER}"

# After the first run's chown, the repo is owned by the app user; a later
# re-run as root must still be able to fetch/reset it (dubious ownership).
git config --global --add safe.directory "${APP_DIR}" >/dev/null 2>&1 || true

if [[ ! -d "${APP_DIR}/.git" ]]; then
  log "cloning ${GITHUB_REPO} into ${APP_DIR}"
  git clone --depth 1 "${GITHUB_REPO}" "${APP_DIR}"
else
  log "refreshing repo at ${APP_DIR}"
  git -C "${APP_DIR}" fetch --all --quiet
  git -C "${APP_DIR}" reset --hard origin/HEAD
fi

# The cloned repo may keep the app under a same-named subfolder (e.g. when the
# git root is the workspace that contains the project). Resolve the real app
# root so requirements/units/builds resolve regardless of layout.
if [[ -f "${APP_DIR}/ai-risk-guard/app/app.py" && -f "${APP_DIR}/ai-risk-guard/requirements.txt" ]]; then
  APP_SRC="${APP_DIR}/ai-risk-guard"
else
  APP_SRC="${APP_DIR}"
fi
mkdir -p "${DATA_DIR}"

# --- 4. venv + deps ----------------------------------------------------------
if [[ ! -d "${APP_DIR}/venv" ]]; then
  log "creating venv"
  python3 -m venv "${APP_DIR}/venv"
fi
"${APP_DIR}/venv/bin/pip" install --quiet --upgrade pip
"${APP_DIR}/venv/bin/pip" install --quiet -r "${APP_SRC}/requirements.txt"

# --- 5. Sandbox image --------------------------------------------------------
if [[ "${CI_IMAGE:-}" != "no" ]]; then
  if ! docker image inspect "${SANDBOX_IMAGE}" >/dev/null 2>&1; then
    log "building sandbox image ${SANDBOX_IMAGE}"
    docker build -f "${APP_SRC}/sandbox/Dockerfile.sandbox" -t "${SANDBOX_IMAGE}" "${APP_SRC}"
  else
    log "sandbox image already present; skipping build"
  fi
fi

# --- 6. Systemd service ------------------------------------------------------
install -o root -g root -m 0644 \
  "${APP_SRC}/deploy/ai-risk-guard.service" /etc/systemd/system/ai-risk-guard.service
sed -i "s#^WorkingDirectory=.*#WorkingDirectory=${APP_SRC}#" \
  /etc/systemd/system/ai-risk-guard.service
systemctl daemon-reload
systemctl enable ai-risk-guard >/dev/null 2>&1 || true

# --- 7. Deploy user for CI (SSH + sudoers) -----------------------------------
if [[ -z "${DEPLOY_SSH_PUBKEY:-}" ]]; then
  log "DEPLOY_SSH_PUBKEY unset; skipping deploy user creation (CI deploy will not work)"
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
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
  chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"
  chown -R "${APP_USER}:${APP_USER}" "${DATA_DIR}"
  chmod -R g+w "${APP_DIR}"
  chmod 750 "${DATA_DIR}"
  log "configured deploy user '${DEPLOY_USER}' with restricted sudo for ai-risk-guard"
fi

# --- 8. Environment file (root-only, mode 600) -------------------------------
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
NGROK_BYPASS_WARNING=${NGROK_BYPASS_WARNING:-true}
EOF
  chmod 600 "${ENV_FILE}"
  chown root:root "${ENV_FILE}"
  log "wrote ${ENV_FILE} (mode 600)"
else
  log "${ENV_FILE} already exists; leaving unchanged"
fi

# --- 9. ngrok tunnel ----------------------------------------------------------
if ! command -v ngrok >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc -o /etc/apt/keyrings/ngrok.asc
  echo "deb [signed-by=/etc/apt/keyrings/ngrok.asc] https://ngrok-agent.s3.amazonaws.com buster main" \
    > /etc/apt/sources.list.d/ngrok.list
  apt-get update -qq
  apt-get install -y -qq ngrok >/dev/null
fi
NGROK_BIN="$(command -v ngrok)"
cat > /etc/ngrok.yml <<EOF
version: "3"
agent:
  authtoken: ${NGROK_AUTHTOKEN}
EOF
chmod 600 /etc/ngrok.yml
cat > /etc/systemd/system/ngrok.service <<EOF
[Unit]
Description=ngrok tunnel for AI Risk Guard
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
ExecStart=${NGROK_BIN} http --url=https://${NGROK_STATIC_DOMAIN} --config=/etc/ngrok.yml 8000
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ngrok
log "tunnel: https://${NGROK_STATIC_DOMAIN} (ngrok systemd unit enabled)"

# --- 10. Firewall (SSH only; tunnel needs no inbound) -------------------------
if [[ -n "${ADMIN_SSH_IPS:-}" ]]; then
  for ip in ${ADMIN_SSH_IPS}; do
    ufw allow from "${ip}" to any port 22 proto tcp >/dev/null
  done
else
  ufw allow 22/tcp >/dev/null
fi
ufw --force enable >/dev/null

# --- 11. Nightly backup -------------------------------------------------------
install -o root -g root -m 0755 \
  "${APP_SRC}/deploy/backup-dashboard.sh" /usr/local/sbin/backup-dashboard.sh
cat > /etc/cron.d/ai-risk-guard-backup <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
15 3 * * * root /usr/local/sbin/backup-dashboard.sh
EOF
chmod 644 /etc/cron.d/ai-risk-guard-backup

# --- 12. Start + verify --------------------------------------------------------
systemctl restart ai-risk-guard
sleep 2
log "--- health checks ---"
curl -fsS "http://127.0.0.1:8000/api/health" && echo
curl -fsS "http://127.0.0.1:8000/api/health/ready" && echo
curl -fsS -I "http://127.0.0.1:8000/dashboard" | head -n 1
log "done. Dashboard: https://${HOSTNAME}/dashboard"
log "tunnel status: $(systemctl is-active ngrok)"