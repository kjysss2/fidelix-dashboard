#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/fidelix-dashboard"
APP_USER="fidelix"

if [[ "${EUID}" -ne 0 ]]; then
  echo "root 권한으로 실행해야 합니다. 예: sudo bash deploy/naver-cloud/bootstrap-ubuntu.sh"
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv nginx curl ca-certificates

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
fi

mkdir -p "${APP_DIR}/data" "${APP_DIR}/static"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  if [[ -f "${APP_DIR}/.env.example" ]]; then
    cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  else
    cat > "${APP_DIR}/.env" <<'ENV'
DART_API_KEY=
REFRESH_AT=08:00
HOST=127.0.0.1
PORT=8765
REFRESH_ON_STARTUP=0
ENABLE_CHINA_IDC=0
ENV
  fi
fi

python3 -m py_compile "${APP_DIR}/server.py" "${APP_DIR}/refresh_once.py"

cp "${APP_DIR}/deploy/naver-cloud/fidelix-dashboard.service" /etc/systemd/system/fidelix-dashboard.service
cp "${APP_DIR}/deploy/naver-cloud/nginx-fidelix-dashboard.conf" /etc/nginx/sites-available/fidelix-dashboard
ln -sf /etc/nginx/sites-available/fidelix-dashboard /etc/nginx/sites-enabled/fidelix-dashboard
rm -f /etc/nginx/sites-enabled/default

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

systemctl daemon-reload
systemctl enable fidelix-dashboard
systemctl restart fidelix-dashboard

nginx -t
systemctl enable nginx
systemctl restart nginx

echo "배포 완료"
echo "서비스 확인: systemctl status fidelix-dashboard --no-pager"
echo "웹 확인: curl http://127.0.0.1/api/health"
