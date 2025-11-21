# Sistema de Login y Registro Académico

Sistema web desarrollado en Python con Flask que implementa un sistema de autenticación con diferentes roles de usuario: Administrador, Jefe de Carrera, Profesor de Tiempo Completo y Profesor por Asignatura.

## Características

- **Sistema de autenticación seguro** con encriptación de contraseñas
- **Múltiples roles de usuario**:
  - Administrador: Acceso completo al sistema
  - Jefe de Carrera: Gestión académica y de profesores
  - Profesor de Tiempo Completo: Acceso completo a funciones docentes
  - Profesor por Asignatura: Acceso limitado a materias asignadas
- **Interfaz moderna** con Bootstrap 5
- **Base de datos SQLite** (fácil de configurar)
- **Formularios con validación** automática
- **Dashboard personalizado** según el rol del usuario

## Instalación

### Requisitos previos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd sistema_login
   ```

2. **Crear un entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   
   # En macOS/Linux:
   source venv/bin/activate
   
   # En Windows:
   venv\Scripts\activate
   ```

3. **Instalar las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

5. **Abrir en el navegador**
   ```
   http://localhost:5000
   ```

## Uso del Sistema

### Usuario Administrador por Defecto
Al ejecutar la aplicación por primera vez, se crea automáticamente un usuario administrador:
- **Usuario**: `admin`
- **Contraseña**: `admin123`
- **Rol**: Administrador

### Registro de Nuevos Usuarios

1. Visita `http://localhost:5000/register`
2. Completa el formulario con:
   - Nombre y apellido
   - Usuario único
   - Email válido
   - Teléfono (opcional)
   - Contraseña (mínimo 6 caracteres)
   - Selecciona el rol:
     - **Administrador**: Acceso completo
     - **Jefe de Carrera**: Gestión académica
     - **Profesor**: Selecciona entre tiempo completo o por asignatura

### Funcionalidades por Rol

#### Administrador
- Gestión completa de usuarios
- Configuración del sistema
- Reportes generales
- Administración de seguridad

#### Jefe de Carrera
- Gestión de profesores de la carrera
- Administración del plan de estudios
- Gestión de horarios académicos
- Reportes académicos específicos

#### Profesor de Tiempo Completo
- Gestión de materias asignadas
- Registro de calificaciones
- Control de asistencia
- Acceso a funciones de investigación

#### Profesor por Asignatura
- Gestión de materias específicas asignadas
- Registro de calificaciones
- Control de asistencia
- Acceso limitado (solo materias asignadas)

## Estructura del Proyecto

```
sistema_login/
├── app.py                 # Aplicación principal Flask
├── models.py              # Modelos de base de datos
├── forms.py               # Formularios WTF
├── requirements.txt       # Dependencias de Python
├── README.md             # Este archivo
├── templates/            # Plantillas HTML
│   ├── base.html         # Plantilla base
│   ├── index.html        # Página principal
│   ├── login.html        # Página de login
│   ├── register.html     # Página de registro
│   └── dashboard.html    # Dashboard de usuario
└── static/               # Archivos estáticos
    └── css/
        └── style.css     # Estilos personalizados
```

## Configuración

### Variables de Configuración (app.py)
- `SECRET_KEY`: Cambia esta clave en producción
- `SQLALCHEMY_DATABASE_URI`: Configuración de base de datos
- Debug mode: Desactiva en producción

### Base de Datos
El sistema utiliza SQLite por defecto. La base de datos se crea automáticamente en `sistema_academico.db`.

## Personalización

### Agregar Nuevos Campos
1. Modifica el modelo `User` en `models.py`
2. Actualiza los formularios en `forms.py`
3. Modifica las plantillas HTML correspondientes

### Cambiar Estilos
- Modifica `static/css/style.css` para personalizar la apariencia
- Las plantillas usan Bootstrap 5 para el diseño responsivo

### Agregar Nuevas Rutas
1. Define nuevas rutas en `app.py`
2. Crea las plantillas correspondientes en `templates/`
3. Agrega validaciones de roles si es necesario

## Seguridad

- Las contraseñas se almacenan encriptadas usando Werkzeug
- Validación de formularios en el servidor
- Control de acceso basado en roles
- Protección CSRF con Flask-WTF

## Producción

### Despliegue en Servidor Linux (Ubuntu/Debian)

#### 1. Preparar el Servidor

```bash
# Actualizar sistema e instalar dependencias
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential \
    libssl-dev libffi-dev python3-dev nginx

# Instalar Gunicorn (servidor WSGI para producción)
# Se instalará dentro del venv en el siguiente paso
```

#### 2. Configurar la Aplicación

```bash
# Clonar el proyecto (o subir archivos vía SCP/FTP)
cd /opt
sudo git clone <tu-repositorio-url> sistema_login
sudo chown -R $USER:$USER sistema_login
cd sistema_login

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias (incluyendo Gunicorn)
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Inicializar configuración del sistema
python init_config.py

# (Opcional) Poblar base de datos con datos de ejemplo
# NOTA: Requiere que exista un usuario 'admin' primero
python instance/poblar.py
```

