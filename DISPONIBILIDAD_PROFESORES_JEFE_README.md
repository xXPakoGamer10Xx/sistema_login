# Módulo de Disponibilidad de Profesores para Jefe de Carrera

## Descripción General

Este módulo permite a los **Jefes de Carrera** gestionar la disponibilidad horaria de los profesores asignados a su carrera. Los jefes pueden ver, editar y consultar los horarios en los que cada profesor está disponible para impartir clases.

## Características Principales

### 1. Listado de Profesores con Disponibilidad
- **Ruta:** `/jefe-carrera/profesores/disponibilidad`
- **Función:** `disponibilidad_profesores_jefe()`
- **Descripción:** Muestra un listado completo de todos los profesores de la carrera del jefe actual
- **Características:**
  - Filtrado automático por carrera del jefe de carrera
  - Estadísticas de disponibilidad:
    - Total de profesores
    - Profesores con disponibilidad configurada
    - Profesores sin disponibilidad
  - Información detallada de cada profesor:
    - Nombre completo
    - Email
    - Teléfono
    - Rol (Tiempo Completo / Asignatura)
    - Estado de disponibilidad
  - Acciones rápidas:
    - Ver disponibilidad (modo lectura)
    - Editar disponibilidad

### 2. Edición de Disponibilidad de Profesor
- **Ruta:** `/jefe-carrera/profesor/<id>/disponibilidad/editar`
- **Función:** `editar_disponibilidad_profesor_jefe(id)`
- **Descripción:** Permite al jefe de carrera editar la disponibilidad horaria de un profesor específico
- **Características:**
  - Verificación de permisos (solo profesores de su carrera)
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

### 3. Vista de Disponibilidad de Profesor
- **Ruta:** `/jefe-carrera/profesor/<id>/disponibilidad/ver`
- **Función:** `ver_disponibilidad_profesor_jefe(id)`
- **Descripción:** Muestra una vista de solo lectura de la disponibilidad de un profesor
- **Características:**
  - Verificación de permisos (solo profesores de su carrera)
  - Tabla visual con disponibilidades marcadas
  - Resumen estadístico:
    - Total de horas disponibles por semana
    - Horas disponibles por día
  - Información del profesor:
    - Datos personales
    - Rol
    - Estado
  - Acceso rápido a edición desde la vista

## Plantillas

### 1. `disponibilidad_profesores.html`
**Ubicación:** `templates/jefe/disponibilidad_profesores.html`

**Contenido:**
- Tarjetas de estadísticas (total, con disponibilidad, sin disponibilidad)
- Tabla de profesores con estado de disponibilidad
- Botones de acción (ver, editar)
- Diseño responsivo con Bootstrap 5

### 2. `editar_disponibilidad_profesor.html`
**Ubicación:** `templates/jefe/editar_disponibilidad_profesor.html`

**Contenido:**
- Formulario de edición con tabla de disponibilidad
- Checkboxes para cada combinación día/horario
- JavaScript para selección rápida
- Botones de acción (guardar, cancelar)
- Información del profesor

### 3. `ver_disponibilidad_profesor.html`
**Ubicación:** `templates/jefe/ver_disponibilidad_profesor.html`

**Contenido:**
- Vista de solo lectura de disponibilidades
- Tabla visual con celdas marcadas
- Resumen por día
- Botón para acceder a edición
- Estadísticas de disponibilidad

## Seguridad y Permisos

### Verificación de Roles
- Solo usuarios con rol `jefe_carrera` pueden acceder
- Verificación mediante decorador `@login_required` y `current_user.is_jefe_carrera()`

### Verificación de Carrera
- El jefe solo puede gestionar profesores de su propia carrera
- Verificación mediante:
  ```python
  if not any(carrera.id == current_user.carrera_id for carrera in profesor.carreras):
      flash('No tienes permisos...', 'error')
      return redirect(...)
  ```

