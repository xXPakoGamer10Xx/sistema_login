# Sistema de Gestión Académica

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Último commit](https://img.shields.io/github/last-commit/xXPakoGamer10Xx/sistema_login)](https://github.com/xXPakoGamer10Xx/sistema_login/commits/main)
[![Issues](https://img.shields.io/github/issues/xXPakoGamer10Xx/sistema_login)](https://github.com/xXPakoGamer10Xx/sistema_login/issues)
[![Stars](https://img.shields.io/github/stars/xXPakoGamer10Xx/sistema_login?style=social)](https://github.com/xXPakoGamer10Xx/sistema_login/stargazers)
[![Forks](https://img.shields.io/github/forks/xXPakoGamer10Xx/sistema_login?style=social)](https://github.com/xXPakoGamer10Xx/sistema_login/network/members)

Aplicación web desarrollada con Flask para administrar carreras, materias, grupos, profesores y horarios académicos. Incluye generación automática de horarios, control de disponibilidad docente, importación/exportación de datos, respaldo de base de datos y autenticación por roles.

## Tabla de contenidos

- [Características](#características)
- [Stack tecnológico](#stack-tecnológico)
- [Requisitos](#requisitos)
- [Inicio rápido con Docker](#inicio-rápido-con-docker-recomendado)
- [Instalación local](#instalación-local)
- [Configuración de entorno](#configuración-de-entorno)
- [Usuario inicial](#usuario-inicial)
- [Comandos operativos](#comandos-operativos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Seguridad](#seguridad)
- [Despliegue en producción](#despliegue-en-producción-linux)
- [Licencia](#licencia)

## Características

- Generación automática de horarios con OR-Tools.
- Gestión de disponibilidad de profesores por día y bloque horario.
- Importación masiva de datos académicos (profesores, materias, carreras y asignaciones).
- Exportación de reportes y horarios en PDF/Excel.
- Sistema de backups con soporte de cifrado AES-256-GCM.
- Control de acceso por roles con flujos diferenciados para administración y personal docente.
- Interfaz web responsive con Bootstrap 5.

### Roles de usuario

| Rol | Alcance principal |
| --- | --- |
| Administrador | Gestión completa del sistema: usuarios, catálogos, horarios, configuración y backups |
| Jefe de carrera | Gestión académica de su carrera, asignaciones y reportes |
| Profesor tiempo completo | Consulta de carga asignada y administración de disponibilidad |
| Profesor por asignatura | Consulta de horarios/materias y administración de disponibilidad |

## Stack tecnológico

| Capa | Tecnología |
| --- | --- |
| Backend | Flask 2.3, Python 3.12 |
| Persistencia | SQLite + SQLAlchemy 2.x |
| Formularios y auth | Flask-WTF, WTForms, Flask-Login |
| Seguridad | Flask-Limiter, cryptography |
| Generación de horarios | Google OR-Tools |
| Exportación | ReportLab, xhtml2pdf, OpenPyXL |
| Despliegue | Gunicorn, Docker, Docker Compose |

## Requisitos

### Para ejecución con Docker

- Docker 24+ (o compatible con Compose v2)
- Docker Compose

### Para ejecución local

- Python 3.12 (recomendado)
- `pip`

## Inicio rápido con Docker (recomendado)

```bash
git clone https://github.com/xXPakoGamer10Xx/sistema_login.git
cd sistema_login
docker compose up --build
```

Aplicación disponible en: `http://localhost:5001`

Notas de arranque del contenedor:

- Si no existe `.env`, se genera automáticamente con una `SECRET_KEY` segura.
- Se crean carpetas operativas (`instance`, `logs`, `backups`, `static/uploads`, `horarios`).
- Se ejecuta inicialización del sistema y migraciones al iniciar.

## Instalación local

```bash
git clone https://github.com/xXPakoGamer10Xx/sistema_login.git
cd sistema_login

python3 -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

python init_config.py
python migrate_remove_password_temporal.py
python app.py
```

Aplicación disponible en: `http://localhost:5001`

## Configuración de entorno

Variables soportadas en `.env`:

| Variable | Descripción | Valor por defecto |
| --- | --- | --- |
| `SECRET_KEY` | Clave de sesión y CSRF | Se genera automáticamente si no está definida |
| `DATABASE_URL` | URL de conexión de base de datos | `sqlite:///sistema_academico.db` |
| `FLASK_DEBUG` | Modo debug (`0`/`1`) | `0` |
| `BACKUP_ENCRYPTION_KEY` | Clave hex de 32 bytes para cifrar backups | Vacía (sin cifrado) |

Generar claves:

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# BACKUP_ENCRYPTION_KEY (AES-256)
python backup_manager.py genkey
```

## Usuario inicial

En la primera ejecución se crea un usuario administrador por defecto:

| Campo | Valor |
| --- | --- |
| Usuario | `admin` |
| Contraseña | `admin123` |
| Rol | Administrador |

Recomendación: cambiar la contraseña inmediatamente después del primer acceso.

## Comandos operativos

```bash
# Backups
python backup_manager.py auto
python backup_manager.py manual
python backup_manager.py status
python backup_manager.py decrypt backups/archivo.enc

# Datos de prueba / limpieza
python instance/poblar.py
python instance/limpiar_base_datos.py
```

## Estructura del proyecto

```text
sistema_login/
├── app.py
├── models.py
├── forms.py
├── utils.py
├── generador_horarios_mejorado.py
├── backup_manager.py
├── init_config.py
├── migrate_remove_password_temporal.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example
├── seguridad.md
├── instance/
├── templates/
├── static/
├── logs/
├── backups/
└── horarios/
```

## Seguridad

El proyecto incluye controles de seguridad a nivel de aplicación y despliegue, entre ellos:

- Protección CSRF en formularios.
- Rate limiting en endpoints sensibles (por ejemplo login/registro).
- Security headers HTTP.
- Cookies de sesión seguras (`HttpOnly`, `SameSite=Lax`) y expiración de sesión.
- Validación de contraseñas y controles de autenticación.
- Validación de uploads (tipo/tamaño).
- Logging de auditoría.
- Contenedor Docker ejecutado como usuario no privilegiado.

Detalle técnico y checklist ampliado: `seguridad.md`.

## Despliegue en producción (Linux)

### Docker Compose

```bash
cp .env.example .env
# Editar .env con valores de producción

docker compose up --build -d
```

### Reverse proxy (Nginx)

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location /static {
        alias /opt/sistema_login/static;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    client_max_body_size 10M;
}
```

### HTTPS con Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT.