#### 3. Configurar Variables de Entorno

```bash
# Crear archivo .env (NO subir a git)
cat > .env << 'EOF'
SECRET_KEY=tu_clave_super_secreta_generada_aleatoriamente_aqui
FLASK_ENV=production
DATABASE_URL=sqlite:///instance/sistema_academico.db
EOF

# Asegurar permisos
chmod 600 .env
```

**Importante**: Modifica `app.py` para leer `SECRET_KEY` desde variables de entorno:
```python
import os
from dotenv import load_dotenv

load_dotenv()

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'clave-por-defecto-insegura'
```

#### 4. Configurar Systemd (Inicio Automático)

Crear archivo de servicio:
```bash
sudo nano /etc/systemd/system/sistema-login.service
```

Contenido del archivo:
```ini
[Unit]
Description=Sistema Login - Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/sistema_login
Environment="PATH=/opt/sistema_login/venv/bin"
EnvironmentFile=/opt/sistema_login/.env
ExecStart=/opt/sistema_login/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ajustar permisos y habilitar servicio:
```bash
# Dar permisos al directorio
sudo chown -R www-data:www-data /opt/sistema_login

# Recargar systemd y habilitar servicio
sudo systemctl daemon-reload
sudo systemctl enable sistema-login.service
sudo systemctl start sistema-login.service

# Verificar estado
sudo systemctl status sistema-login.service
```

#### 5. Configurar Nginx (Proxy Inverso)

Crear configuración de sitio:
```bash
sudo nano /etc/nginx/sites-available/sistema-login
```

Contenido del archivo:
```nginx
server {
    listen 80;
    server_name tu-dominio.com;  # Cambiar por tu dominio o IP

    # Logs
    access_log /var/log/nginx/sistema-login-access.log;
    error_log /var/log/nginx/sistema-login-error.log;

    # Archivos estáticos
    location /static {
        alias /opt/sistema_login/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy a Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Limitar tamaño de subida de archivos (para fotos de perfil)
    client_max_body_size 10M;
}
```

Activar sitio y reiniciar Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/sistema-login /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar configuración
sudo systemctl restart nginx
```

#### 6. Configurar HTTPS con Let's Encrypt (Recomendado)

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado SSL (reemplazar email y dominio)
sudo certbot --nginx -d tu-dominio.com --email tu@email.com --agree-tos --no-eff-email

# Renovación automática (ya configurada por defecto)
sudo certbot renew --dry-run
```

#### 7. Configurar Backups Automáticos

```bash
# Crear script de backup
sudo nano /usr/local/bin/backup-sistema-login.sh
```

Contenido:
```bash
#!/bin/bash
cd /opt/sistema_login
source venv/bin/activate
python backup_manager.py auto
```

Dar permisos y configurar cron:
```bash
sudo chmod +x /usr/local/bin/backup-sistema-login.sh

# Editar crontab
sudo crontab -e

# Agregar línea (backup diario a las 2 AM)
0 2 * * * /usr/local/bin/backup-sistema-login.sh
```

### Checklist de Producción

Antes de poner en producción, verifica:

- [x] `SECRET_KEY` cambiada por una clave segura (mínimo 32 caracteres aleatorios)
- [x] Modo debug desactivado (`FLASK_ENV=production`)
- [x] Base de datos con backups configurados
- [x] Gunicorn instalado y corriendo con systemd
- [x] Nginx configurado como proxy inverso
- [x] HTTPS/SSL configurado con Let's Encrypt
- [x] Firewall configurado (ufw):
  ```bash
  sudo ufw allow 22/tcp    # SSH
  sudo ufw allow 80/tcp    # HTTP
  sudo ufw allow 443/tcp   # HTTPS
  sudo ufw enable
  ```
- [x] Logs configurados y rotación activa
- [x] Permisos de archivos correctos (`www-data:www-data`)
- [x] Variables de entorno en `.env` (no en git)
- [x] Backups automáticos configurados
- [x] Monitoreo del servicio activo

### Comandos Útiles de Producción

```bash
# Ver logs del servicio
sudo journalctl -u sistema-login.service -f

# Reiniciar servicio
sudo systemctl restart sistema-login.service

# Ver logs de Nginx
sudo tail -f /var/log/nginx/sistema-login-error.log

# Ejecutar backup manual
cd /opt/sistema_login && source venv/bin/activate && python backup_manager.py manual

# Ver estado del sistema
sudo systemctl status sistema-login.service nginx
```

## Solución de Problemas

### Error de importación de módulos
```bash
pip install -r requirements.txt
```

### Base de datos no se crea
Verifica que tengas permisos de escritura en el directorio del proyecto.

### Puerto en uso
Cambia el puerto en `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

## Contribuir

1. Fork del proyecto
2. Crea una rama para tu feature
3. Commit de tus cambios
4. Push a la rama
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT.