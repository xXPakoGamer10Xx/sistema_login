# Guía de Despliegue con Docker

Este sistema está configurado para ejecutarse fácilmente con Docker y Docker Compose.

## Requisitos previos

- Docker instalado y corriendo.
- Git (para clonar/actualizar el repositorio).

## Instrucciones de Inicio Rápido

1. **Actualizar el código (si ya lo tienes clonado):**
   ```bash
   git pull origin main
   ```

2. **Iniciar el sistema:**
   Simplemente ejecuta este comando en la carpeta del proyecto:
   ```bash
   docker-compose up --build -d
   ```
   - `--build`: Asegura que se construya la imagen con los últimos cambios.
   - `-d`: Ejecuta los contenedores en segundo plano (detached mode).

3. **Acceder a la aplicación:**
   Abre tu navegador y ve a:
   [http://localhost:5001](http://localhost:5001)

## Comandos Útiles

- **Detener el sistema:**
  ```bash
  docker-compose down
  ```

- **Ver logs (para solucionar problemas):**
  ```bash
  docker-compose logs -f
  ```

- **Reiniciar todo (si algo falla):**
  ```bash
  docker-compose down
  docker-compose up --build -d
  ```

## Notas Importantes

- **Datos:** La base de datos (`instance/sistema_academico.db`) y los archivos subidos (`static/uploads`) se guardan en tu máquina local gracias a los "volúmenes" de Docker. **No se perderán** si detienes o reinicias el contenedor.
- **Configuración:** Al iniciar, el sistema ejecutará automáticamente `init_config.py` para asegurar que todo esté listo.