### Trazabilidad
- Cada cambio de disponibilidad registra quién lo hizo mediante `creado_por=current_user.id`
- Historial de cambios mediante `activo=True/False`

## Base de Datos

### Modelo: DisponibilidadProfesor
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

### Escenario 1: Ver Estado de Disponibilidad
1. Jefe accede a "Disponibilidad de Profesores" desde dashboard
2. Sistema muestra listado filtrado por carrera
3. Jefe visualiza estadísticas y estado de cada profesor
4. Jefe puede hacer clic en "Ver" para detalle

### Escenario 2: Editar Disponibilidad
1. Jefe hace clic en "Editar" para un profesor
2. Sistema carga disponibilidades existentes
3. Jefe marca/desmarca horarios disponibles
4. Jefe guarda cambios
5. Sistema:
   - Desactiva registros anteriores (activo=False)
   - Crea nuevos registros con la selección actual
   - Registra el cambio con creado_por
   - Muestra confirmación

### Escenario 3: Consulta Rápida
1. Jefe hace clic en "Ver" para un profesor
2. Sistema muestra vista de solo lectura
3. Jefe visualiza disponibilidad y estadísticas
4. Si necesita editar, hace clic en "Editar Disponibilidad"

## Integración con Dashboard

### Tarjeta en Dashboard del Jefe
**Ubicación:** `templates/dashboard.html`

**Código agregado:**
```html
<div class="col-md-6 mb-3">
    <div class="card border-warning">
        <div class="card-body text-center">
            <i class="fas fa-clock-history fa-2x text-warning mb-2"></i>
            <h6>Disponibilidad de Profesores</h6>
            <p class="small text-muted">Gestionar disponibilidad horaria de profesores</p>
            <a href="{{ url_for('disponibilidad_profesores_jefe') }}" class="btn btn-warning btn-sm">Gestionar</a>
        </div>
    </div>
</div>
```

## Interacción con Otros Módulos

### Generador de Horarios
- La disponibilidad configurada se utiliza en `generador_horarios.py`
- Solo se asignan profesores a horarios donde estén disponibles
- Mejora la eficiencia del generador automático

### Registro de Profesores
- Los profesores pueden configurar su propia disponibilidad al registrarse
- El jefe puede posteriormente editar/actualizar esta información

### Panel de Administrador
- El administrador tiene funcionalidad similar en su panel
- Puede gestionar disponibilidad de todos los profesores
- El jefe solo gestiona su carrera

## Consideraciones Técnicas

### Rendimiento
- Consultas optimizadas con filtros por carrera
- Uso de relaciones SQLAlchemy para reducir queries
- Carga de horarios activos únicamente

### Experiencia de Usuario
- Diseño responsivo con Bootstrap 5
- Feedback visual de acciones (mensajes flash)
- Botones de selección rápida para eficiencia
- Confirmaciones de cambios

### Mantenimiento
- Código reutilizable entre admin y jefe
- Plantillas modulares
- Comentarios claros en código
- Separación de lógica y presentación

## Próximas Mejoras Sugeridas

1. **Exportación de Disponibilidad**
   - Exportar a Excel/PDF la disponibilidad de todos los profesores

2. **Notificaciones**
   - Notificar al profesor cuando el jefe modifica su disponibilidad

3. **Historial de Cambios**
   - Vista de historial con quién y cuándo se hicieron cambios

4. **Validaciones Avanzadas**
   - Alertas si un profesor tiene muy pocas horas disponibles
   - Sugerencias de horarios óptimos

5. **Dashboard de Análisis**
   - Gráficos de disponibilidad por turno
   - Comparativas entre profesores
   - Identificación de brechas de cobertura

## Notas Finales

Este módulo es fundamental para la gestión eficiente de horarios académicos, permitiendo al jefe de carrera mantener actualizadas las disponibilidades de su equipo docente y optimizar la asignación de horarios.

**Fecha de Implementación:** 2024  
**Versión:** 1.0  
**Estado:** Funcional y en producción
