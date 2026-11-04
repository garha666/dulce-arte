#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Instalación de Dulce Arte en Ubuntu 22.04 (AWS EC2).
#
# Uso:
#   1. Copia el proyecto a ~/apps/dulce-arte (git clone o scp).
#   2. Edita deploy/.env.produccion con tu IP elástica.
#   3. bash deploy/instalar.sh
#
# El script es idempotente: puedes ejecutarlo más de una vez.
# ---------------------------------------------------------------------------
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_NAME="${DB_NAME:-dulcearte}"
DB_USER="${DB_USER:-dulcearte}"
DB_PASS="${DB_PASS:-dulcearte2026}"

echo "==> Paquetes del sistema"
sudo apt update -y
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib

echo "==> PostgreSQL: base de datos y usuario"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET timezone TO 'America/Santiago';"
sudo -u postgres psql -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

echo "==> Entorno virtual y dependencias"
python3 -m venv "${APP_DIR}/env"
"${APP_DIR}/env/bin/pip" install --upgrade pip --quiet
"${APP_DIR}/env/bin/pip" install -r "${APP_DIR}/requirements.txt" --quiet

echo "==> Archivo .env"
if [ ! -f "${APP_DIR}/.env" ]; then
  cp "${APP_DIR}/deploy/.env.produccion" "${APP_DIR}/.env"
  echo "Se creó .env desde deploy/.env.produccion — revisa la IP y la SECRET_KEY."
fi

echo "==> Migraciones, estáticos y datos de prueba"
cd "${APP_DIR}"
"${APP_DIR}/env/bin/python" manage.py migrate --noinput
"${APP_DIR}/env/bin/python" manage.py collectstatic --noinput
"${APP_DIR}/env/bin/python" seed_data.py || true

echo "==> Gunicorn (systemd)"
sudo cp "${APP_DIR}/deploy/gunicorn.service" /etc/systemd/system/gunicorn.service
sudo sed -i "s#/home/ubuntu/apps/dulce-arte#${APP_DIR}#g" /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl restart gunicorn

echo "==> Nginx"
sudo cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/dulcearte
sudo sed -i "s#/home/ubuntu/apps/dulce-arte#${APP_DIR}#g" /etc/nginx/sites-available/dulcearte
sudo ln -sf /etc/nginx/sites-available/dulcearte /etc/nginx/sites-enabled/dulcearte
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "==> Permisos del socket"
sudo usermod -aG www-data ubuntu || true
sudo usermod -aG ubuntu www-data || true
sudo chmod 750 /home/ubuntu || true
sudo chown ubuntu:www-data "${APP_DIR}/dulcearte.sock" || true
sudo chmod 660 "${APP_DIR}/dulcearte.sock" || true
sudo systemctl restart gunicorn nginx

echo
echo "Listo. Abre http://<IP_ELASTICA>/ en el navegador."
echo "Estado:  sudo systemctl status gunicorn nginx"
