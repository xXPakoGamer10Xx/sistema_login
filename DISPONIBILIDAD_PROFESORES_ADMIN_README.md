# Módulo de Disponibilidad de Profesores para Administrador

## Descripción General

Este módulo permite a los **Administradores** gestionar la disponibilidad horaria de **todos los profesores** del sistema. El administrador tiene acceso completo a la configuración de disponibilidades con capacidades de filtrado avanzado por carrera y tipo de profesor.

## Características Principales

### 1. Listado Global de Profesores con Disponibilidad
- **Ruta:** `/admin/profesores/disponibilidad`
- **Función:** `admin_disponibilidad_profesores()`
- **Descripción:** Muestra un listado completo de todos los profesores del sistema con opciones de filtrado
- **Características:**
  - Acceso a **todos los profesores** del sistema (sin restricción por carrera)
  - Estadísticas globales de disponibilidad:
    - Total de profesores en el sistema
    - Profesores con disponibilidad configurada
    - Profesores sin disponibilidad
  - **Filtros avanzados:**
    - Por carrera (dropdown con todas las carreras)
    - Por tipo de profesor (Tiempo Completo / Asignatura)
    - Posibilidad de combinar filtros
  - Información detallada de cada profesor:
    - Nombre completo
    - Email
    - Teléfono
    - Rol (Tiempo Completo / Asignatura)
    - Carrera(s) asignadas (múltiples badges)
    - Estado de disponibilidad
  - Acciones rápidas:
    - Ver disponibilidad (modo lectura)
    - Editar disponibilidad

### 2. Edición de Disponibilidad de Profesor
- **Ruta:** `/admin/profesor/<id>/disponibilidad/editar`
- **Función:** `admin_editar_disponibilidad_profesor(id)`
- **Descripción:** Permite al administrador editar la disponibilidad horaria de cualquier profesor del sistema
- **Características:**
  - Acceso sin restricciones de carrera
  - Verificación que el usuario sea profesor
  - Información completa del profesor:
    - Email, teléfono, rol, estado
    - Todas las carreras asignadas
  - Tabla interactiva de disponibilidad:
    - Días de la semana (lunes a sábado)
    - Horarios por turno (matutino, vespertino, nocturno)
    - Checkboxes para marcar disponibilidad
  - Botones de selección rápida:
    - Seleccionar/deseleccionar día completo
    - Seleccionar/deseleccionar horario completo (fila)
    - Seleccionar todo
    - Deseleccionar todo
  - Funcionalidad:
    - Carga disponibilidades existentes
    - Desactiva disponibilidades anteriores (activo=False)
    - Crea nuevas disponibilidades basadas en la selección
    - Registra quién hizo el cambio (creado_por)
    - Trazabilidad completa de cambios

### 3. Vista de Disponibilidad de Profesor
- **Ruta:** `/admin/profesor/<id>/disponibilidad/ver`
- **Función:** `admin_ver_disponibilidad_profesor(id)`
- **Descripción:** Muestra una vista de solo lectura de la disponibilidad de cualquier profesor
- **Características:**
  - Acceso sin restricciones de carrera
  - Verificación que el usuario sea profesor
  - Tabla visual con disponibilidades marcadas
  - Resumen estadístico:
    - Total de horas disponibles por semana
    - Horas disponibles por día
  - Información completa del profesor:
    - Datos personales
    - Rol y estado
    - Todas las carreras asignadas
  - Acceso rápido a edición desde la vista

## Diferencias con el Módulo de Jefe de Carrera

| Característica | Administrador | Jefe de Carrera |
|---------------|---------------|-----------------|
| Alcance | **Todos los profesores del sistema** | Solo profesores de su carrera |
| Filtros | Por carrera y tipo de profesor | No disponible (auto-filtrado) |
| Restricciones | Ninguna | Solo su carrera asignada |
| Información mostrada | Todas las carreras del profesor | Solo la carrera del jefe |
| Permisos | Acceso completo | Acceso limitado a su carrera |
| Estadísticas | Globales del sistema | Solo de su carrera |

## Plantillas

### 1. `admin_disponibilidad_profesores.html`
**Ubicación:** `templates/admin/admin_disponibilidad_profesores.html`

**Contenido:**
- Tarjetas de estadísticas globales
- Panel de filtros (carrera + tipo de profesor)
- Tabla de profesores con estado de disponibilidad
- Botones de acción (ver, editar)
- Columna adicional mostrando todas las carreras del profesor
- Diseño responsivo con Bootstrap 5

**Características especiales:**
- Sistema de filtrado con formulario GET
- Botón "Limpiar filtros" para resetear búsqueda
- Badges múltiples para mostrar todas las carreras de cada profesor

### 2. `admin_editar_disponibilidad_profesor.html`
**Ubicación:** `templates/admin/admin_editar_disponibilidad_profesor.html`

