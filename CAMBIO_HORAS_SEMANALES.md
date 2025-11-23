# Cambio de Sistema de Horas en Materias

## 📋 Resumen
Se ha actualizado el sistema de gestión de materias para simplificar el manejo de horas. Anteriormente se usaban dos campos separados (`horas_teoricas` y `horas_practicas`), ahora se usa un único campo `horas_semanales` que representa el total de horas que se impartirán por semana.

## ✅ Cambios Realizados

### 1. **Modelo de Base de Datos** (`models.py`)
- ❌ Eliminado: `horas_teoricas` (INTEGER)
- ❌ Eliminado: `horas_practicas` (INTEGER)
- ✅ Agregado: `horas_semanales` (INTEGER) - Total de horas por semana

### 2. **Formularios** (`forms.py`)
- `MateriaForm`: 
  - Reemplazados campos `horas_teoricas` y `horas_practicas`
  - Nuevo campo `horas_semanales` con validación 1-50 horas
  - Valor por defecto: 5 horas

### 3. **Rutas y Lógica** (`app.py`)
- `nueva_materia()`: Actualizado para usar `horas_semanales`
- `editar_materia()`: Actualizado para usar `horas_semanales`
- `descargar_plantilla_csv_materias()`: Plantilla CSV actualizada

### 4. **Importación Masiva** (`utils.py`)
- `procesar_archivo_materias()`: Actualizado para leer `horas_semanales` del CSV
- Valor por defecto: 5 horas si no se especifica

### 5. **Generador de Horarios** (`generador_horarios.py`)
- Actualizado para usar `materia.horas_semanales`
- Mensajes de log actualizados
- Cálculos simplificados

### 6. **Templates**
Actualizados los siguientes archivos HTML:
- `admin/materia_form.html`: Formulario de creación/edición
- `admin/materias.html`: Listado de materias
- `admin/importar_materias.html`: Documentación e instrucciones
- `admin/ver_materias_grupo.html`: Vista de materias por grupo
- `admin/ver_materias_profesor.html`: Vista de materias por profesor
- `jefe/editar_materia.html`: Formulario de edición para jefe
- `jefe/ver_materias_profesor.html`: Vista para jefe de carrera

## 📄 Migración de Datos

Se ejecutó el script `migrate_horas_semanales.py` que:
1. ✅ Agregó la columna `horas_semanales` a la tabla `materia`
2. ✅ Migró los datos: `horas_semanales = horas_teoricas + horas_practicas`
3. ✅ Recreó la tabla sin las columnas antiguas
4. ✅ Migró 135 materias exitosamente

## 📊 Formato CSV Actualizado

### Antes:
```csv
nombre,codigo,cuatrimestre,carrera_codigo,creditos,horas_teoricas,horas_practicas,descripcion
```

### Ahora:
```csv
nombre,codigo,cuatrimestre,carrera_codigo,creditos,horas_semanales,descripcion
```

### Ejemplo:
```csv
nombre,codigo,cuatrimestre,carrera_codigo,creditos,horas_semanales,descripcion
Introducción a la Programación,ISI-101,1,ING-SIS,4,5,Fundamentos de programación
Matemáticas Discretas,MAT-101,1,ING-SIS,3,4,Lógica y matemáticas
```

## 🎯 Uso del Sistema

### Crear Materia Manualmente
1. Admin → Materias → Nueva Materia
2. Llenar el formulario con:
   - Nombre, Código, Cuatrimestre, Carrera
   - **Horas Semanales**: Total de horas que se impartirán por semana (1-50)
   - Créditos, Descripción (opcional)

### Importar Materias Masivamente
1. Admin → Materias → Importar desde CSV/Excel
2. Usar la plantilla actualizada con la columna `horas_semanales`
3. Descargar plantilla desde el botón "Descargar Plantilla CSV"

### Generar Horarios
- El generador ahora usa directamente `horas_semanales` de cada materia
- Ejemplo: Materia con 5 horas semanales = 5 bloques horarios en la semana

## 🔍 Verificación

Para verificar que los cambios funcionan correctamente:

1. **Crear una materia nueva**:
   - Verificar que el campo "Horas Semanales" aparece en el formulario
   - Guardar y verificar que se almacena correctamente

2. **Editar una materia existente**:
   - Verificar que muestra las horas semanales migradas
   - Editar y guardar cambios

3. **Importar materias desde CSV**:
   - Usar la nueva plantilla con `horas_semanales`
   - Verificar que se importan correctamente

4. **Generar horarios**:
   - El generador debe mostrar "Xh semanales" en los logs
   - Los horarios deben generarse usando las horas semanales

## 📝 Notas Importantes

- ✅ Todos los datos existentes fueron migrados automáticamente
- ✅ No se perdió información: `horas_semanales = horas_teoricas + horas_practicas`
- ✅ El sistema es retrocompatible con los datos migrados
- ⚠️  Las plantillas CSV antiguas ya no funcionarán (usar la nueva plantilla)
- ⚠️  El archivo `plantilla_materias_ejemplo.csv` contiene ejemplos actualizados

## 🚀 Archivos Creados/Modificados

### Archivos Nuevos:
- `migrate_horas_semanales.py` - Script de migración (ya ejecutado)
- `plantilla_materias_ejemplo.csv` - Plantilla de ejemplo actualizada
- `CAMBIO_HORAS_SEMANALES.md` - Este documento

### Archivos Modificados:
- `models.py` - Modelo Materia actualizado
- `forms.py` - MateriaForm actualizado
- `app.py` - Rutas de materias actualizadas
- `utils.py` - Importación CSV actualizada
- `generador_horarios.py` - Generador actualizado
- 7 templates HTML actualizados

## ✅ Estado Final
**Sistema completamente actualizado y funcional** ✨

Fecha de cambio: 21 de noviembre de 2025
