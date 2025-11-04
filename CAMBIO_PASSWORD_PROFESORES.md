# Funcionalidad de Cambio de Contraseña para Usuarios

## Descripción
Esta funcionalidad permite al administrador cambiar la contraseña de cualquier usuario en el sistema (profesores, jefes de carrera, e incluso otros administradores). Es útil cuando un usuario olvida su contraseña o desea cambiarla por razones de seguridad.

## Ubicación de la Funcionalidad

La funcionalidad está disponible en **dos módulos**:

### 1. Módulo de Gestión de Profesores
- **Ruta**: `/admin/profesores`
- **Acceso**: Botón "Cambiar Contraseña" en los detalles expandibles de cada profesor
- **Función específica**: Solo para usuarios con rol de profesor (completo o asignatura)

### 2. Módulo de Gestión de Usuarios
- **Ruta**: `/admin/usuarios`
- **Acceso**: Botón de llave (🔑) en la fila de acciones de cada usuario
- **Función general**: Para cualquier usuario del sistema

## Características Implementadas

### 1. Formulario de Cambio de Contraseña (`CambiarPasswordProfesorForm`)
- **Ubicación**: `forms.py`
- **Campos**:
  - `nueva_password`: Campo para ingresar la nueva contraseña (mínimo 6 caracteres)
  - `confirmar_password`: Campo para confirmar la nueva contraseña
- **Validaciones**:
  - Contraseña obligatoria
  - Longitud mínima de 6 caracteres
  - Confirmación de contraseña debe coincidir con la nueva contraseña

### 2. Ruta de Cambio de Contraseña
- **Endpoints**: 
  - `/admin/profesores/<int:id>/cambiar-password` (específico para profesores)
  - `/admin/usuario/<int:id>/cambiar-password` (general para cualquier usuario)
- **Métodos**: GET, POST
- **Acceso**: Solo administradores
- **Funcionalidad**:
  - Valida que el usuario tenga permisos de administrador
  - Para la ruta de profesores: verifica que el usuario seleccionado sea un profesor
  - Para la ruta de usuarios: permite cambiar contraseña de cualquier usuario
  - Permite cambiar la contraseña del usuario
  - Muestra mensajes de éxito o error

### 3. Interfaz de Usuario
- **Plantillas**: 
  - `templates/admin/cambiar_password_profesor.html` (para profesores)
  - `templates/admin/cambiar_password_usuario.html` (para usuarios en general)
- **Características**:
  - Muestra información del usuario (nombre, usuario, email, tipo/rol)
  - Formulario con campos de contraseña
  - Botón para mostrar/ocultar contraseña
  - Validación en tiempo real de coincidencia de contraseñas
  - Mensaje de advertencia sobre informar al usuario
  - Botones de cancelar y guardar

### 4. Integración en Listas de Usuarios
- **En Gestión de Profesores** (`templates/admin/profesores.html`):
  - Botón "Cambiar Contraseña" en la sección expandible de cada profesor
  - Color amarillo (warning) para destacar la importancia de la acción
  
- **En Gestión de Usuarios** (`templates/admin/usuarios.html`):
  - Botón con icono de llave (🔑) en la fila de acciones
  - Integrado junto a editar, activar/desactivar y eliminar
  - Tooltip explicativo "Cambiar Contraseña"

## Flujo de Uso

### Opción 1: Desde Gestión de Profesores

1. **Acceso a la Funcionalidad**:
   - El administrador navega a "Gestión de Profesores"
   - Hace clic en un profesor para ver sus detalles
   - Selecciona el botón "Cambiar Contraseña"

2. **Cambio de Contraseña**:
   - El sistema muestra la información del profesor
   - El administrador ingresa la nueva contraseña dos veces
   - El sistema valida que las contraseñas coincidan
   - Al guardar, la contraseña se actualiza en la base de datos

3. **Confirmación**:
   - El sistema muestra un mensaje de éxito
   - Redirige a la lista de profesores
   - El profesor puede usar la nueva contraseña inmediatamente

### Opción 2: Desde Gestión de Usuarios

1. **Acceso a la Funcionalidad**:
   - El administrador navega a "Gestión de Usuarios"
   - Localiza al usuario en la tabla
   - Hace clic en el botón de llave (🔑) en la columna de acciones

2. **Cambio de Contraseña**:
   - El sistema muestra la información del usuario
   - El administrador ingresa la nueva contraseña dos veces
   - El sistema valida que las contraseñas coincidan
   - Al guardar, la contraseña se actualiza en la base de datos

3. **Confirmación**:
   - El sistema muestra un mensaje de éxito
   - Redirige a la lista de usuarios
   - El usuario puede usar la nueva contraseña inmediatamente

## Seguridad

- ✅ **Acceso Restringido**: Solo administradores pueden cambiar contraseñas
- ✅ **Validación de Roles**: Verifica que el usuario sea un profesor
- ✅ **Hash de Contraseña**: La contraseña se almacena hasheada mediante el modelo User
- ✅ **Validación de Formulario**: Verifica longitud y coincidencia de contraseñas
- ✅ **Mensajes de Advertencia**: Informa al administrador que debe comunicar la nueva contraseña

## Mejoras Futuras Sugeridas

1. **Generador de Contraseñas**: Opción para generar contraseñas aleatorias seguras
2. **Envío por Email**: Enviar automáticamente la nueva contraseña al profesor por correo
3. **Historial de Cambios**: Registrar cuándo y quién cambió la contraseña
4. **Contraseña Temporal**: Opción de crear contraseña temporal que debe cambiarse al primer inicio de sesión
5. **Notificación al Profesor**: Alerta automática al profesor cuando su contraseña es cambiada
6. **Requisitos de Complejidad**: Agregar validaciones para contraseñas más seguras (mayúsculas, números, símbolos)

## Código Relacionado

### Backend (app.py)
- **Ruta para profesores**: Función `cambiar_password_profesor(id)` - línea ~2178
- **Ruta para usuarios**: Función `cambiar_password_usuario(id)` - línea ~2874

### Formularios (forms.py)
- **Formulario**: Clase `CambiarPasswordProfesorForm` - línea ~863
  - Utilizado tanto para profesores como para usuarios en general

### Plantillas
- **Para profesores**: `templates/admin/cambiar_password_profesor.html`
- **Para usuarios**: `templates/admin/cambiar_password_usuario.html`
- **Integración en profesores**: `templates/admin/profesores.html` - Botón en detalles del profesor
- **Integración en usuarios**: `templates/admin/usuarios.html` - Botón en acciones de la tabla

### Modelos (models.py)
- **Propiedad password**: Setter en clase `User` - línea ~78
- **Método set_password**: Clase `User` - línea ~74
- **Método check_password**: Clase `User` - línea ~84

## Notas Importantes

- La contraseña se actualiza usando el setter del modelo `User`, que automáticamente hashea la contraseña
- El administrador debe informar la nueva contraseña al profesor de forma segura
- No se requiere la contraseña anterior para el cambio (privilegio de administrador)
- La funcionalidad solo está disponible para usuarios con rol de profesor (completo o asignatura)