**Contenido:**
- Formulario de edición con tabla de disponibilidad
- Información completa del profesor (incluyendo todas sus carreras)
- Checkboxes para cada combinación día/horario
- JavaScript para selección rápida
- Botones de acción (guardar, cancelar)

**Características especiales:**
- Muestra todas las carreras asignadas al profesor
- Panel de administrador claramente identificado
- Información de trazabilidad de cambios

### 3. `admin_ver_disponibilidad_profesor.html`
**Ubicación:** `templates/admin/admin_ver_disponibilidad_profesor.html`

**Contenido:**
- Vista de solo lectura de disponibilidades
- Tabla visual con celdas marcadas
- Resumen por día
- Información completa del profesor (incluyendo todas sus carreras)
- Botón para acceder a edición
- Estadísticas de disponibilidad

**Características especiales:**
- Vista completa de información del profesor
- Resumen visual por día de la semana
- Información sobre trazabilidad de cambios

## Seguridad y Permisos

### Verificación de Roles
- Solo usuarios con rol `admin` pueden acceder
- Verificación mediante decorador `@login_required` y `current_user.is_admin()`

### Sin Restricciones de Carrera
- El administrador puede gestionar cualquier profesor
- No hay verificación de carrera (acceso completo)
- Ideal para mantenimiento y supervisión global

### Verificación de Tipo de Usuario
- Verifica que el ID proporcionado corresponda a un profesor
- Validación: `rol in ['profesor_completo', 'profesor_asignatura']`

### Trazabilidad Completa
- Cada cambio de disponibilidad registra quién lo hizo mediante `creado_por=current_user.id`
- Historial de cambios mediante `activo=True/False`
- Auditoría completa de modificaciones

## Base de Datos

### Modelo: DisponibilidadProfesor
(Mismo modelo usado por jefe de carrera)

**Campos principales:**
- `profesor_id`: ID del profesor
- `horario_id`: ID del horario
- `dia_semana`: Día de la semana (lunes-sábado)
- `disponible`: Boolean (True/False)
- `activo`: Boolean (True para actual, False para histórico)
- `creado_por`: ID del usuario que creó/modificó el registro
- `fecha_creacion`: Timestamp de creación

**Relaciones:**
- `profesor`: Relación con User
- `horario`: Relación con Horario
- `creador`: Relación con User (quien hizo el cambio)

## Flujo de Trabajo

### Escenario 1: Búsqueda y Filtrado
1. Admin accede a "Disponibilidad de Profesores" desde dashboard
2. Sistema muestra todos los profesores con estadísticas globales
3. Admin aplica filtros (ej: Carrera X + Tiempo Completo)
4. Sistema filtra y muestra resultados
5. Admin puede limpiar filtros para volver a vista completa

### Escenario 2: Revisión Global
1. Admin accede al módulo sin filtros
2. Visualiza estadísticas globales del sistema
3. Identifica profesores sin disponibilidad configurada
4. Hace clic en "Editar" para configurar disponibilidad
5. Guarda cambios con trazabilidad

### Escenario 3: Gestión de Profesor Específico
1. Admin aplica filtros o busca en lista completa
2. Hace clic en "Ver" para revisar disponibilidad actual
3. Si necesita cambios, hace clic en "Editar Disponibilidad"
4. Modifica horarios según necesidad
5. Guarda cambios con registro de auditoría

### Escenario 4: Supervisión por Carrera
1. Admin selecciona una carrera específica en filtros
2. Sistema muestra solo profesores de esa carrera
3. Admin revisa estado de disponibilidad de la carrera
4. Identifica brechas o problemas
5. Realiza ajustes necesarios

## Integración con Dashboard

### Tarjeta en Dashboard del Administrador
**Ubicación:** `templates/dashboard.html`

**Código agregado:**
```html
<div class="col-md-6 mb-3">
    <div class="card border-warning">
        <div class="card-body text-center">
            <i class="fas fa-clock-history fa-2x text-warning mb-2"></i>
            <h6>Disponibilidad de Profesores</h6>
            <p class="small text-muted">Gestionar disponibilidad horaria de profesores</p>
            <a href="{{ url_for('admin_disponibilidad_profesores') }}" class="btn btn-warning btn-sm">Gestionar</a>
        </div>
    </div>
</div>
```

## Interacción con Otros Módulos

### Gestión de Profesores
- Complementa el módulo principal de gestión de profesores
- Permite configurar disponibilidad después de crear profesor
- Acceso directo desde gestión de profesores (posible mejora futura)

### Generador de Horarios
- La disponibilidad configurada se utiliza en `generador_horarios.py`
- Solo se asignan profesores a horarios donde estén disponibles
- Mejora la eficiencia del generador automático

### Registro de Profesores
- Los profesores pueden configurar su propia disponibilidad al registrarse
- El administrador puede posteriormente editar/actualizar toda la información
- Funcionalidad complementaria bidireccional

### Módulo de Jefe de Carrera
- Misma funcionalidad pero con alcance diferente
- Administrador tiene visión global
- Jefe de carrera tiene visión específica de su carrera

