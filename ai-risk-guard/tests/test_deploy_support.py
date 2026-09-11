from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
WORKFLOWS = ROOT / ".github" / "workflows"


def test_service_unit_references_production_layout():
    unit = (DEPLOY / "ai-risk-guard.service").read_text(encoding="utf-8")
    assert "WorkingDirectory=/opt/ai-risk-guard" in unit
    assert "EnvironmentFile=/etc/ai-risk-guard.env" in unit
    assert "ExecStart=/opt/ai-risk-guard/venv/bin/python app/app.py" in unit
    assert "User=airiskguard" in unit
    assert "ReadWritePaths=/opt/ai-risk-guard/data" in unit


def test_nginx_conf_proxies_to_app():
    conf = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://127.0.0.1:8000" in conf
    assert "client_max_body_size 6m" in conf
    assert "X-Forwarded-Proto $scheme" in conf
    assert "server_name YOUR_HOSTNAME" in conf
    assert "/static/" in conf


def test_setup_script_shebang_and_key_steps():
    script = (DEPLOY / "azure-vm-setup.sh").read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash")
    assert "Dockerfile.sandbox" in script
    assert "/etc/ai-risk-guard.env" in script
    assert "certbot --nginx" in script
    assert "ai-risk-guard.service" in script
    assert "systemctl restart ai-risk-guard" in script


def test_setup_script_app_user_is_nologin():
    script = (DEPLOY / "azure-vm-setup.sh").read_text(encoding="utf-8")
    assert "useradd --system --home-dir \"${APP_DIR}\" --shell /usr/sbin/nologin" in script


def test_setup_script_deploy_user_login_capable():
    script = (DEPLOY / "azure-vm-setup.sh").read_text(encoding="utf-8")
    assert 'DEPLOY_USER="${DEPLOY_USER:-deploy}"' in script
    assert "useradd --create-home --shell /bin/bash --groups docker" in script
    assert "authorized_keys" in script
    assert "sudoers.d/ai-risk-guard-deploy" in script
    assert "NOPASSWD:" in script
    assert "DEPLOY_USER must differ from APP_USER" in script
    assert 'chmod 750 "${DATA_DIR}"' in script


def test_backup_script_wal_and_retention():
    script = (DEPLOY / "backup-dashboard.sh").read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash")
    assert "-wal" in script and "-shm" in script
    assert "14" in script


def test_deploy_workflow_gated_on_ci():
    yaml_text = (WORKFLOWS / "deploy.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(yaml_text)
    on_key = "on" if "on" in workflow else True
    trigger = workflow[on_key]
    assert trigger["workflow_run"]["workflows"] == ["CI"]
    assert trigger["workflow_run"]["branches"] == ["main"]
    assert trigger["workflow_run"]["types"] == ["completed"]
    assert "SSH_PRIVATE_KEY" in yaml_text
    assert "VM_HOST" in yaml_text
    assert "sudo systemctl restart ai-risk-guard" in yaml_text


def test_env_example_documents_ci_validation():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "CI_VALIDATION_SECRET" in env
    assert "CI_VALIDATION_BASE_URL" in env
    assert "CI_VALIDATION_TOKEN" in env