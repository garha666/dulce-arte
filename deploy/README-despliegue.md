# Despliegue en AWS EC2 — Dulce Arte

Guía basada en la receta del ramo (Gunicorn + Nginx) **ampliada con PostgreSQL**, que es lo
que exige la rúbrica.

> Atajo: si ya clonaste el proyecto en `~/apps/dulce-arte`, puedes ejecutar
> `bash deploy/instalar.sh` y saltar a la sección 8 (el script hace los pasos 2 a 7).
> Antes revisa `deploy/.env.produccion` y reemplaza la IP y la `SECRET_KEY`.

## 1. Instancia EC2

- AMI: **Ubuntu Server 22.04 LTS**, tipo `t2.micro` o `t3.micro`.
- Security Group entrante: **SSH 22** (tu IP), **HTTP 80** (0.0.0.0/0), opcional HTTPS 443.
- Asignar **Elastic IP** y asociarla a la instancia (para que no cambie la IP).

```bash
ssh -i claves.pem ubuntu@IP_ELASTICA
```

## 2. Paquetes del sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx git postgresql postgresql-contrib -y
```

## 3. PostgreSQL en la instancia

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE dulcearte;
CREATE USER dulcearte WITH PASSWORD 'dulcearte2026';
ALTER ROLE dulcearte SET client_encoding TO 'utf8';
ALTER ROLE dulcearte SET default_transaction_isolation TO 'read committed';
ALTER ROLE dulcearte SET timezone TO 'America/Santiago';
GRANT ALL PRIVILEGES ON DATABASE dulcearte TO dulcearte;
\q
```

> En PostgreSQL 15+ además: `sudo -u postgres psql -d dulcearte -c "GRANT ALL ON SCHEMA public TO dulcearte;"`

## 4. Proyecto

```bash
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/USUARIO/dulce-arte.git
cd dulce-arte
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Crear `.env` en la instancia (no se sube al repo):

```
DJANGO_SECRET_KEY=<clave larga y aleatoria>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=IP_ELASTICA,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://IP_ELASTICA
DB_ENGINE=postgresql
DB_NAME=dulcearte
DB_USER=dulcearte
DB_PASSWORD=dulcearte2026
DB_HOST=127.0.0.1
DB_PORT=5432
```

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python seed_data.py           # opcional, datos de demostración
```

## 5. Gunicorn

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl status gunicorn
```

## 6. Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dulcearte
sudo ln -s /etc/nginx/sites-available/dulcearte /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

## 7. Permisos (error típico 502 / 13 Permission denied)

```bash
sudo usermod -aG www-data ubuntu
sudo usermod -aG ubuntu www-data
sudo chmod 750 /home/ubuntu
sudo chmod 770 /home/ubuntu/apps/dulce-arte
sudo chown ubuntu:www-data /home/ubuntu/apps/dulce-arte/dulcearte.sock
sudo chmod 660 /home/ubuntu/apps/dulce-arte/dulcearte.sock
sudo systemctl restart gunicorn nginx
```

Verificación:

```bash
curl --unix-socket /home/ubuntu/apps/dulce-arte/dulcearte.sock http://localhost/ -I
namei -l /home/ubuntu/apps/dulce-arte/dulcearte.sock
```

## 8. Prueba final

Abrir en el navegador:

- `http://IP_ELASTICA/` → login
- `http://IP_ELASTICA/admin/` → Django Admin con estilos (estáticos servidos por Nginx)
- `http://IP_ELASTICA/api/` → navegador de DRF

Si el Admin aparece sin CSS, revisar `STATIC_ROOT`, `collectstatic` y el bloque `location /static/`.

## Errores frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| 502 Bad Gateway | socket no creado | revisar `gunicorn.service` y `systemctl status gunicorn` |
| 400 Bad Request | falta la IP en `ALLOWED_HOSTS` | agregar la Elastic IP al `.env` y reiniciar Gunicorn |
| `(13) Permission denied` | Nginx no puede leer el socket | `chown ubuntu:www-data` + `chmod 660` |
| Admin sin estilos | no se ejecutó `collectstatic` | ejecutarlo y revisar `location /static/` |
| `connection refused` a la BD | PostgreSQL detenido | `sudo systemctl restart postgresql` |