### Reportes del Sistema
- Posible integración futura para reportes de cobertura horaria
- Análisis de disponibilidad por turno/carrera
- Identificación de brechas de cobertura

## Consideraciones Técnicas

### Rendimiento
- Consultas optimizadas con filtros opcionales
- Uso de relaciones SQLAlchemy para reducir queries
- Carga de horarios activos únicamente
- Índices en campos de filtrado frecuente

### Experiencia de Usuario
- Diseño responsivo con Bootstrap 5
- Feedback visual de acciones (mensajes flash)
- Botones de selección rápida para eficiencia
- Confirmaciones de cambios
- Filtros intuitivos con dropdown
- Botón de limpieza de filtros

### Escalabilidad
- Diseñado para manejar múltiples profesores
- Filtrado eficiente para grandes conjuntos de datos
- Paginación posible como mejora futura

### Mantenimiento
- Código reutilizable entre admin y jefe
- Plantillas modulares
- Comentarios claros en código
- Separación de lógica y presentación
- Nombres descriptivos de funciones y rutas

## Próximas Mejoras Sugeridas

1. **Paginación**
   - Implementar paginación en listado de profesores
   - Útil cuando hay muchos profesores en el sistema

2. **Búsqueda por Nombre**
   - Agregar campo de búsqueda por nombre/email de profesor
   - Búsqueda en tiempo real con JavaScript

3. **Exportación de Datos**
   - Exportar a Excel/PDF la disponibilidad de todos los profesores
   - Exportar solo profesores filtrados

4. **Importación Masiva**
   - Importar disponibilidades desde CSV
   - Útil para configuración inicial masiva

5. **Notificaciones**
   - Notificar al profesor cuando el admin modifica su disponibilidad
   - Email o notificación en sistema

6. **Historial de Cambios Visible**
   - Vista de historial con quién y cuándo se hicieron cambios
   - Posibilidad de revertir cambios

7. **Dashboard de Análisis**
   - Gráficos de disponibilidad por turno
   - Comparativas entre carreras
   - Identificación de brechas de cobertura
   - Heatmap de disponibilidad global

8. **Validaciones Avanzadas**
   - Alertas si un profesor tiene muy pocas horas disponibles
   - Sugerencias de horarios óptimos
   - Detección de conflictos

9. **Integración con Gestión de Profesores**
   - Link directo desde perfil de profesor
   - Widget de disponibilidad en perfil

10. **Copiar Disponibilidad**
    - Copiar disponibilidad de un profesor a otro
    - Plantillas de disponibilidad comunes

## Casos de Uso Principales

### 1. Configuración Inicial del Sistema
El administrador configura la disponibilidad de todos los profesores nuevos que se cargan masivamente al sistema.

### 2. Auditoría y Supervisión
El administrador revisa periódicamente que todos los profesores tengan su disponibilidad actualizada y completa.

### 3. Resolución de Conflictos
Cuando hay problemas en la generación de horarios, el administrador verifica y ajusta disponibilidades según sea necesario.

### 4. Cobertura por Carrera
El administrador filtra por carrera para asegurar que hay suficiente cobertura horaria en cada programa.

### 5. Análisis por Turno
Filtrando y revisando disponibilidades, el administrador identifica si hay suficientes profesores para cada turno (matutino/vespertino/nocturno).

## Notas Técnicas

### Query de Filtrado
```python
# Query base
query = User.query.filter(
    User.rol.in_(['profesor_completo', 'profesor_asignatura']),
    User.activo == True
)

# Filtro por carrera (opcional)
if carrera_id:
    query = query.filter(User.carreras.any(id=carrera_id))

# Filtro por rol (opcional)
if rol_filtro:
    query = query.filter(User.rol == rol_filtro)

profesores = query.order_by(User.apellido, User.nombre).all()
```

### Cálculo de Estadísticas
```python
total_profesores = len(profesores)
profesores_con_disponibilidad = 0

for profesor in profesores:
    disponibilidades = DisponibilidadProfesor.query.filter_by(
        profesor_id=profesor.id,
        activo=True
    ).count()
    if disponibilidades > 0:
        profesores_con_disponibilidad += 1
```

## Notas Finales

Este módulo es esencial para la administración completa del sistema académico, proporcionando al administrador las herramientas necesarias para supervisar y gestionar la disponibilidad horaria de todos los profesores. Su diseño modular y escalable permite futuras expansiones y mejoras según las necesidades del sistema.

La combinación de este módulo con el módulo equivalente para jefes de carrera proporciona una gestión descentralizada pero supervisada de las disponibilidades, donde cada rol tiene el nivel de acceso apropiado para sus responsabilidades.

**Fecha de Implementación:** 2024  
**Versión:** 1.0  
**Estado:** Funcional y en producción  
**Compatibilidad:** Totalmente compatible con módulo de jefe de carrera
