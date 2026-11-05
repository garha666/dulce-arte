#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Instalación de Dulce Arte en Ubuntu 22.04 (AWS EC2).
#
# Uso:
#   1. Copia el proyecto a ~/apps/dulce-arte (git clone o scp).
#   2. Edita deploy/.env.produccion y reemplaza IP_ELASTICA.
#   3. bash deploy/instalar.sh
#
# Variables opcionales:
#   DB_PASS="..."        clave de PostgreSQL (si no se indica, se genera una).
#   SEED_DEMO_DATA=true  carga seed_data.py (solo para una demo controlada).
#
# El script es idempotente: puedes ejecutarlo más de una vez.
# ---------------------------------------------------------------------------
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${APP_DIR}/.env"
DB_NAME="${DB_NAME:-dulcearte}"
DB_USER="${DB_USER:-dulcearte}"
SEED_DEMO_DATA="${SEED_DEMO_DATA:-false}"

generar_clave() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "${1:-24}"
  else
    python3 -c "import secrets; print(secrets.token_urlsafe(${1:-32}))"
  fi
}

leer_env() {
  grep -E "^$1=" "${ENV_FILE}" 2>/dev/null | tail -n 1 | cut -d= -f2-
}

# ---------------------------------------------------------------- Credenciales
DB_PASS="${DB_PASS:-}"
if [ -z "${DB_PASS}" ] && [ -f "${ENV_FILE}" ]; then
  DB_PASS="$(leer_env DB_PASSWORD)"
fi
if [ -z "${DB_PASS}" ] || [ "${DB_PASS}" = "reemplaza-por-una-clave-fuerte" ]; then
  DB_PASS="$(generar_clave 24)"
  echo "==> DB_PASS no definida: se generó una clave aleatoria para PostgreSQL."
fi

echo "==> Paquetes del sistema"
sudo apt update -y
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib

echo "==> PostgreSQL: base de datos y usuario"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASS}';"
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
if [ ! -f "${ENV_FILE}" ]; then
  cp "${APP_DIR}/deploy/.env.produccion" "${ENV_FILE}"
  echo "Se creó .env desde deploy/.env.produccion — revisa IP_ELASTICA y DJANGO_ALLOWED_HOSTS."
fi

# Genera una SECRET_KEY real si el archivo sigue con el valor de ejemplo.
if grep -q '^DJANGO_SECRET_KEY=reemplaza-por-una-clave-larga-y-aleatoria' "${ENV_FILE}"; then
  SECRET_KEY="$(generar_clave 48)"
  sed -i "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${SECRET_KEY}|" "${ENV_FILE}"
  echo "Se generó DJANGO_SECRET_KEY aleatoria en .env."
fi

# Mantén sincronizada la clave de PostgreSQL con la del .env.
if grep -q '^DB_PASSWORD=' "${ENV_FILE}"; then
  sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${DB_PASS}|" "${ENV_FILE}"
else
  printf '\nDB_PASSWORD=%s\n' "${DB_PASS}" >> "${ENV_FILE}"
fi

echo "==> Migraciones y estáticos"
cd "${APP_DIR}"
"${APP_DIR}/env/bin/python" manage.py migrate --noinput
"${APP_DIR}/env/bin/python" manage.py collectstatic --noinput

if [ "${SEED_DEMO_DATA}" = "true" ]; then
  echo "==> Datos de demostración (SEED_DEMO_DATA=true)"
  "${APP_DIR}/env/bin/python" seed_data.py || true
  echo "AVISO: cambia las claves de los usuarios demo antes de exponer la instancia."
else
  echo "==> Seed omitido (recomendado en producción)."
  echo "    Crea el administrador con: ${APP_DIR}/env/bin/python manage.py createsuperuser"
fi

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
echo "HTTPS:   cuando configures un certificado en Nginx, cambia"
echo "         DJANGO_SECURE_COOKIES=True en .env y ejecuta:"
echo "         sudo systemctl restart gunicorn"
