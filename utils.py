import pandas as pd
import io
import random
import string
from flask import make_response
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from datetime import datetime
from models import User, Carrera, db, Materia, HorarioAcademico

def generar_password_temporal():
    """Generar una contraseña temporal aleatoria de 8 caracteres"""
    caracteres = string.ascii_uppercase + string.ascii_lowercase + string.digits
    password = ''.join(random.choice(caracteres) for _ in range(8))
    return password

def procesar_archivo_profesores(archivo, carrera_defecto_id=None):
    """
    Procesar archivo CSV/Excel con datos de usuarios (profesores, jefes de carrera, admins)
    
    Formato esperado del archivo:
    - nombre, apellido_paterno, apellido_materno, email, telefono, rol, tipo_profesor (opcional), carrera_codigo (opcional)
    
    Roles soportados:
    - admin, administrador
    - jefe_carrera, jefe carrera
    - profesor (requiere tipo_profesor)
    
    Tipos de profesor (solo para rol=profesor):
    - profesor_completo, tiempo completo
    - profesor_asignatura, asignatura
    """
    resultado = {
        'exito': False,
        'procesados': 0,
        'creados': 0,
        'actualizados': 0,
        'errores': [],
        'usuarios_creados': [],  # Lista de usuarios con sus contraseñas temporales
        'mensaje': ''
    }
    
    try:
        # Leer archivo según extensión
        if archivo.filename.endswith('.csv'):
            # Intentar leer con diferentes codificaciones
            try:
                df = pd.read_csv(archivo, encoding='utf-8')
            except UnicodeDecodeError:
                archivo.seek(0)
                try:
                    df = pd.read_csv(archivo, encoding='latin-1')
                except:
                    archivo.seek(0)
                    df = pd.read_csv(archivo, encoding='iso-8859-1')
        else:  # Excel
            df = pd.read_excel(archivo)
        
        # Limpiar nombres de columnas (eliminar espacios y convertir a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas
        columnas_requeridas = ['nombre', 'apellido_paterno', 'apellido_materno', 'email', 'rol']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            columnas_encontradas = ', '.join(df.columns.tolist())
            resultado['mensaje'] = f"Columnas faltantes: {', '.join(columnas_faltantes)}. Columnas encontradas: {columnas_encontradas}"
            return resultado
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                resultado['procesados'] += 1
                
                # Validar datos básicos
                if pd.isna(row['nombre']) or pd.isna(row['apellido_paterno']) or pd.isna(row['apellido_materno']) or pd.isna(row['email']) or pd.isna(row['rol']):
                    resultado['errores'].append(f"Fila {index + 2}: Datos básicos incompletos (nombre, apellido_paterno, apellido_materno, email o rol vacío)")
                    continue
                
                # Validar y normalizar rol
                rol_input = str(row['rol']).lower().strip()
                rol_final = None
                tipo_profesor = None
                
                # Normalizar roles
                if rol_input in ['admin', 'administrador']:
                    rol_final = 'admin'
                elif rol_input in ['jefe_carrera', 'jefe carrera', 'jefe de carrera']:
                    rol_final = 'jefe_carrera'
                elif rol_input == 'profesor':
                    # Para profesor, se requiere tipo_profesor
                    if 'tipo_profesor' not in df.columns or pd.isna(row['tipo_profesor']):
                        resultado['errores'].append(f"Fila {index + 2}: Los profesores requieren especificar 'tipo_profesor' (profesor_completo o profesor_asignatura)")
                        continue
                    
                    tipo_profesor_input = str(row['tipo_profesor']).lower().strip()
                    if tipo_profesor_input in ['profesor_completo', 'tiempo completo', 'completo']:
                        tipo_profesor = 'profesor_completo'
                        rol_final = 'profesor_completo'
                    elif tipo_profesor_input in ['profesor_asignatura', 'asignatura', 'por asignatura']:
                        tipo_profesor = 'profesor_asignatura'
                        rol_final = 'profesor_asignatura'
                    else:
                        resultado['errores'].append(f"Fila {index + 2}: Tipo de profesor inválido (debe ser: profesor_completo, profesor_asignatura, tiempo completo o asignatura)")
                        continue
                else:
                    resultado['errores'].append(f"Fila {index + 2}: Rol inválido '{rol_input}' (debe ser: admin, jefe_carrera o profesor)")
                    continue
                
                # Determinar carrera(s) según el rol
                carreras = []
                carrera_id = None
                carreras_no_encontradas = []
                
                if rol_final == 'jefe_carrera':
                    # Jefe de carrera necesita UNA carrera
                    if 'carrera_codigo' in df.columns and not pd.isna(row['carrera_codigo']):
                        codigo_limpio = str(row['carrera_codigo']).split(',')[0].upper().strip()  # Solo la primera
                        carrera = Carrera.query.filter_by(codigo=codigo_limpio).first()
                        if carrera:
                            carrera_id = carrera.id
                        else:
                            resultado['errores'].append(f"Fila {index + 2}: Carrera '{codigo_limpio}' no encontrada para jefe de carrera")
                            continue
                    elif carrera_defecto_id:
                        carrera_id = carrera_defecto_id
                    else:
                        resultado['errores'].append(f"Fila {index + 2}: Jefes de carrera requieren especificar 'carrera_codigo'")
                        continue
                        
                elif rol_final in ['profesor_completo', 'profesor_asignatura']:
                    # Profesores pueden tener múltiples carreras
                    if 'carrera_codigo' in df.columns and not pd.isna(row['carrera_codigo']):
                        codigos_carrera = str(row['carrera_codigo']).split(',')
                        for codigo in codigos_carrera:
                            codigo_limpio = codigo.upper().strip()
                            carrera = Carrera.query.filter_by(codigo=codigo_limpio).first()
                            if carrera:
                                carreras.append(carrera)
                            else:
                                carreras_no_encontradas.append(codigo_limpio)
                        
                        if carreras_no_encontradas:
                            resultado['errores'].append(
                                f"Fila {index + 2} ({row['nombre']} {row['apellido_paterno']}): "
                                f"Carrera(s) no encontrada(s): {', '.join(carreras_no_encontradas)}. "
                                f"Verifica los códigos disponibles."
                            )
                            if not carreras:
                                continue
                    elif carrera_defecto_id:
                        carrera = Carrera.query.get(carrera_defecto_id)
                        if carrera:
                            carreras.append(carrera)
                    else:
                        resultado['errores'].append(f"Fila {index + 2}: Profesores requieren al menos una carrera. Agrega 'carrera_codigo' o selecciona una carrera por defecto.")
                        continue
                # Admin no requiere carrera
                
                # Construir apellido completo
                apellido_paterno = str(row['apellido_paterno']).strip().title()
                apellido_materno = str(row['apellido_materno']).strip().title()
                apellido_completo = f"{apellido_paterno} {apellido_materno}"
                
                # Verificar si el usuario ya existe por email
                usuario_existente = User.query.filter_by(email=str(row['email']).strip()).first()
                
                if usuario_existente:
                    # Actualizar usuario existente
                    usuario_existente.nombre = str(row['nombre']).strip().title()
                    usuario_existente.apellido = apellido_completo
                    usuario_existente.rol = rol_final
                    usuario_existente.telefono = str(row['telefono']).strip() if 'telefono' in df.columns and not pd.isna(row['telefono']) else None
                    
                    # Actualizar carreras según el rol
                    if rol_final in ['profesor_completo', 'profesor_asignatura']:
                        usuario_existente.carreras = carreras
                        usuario_existente.carrera_id = None
                    elif rol_final == 'jefe_carrera':
                        usuario_existente.carrera_id = carrera_id
                        usuario_existente.carreras = []
                    else:  # admin
                        usuario_existente.carreras = []
                        usuario_existente.carrera_id = None
                    
                    resultado['actualizados'] += 1
                else:
                    # Generar username único
                    nombre_base = str(row['nombre']).lower().strip()
                    apellido_base = apellido_paterno.lower()
                    username_base = f"{nombre_base}.{apellido_base}".replace(' ', '')
                    username = username_base
                    contador = 1
                    
                    while User.query.filter_by(username=username).first():
                        username = f"{username_base}{contador}"
                        contador += 1
                    
                    # Generar contraseña temporal aleatoria
                    password_temporal = generar_password_temporal()
                    
                    # Crear nuevo usuario
                    usuario = User(
                        username=username,
                        email=str(row['email']).strip(),
                        password=password_temporal,
                        nombre=str(row['nombre']).strip().title(),
                        apellido=apellido_completo,
                        rol=rol_final,
                        telefono=str(row['telefono']).strip() if 'telefono' in df.columns and not pd.isna(row['telefono']) else None,
                        carreras=carreras if rol_final in ['profesor_completo', 'profesor_asignatura'] else None,
                        carrera_id=carrera_id if rol_final == 'jefe_carrera' else None,
                        requiere_cambio_password=True,  # Forzar cambio de contraseña
                        password_temporal=password_temporal  # Guardar para mostrar al admin
                    )
                    
                    db.session.add(usuario)
                    resultado['creados'] += 1
                    
                    # Agregar a la lista de usuarios creados con sus contraseñas
                    resultado['usuarios_creados'].append({
                        'nombre': usuario.get_nombre_completo(),
                        'username': username,
                        'email': usuario.email,
                        'password': password_temporal,
                        'rol': usuario.get_rol_display()
                    })
                
            except Exception as e:
                resultado['errores'].append(f"Fila {index + 2}: Error al procesar - {str(e)}")
        
        # Guardar todos los cambios
        if resultado['creados'] > 0 or resultado['actualizados'] > 0:
            db.session.commit()
            resultado['exito'] = True
            resultado['mensaje'] = f"Importación completada: {resultado['creados']} creados, {resultado['actualizados']} actualizados"
        else:
            resultado['mensaje'] = "No se pudo procesar ningún registro correctamente"
        
    except pd.errors.EmptyDataError:
        resultado['mensaje'] = 'El archivo está vacío o no tiene datos válidos'
    except pd.errors.ParserError:
        resultado['mensaje'] = 'Error al leer el archivo. Verifica que sea un CSV válido'
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f"Error al leer archivo: {str(e)}"
    
    return resultado

def generar_pdf_profesores(carrera_id=None, incluir_contacto=True):
    """
    Generar PDF con lista de profesores
    """
    from models import User, Carrera
    
    # Crear buffer para el PDF
    buffer = io.BytesIO()
    
    # Configurar documento
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Centrado
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    # Contenido del PDF
    elements = []
    
    # Título
    if carrera_id:
        carrera = Carrera.query.get(carrera_id)
        titulo = f"Lista de Profesores - {carrera.nombre if carrera else 'Carrera'}"
    else:
        titulo = "Lista de Profesores - Todas las Carreras"
    
    elements.append(Paragraph(titulo, title_style))
    elements.append(Spacer(1, 12))
    
    # Información del reporte
    fecha_reporte = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(f"Fecha de generación: {fecha_reporte}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Obtener profesores
    query = User.query.filter(
        User.rol.in_(['profesor_completo', 'profesor_asignatura']),
        User.activo == True
    )
    
    # Filtrar por carrera si se especifica
    if carrera_id:
        carrera = Carrera.query.get(carrera_id)
        if carrera:
            # Filtrar profesores que tengan esta carrera (many-to-many)
            query = query.filter(User.carreras.contains(carrera))
    
    profesores = query.order_by(User.apellido, User.nombre).all()
    
    if not profesores:
        elements.append(Paragraph("No se encontraron profesores con los criterios especificados.", styles['Normal']))
    else:
        # Agrupar por carrera si se muestran todas
        if not carrera_id:
            profesores_por_carrera = {}
            for profesor in profesores:
                # Obtener todas las carreras del profesor
                if profesor.carreras:
                    for carrera in profesor.carreras:
                        if carrera.nombre not in profesores_por_carrera:
                            profesores_por_carrera[carrera.nombre] = []
                        if profesor not in profesores_por_carrera[carrera.nombre]:
                            profesores_por_carrera[carrera.nombre].append(profesor)
                else:
                    if 'Sin carrera' not in profesores_por_carrera:
                        profesores_por_carrera['Sin carrera'] = []
                    profesores_por_carrera['Sin carrera'].append(profesor)
            
            # Generar tabla para cada carrera
            for carrera_nombre, lista_profesores in sorted(profesores_por_carrera.items()):
                elements.append(Paragraph(carrera_nombre, heading_style))
                elements.append(Spacer(1, 6))
                
                # Crear tabla
                data = crear_tabla_profesores(lista_profesores, incluir_contacto)
                table = Table(data)
                table.setStyle(get_table_style())
                
                elements.append(table)
                elements.append(Spacer(1, 20))
        else:
            # Crear tabla única
            data = crear_tabla_profesores(profesores, incluir_contacto)
            table = Table(data)
            table.setStyle(get_table_style())
            
            elements.append(table)
    
    # Pie de página
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Sistema de Gestión Académica", styles['Normal']))
    
    # Generar PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def crear_tabla_profesores(profesores, incluir_contacto):
    """Crear datos de tabla para profesores"""
    if incluir_contacto:
        headers = ['Nombre', 'Tipo', 'Email', 'Teléfono', 'Fecha Registro']
        data = [headers]
        
        for profesor in profesores:
            data.append([
                profesor.get_nombre_completo(),
                'T.C.' if profesor.is_profesor_completo() else 'Asig.',
                profesor.email,
                profesor.telefono or 'N/A',
                profesor.fecha_registro.strftime('%d/%m/%Y')
            ])
    else:
        headers = ['Nombre', 'Tipo', 'Fecha Registro']
        data = [headers]
        
        for profesor in profesores:
            data.append([
                profesor.get_nombre_completo(),
                'Tiempo Completo' if profesor.is_profesor_completo() else 'Por Asignatura',
                profesor.fecha_registro.strftime('%d/%m/%Y')
            ])
    
    return data

def get_table_style():
    """Obtener estilo para las tablas"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

def generar_plantilla_csv():
    """Generar archivo CSV de plantilla para importar usuarios con ejemplos"""
    # Crear encabezados y ejemplos de datos
    contenido_csv = """nombre,apellido_paterno,apellido_materno,email,telefono,rol,tipo_profesor,carrera_codigo
Juan,Pérez,García,juan.perez@universidad.edu,555-1234,profesor,profesor_completo,IRO
María,González,López,maria.gonzalez@universidad.edu,555-5678,profesor,profesor_asignatura,IRO,ISC
Carlos,Rodríguez,Martínez,carlos.rodriguez@universidad.edu,555-9012,jefe_carrera,,IRO
Ana,López,Hernández,ana.lopez@universidad.edu,,profesor,asignatura,IRO,ISC,IND
Pedro,Sánchez,Ramírez,pedro.sanchez@universidad.edu,555-3456,admin,,
"""
    
    # Crear response
    response = make_response(contenido_csv)
    response.headers["Content-Disposition"] = "attachment; filename=plantilla_usuarios.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response

def procesar_archivo_materias(archivo, carrera_defecto_id=None, restar_horas=0):
    """
    Procesar archivo CSV/Excel con datos de materias
    
    Formato esperado del archivo:
    - nombre, codigo, cuatrimestre, carrera_codigo (opcional), creditos, horas_semanales, descripcion
    
    Args:
        archivo: Archivo CSV/Excel a procesar
        carrera_defecto_id: ID de carrera por defecto si no se especifica en el archivo
        restar_horas: Cantidad de horas a restar de horas_semanales de cada materia (default: 0)
    """
    resultado = {
        'exito': False,
        'mensaje': '',
        'procesados': 0,
        'creados': 0,
        'actualizados': 0,
        'errores': []
    }
    
    try:
        # Leer archivo según extensión
        if archivo.filename.endswith('.csv'):
            # Intentar leer con diferentes codificaciones
            try:
                df = pd.read_csv(archivo, encoding='utf-8')
            except UnicodeDecodeError:
                archivo.seek(0)  # Volver al inicio del archivo
                try:
                    df = pd.read_csv(archivo, encoding='latin-1')
                except:
                    archivo.seek(0)
                    df = pd.read_csv(archivo, encoding='iso-8859-1')
        else:  # Excel
            df = pd.read_excel(archivo)
        
        # Limpiar nombres de columnas (eliminar espacios y convertir a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas
        columnas_requeridas = ['nombre', 'codigo', 'cuatrimestre']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            # Mostrar las columnas que se encontraron para ayudar al usuario
            columnas_encontradas = ', '.join(df.columns.tolist())
            resultado['mensaje'] = f"Formato del archivo: El archivo debe contener las siguientes columnas obligatorias: {', '.join(columnas_requeridas)}. Las columnas opcionales son: carrera_codigo, creditos, horas_teoricas, horas_practicas, descripcion. Columnas encontradas en el archivo: {columnas_encontradas}"
            return resultado
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                resultado['procesados'] += 1
                
                # Validar datos básicos
                if pd.isna(row['nombre']) or pd.isna(row['codigo']) or pd.isna(row['cuatrimestre']):
                    resultado['errores'].append(f"Fila {index + 2}: Datos básicos incompletos (nombre, código o cuatrimestre vacío)")
                    continue
                
                # Validar cuatrimestre
                try:
                    cuatrimestre = int(row['cuatrimestre'])
                    if cuatrimestre < 0 or cuatrimestre > 10:
                        resultado['errores'].append(f"Fila {index + 2}: Cuatrimestre debe estar entre 0 y 10")
                        continue
                except:
                    resultado['errores'].append(f"Fila {index + 2}: Cuatrimestre inválido (debe ser un número)")
                    continue
                
                # Determinar carrera
                carrera_id = carrera_defecto_id
                if 'carrera_codigo' in df.columns and not pd.isna(row['carrera_codigo']):
                    carrera = Carrera.query.filter_by(codigo=str(row['carrera_codigo']).upper().strip()).first()
                    if carrera:
                        carrera_id = carrera.id
                    else:
                        resultado['errores'].append(f"Fila {index + 2}: Carrera con código '{row['carrera_codigo']}' no encontrada en el sistema")
                        continue
                
                if not carrera_id:
                    resultado['errores'].append(f"Fila {index + 2}: No se pudo determinar la carrera (especifica carrera_codigo o selecciona carrera por defecto)")
                    continue
                
                # Verificar si la materia ya existe (por código)
                codigo = str(row['codigo']).upper().strip()
                materia_existente = Materia.query.filter_by(codigo=codigo, carrera_id=carrera_id, activa=True).first()
                
                # Obtener valores opcionales
                creditos = int(row['creditos']) if 'creditos' in df.columns and not pd.isna(row['creditos']) else 3
                horas_semanales = int(row['horas_semanales']) if 'horas_semanales' in df.columns and not pd.isna(row['horas_semanales']) else 5
                
                # Aplicar resta de horas si se especificó
                if restar_horas > 0:
                    horas_semanales = max(1, horas_semanales - restar_horas)  # Mínimo 1 hora
                
                descripcion = str(row['descripcion']).strip() if 'descripcion' in df.columns and not pd.isna(row['descripcion']) and str(row['descripcion']).upper() != 'NULL' else None
                
                if materia_existente:
                    # Actualizar materia existente
                    materia_existente.nombre = str(row['nombre']).strip()
                    materia_existente.cuatrimestre = cuatrimestre
                    materia_existente.creditos = creditos
                    materia_existente.horas_semanales = horas_semanales
                    materia_existente.descripcion = descripcion
                    resultado['actualizados'] += 1
                else:
                    # Crear nueva materia
                    materia = Materia(
                        nombre=str(row['nombre']).strip(),
                        codigo=codigo,
                        cuatrimestre=cuatrimestre,
                        carrera_id=carrera_id,
                        creditos=creditos,
                        horas_semanales=horas_semanales,
                        descripcion=descripcion,
                        creado_por=1  # Admin por defecto
                    )
                    db.session.add(materia)
                    resultado['creados'] += 1
                
            except Exception as e:
                resultado['errores'].append(f"Fila {index + 2}: Error al procesar - {str(e)}")
        
        # Guardar todos los cambios
        if resultado['creados'] > 0 or resultado['actualizados'] > 0:
            db.session.commit()
            resultado['exito'] = True
            resultado['mensaje'] = 'Importación completada exitosamente'
        elif len(resultado['errores']) > 0:
            resultado['mensaje'] = 'No se pudo importar ninguna materia debido a errores'
        else:
            resultado['mensaje'] = 'No se encontraron registros para procesar'
        
    except pd.errors.EmptyDataError:
        resultado['mensaje'] = 'El archivo está vacío o no tiene datos válidos'
    except pd.errors.ParserError:
        resultado['mensaje'] = 'Error al leer el archivo. Verifica que sea un CSV válido'
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f"Error al leer el archivo: {str(e)}"
    
    return resultado

def generar_pdf_materias(materias, nombre_carrera=None, cuatrimestre=None, ciclo=None):
    """
    Generar PDF profesional con lista de materias, agrupadas por carrera.
    Usa los colores institucionales de la UPTex y el logo oficial.
    Cada carrera empieza en una hoja nueva.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import PageBreak, HRFlowable
    from collections import OrderedDict
    import os

    # Crear buffer para el PDF
    buffer = io.BytesIO()

    # Usar landscape para que quepa bien
    page_w, page_h = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=40,
        leftMargin=40,
        topMargin=90,
        bottomMargin=40
    )

    # ── Ruta del logo ──
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, 'static', 'images', 'logo.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(base_dir, 'Logo.png')
    logo_exists = os.path.exists(logo_path)

    # ── Colores institucionales UPTex ──
    COLOR_TEAL = colors.HexColor('#00847C')
    COLOR_TEAL_DARK = colors.HexColor('#006B65')
    COLOR_NAVY = colors.HexColor('#1B2A4A')
    COLOR_HEADER_BG = colors.HexColor('#00847C')
    COLOR_HEADER_TEXT = colors.white
    COLOR_ROW_EVEN = colors.HexColor('#E8F5F3')
    COLOR_ROW_ODD = colors.white
    COLOR_BORDER = colors.HexColor('#B0BEC5')
    COLOR_SUBTLE = colors.HexColor('#546E7A')
    COLOR_TOTALS_BG = colors.HexColor('#CFD8DC')

    # ── Construir título ──
    if nombre_carrera and cuatrimestre:
        titulo_pdf = f"Catalogo de Materias - {nombre_carrera} - Cuatrimestre {cuatrimestre}"
    elif nombre_carrera and ciclo:
        ciclo_label = {1: 'Ciclo 1', 2: 'Ciclo 2', 3: 'Ciclo 3'}.get(ciclo, f'Ciclo {ciclo}')
        titulo_pdf = f"Catalogo de Materias - {nombre_carrera} - {ciclo_label}"
    elif nombre_carrera:
        titulo_pdf = f"Catalogo de Materias - {nombre_carrera}"
    elif cuatrimestre:
        titulo_pdf = f"Catalogo de Materias - Cuatrimestre {cuatrimestre}"
    elif ciclo:
        ciclo_label = {1: 'Ciclo 1', 2: 'Ciclo 2', 3: 'Ciclo 3'}.get(ciclo, f'Ciclo {ciclo}')
        titulo_pdf = f"Catalogo de Materias - {ciclo_label}"
    else:
        titulo_pdf = "Catalogo de Materias - Todas las Carreras"

    # Fecha en espanol
    fecha_reporte = datetime.now().strftime('%d de %B de %Y')
    meses_es = {'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
                'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
                'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'}
    for en, es in meses_es.items():
        fecha_reporte = fecha_reporte.replace(en, es)

    # ── Header/Footer en cada pagina ──
    def draw_page_header(canvas_obj, doc_obj):
        canvas_obj.saveState()
        # Barra superior teal
        canvas_obj.setFillColor(COLOR_TEAL)
        canvas_obj.rect(0, page_h - 75, page_w, 75, fill=1, stroke=0)
        # Linea dorada inferior
        canvas_obj.setFillColor(colors.HexColor('#FFD600'))
        canvas_obj.rect(0, page_h - 78, page_w, 3, fill=1, stroke=0)
        # Logo
        if logo_exists:
            try:
                canvas_obj.drawImage(logo_path, 30, page_h - 67, width=70, height=50,
                                     preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        # Titulo centrado
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont('Helvetica-Bold', 15)
        canvas_obj.drawCentredString(page_w / 2, page_h - 35, titulo_pdf)
        # Subtitulo
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.drawCentredString(page_w / 2, page_h - 52, "Area: Direccion Academica")
        # Fecha
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.drawRightString(page_w - 40, page_h - 52, fecha_reporte)
        # Pie de pagina
        canvas_obj.setFillColor(COLOR_SUBTLE)
        canvas_obj.setFont('Helvetica-Oblique', 7)
        canvas_obj.drawCentredString(page_w / 2, 20,
            f"Sistema de Gestion Academica - Universidad Politecnica de Texcoco - Pag. {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    # ── Estilos de texto ──
    styles = getSampleStyleSheet()

    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceBefore=4,
        spaceAfter=8,
        textColor=COLOR_NAVY,
        fontName='Helvetica-Bold'
    )

    stats_style = ParagraphStyle(
        'Stats',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        alignment=1,
        textColor=COLOR_SUBTLE,
        fontName='Helvetica'
    )

    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        fontName='Helvetica'
    )

    cell_center_style = ParagraphStyle(
        'CellCenter',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        fontName='Helvetica',
        alignment=1
    )

    # ── Contenido del PDF ──
    elements = []

    if not materias:
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("No se encontraron materias con los criterios especificados.", styles['Normal']))
    else:
        # Agrupar materias por carrera
        materias_por_carrera = OrderedDict()
        for m in materias:
            try:
                carrera_nom = m.get_carrera_nombre()
            except Exception:
                carrera_nom = 'Sin carrera'
            if carrera_nom not in materias_por_carrera:
                materias_por_carrera[carrera_nom] = []
            materias_por_carrera[carrera_nom].append(m)

        # Estadisticas globales
        total_creditos = sum(m.creditos for m in materias)
        total_horas = sum(m.get_horas_totales() for m in materias)
        cuatrimestres_set = set(m.cuatrimestre for m in materias)

        stats_text = (
            f"<b>{len(materias)}</b> materias  |  "
            f"<b>{len(materias_por_carrera)}</b> carrera(s)  |  "
            f"<b>{len(cuatrimestres_set)}</b> cuatrimestre(s)  |  "
            f"<b>{total_creditos}</b> creditos totales  |  "
            f"<b>{total_horas}</b> horas totales"
        )
        elements.append(Paragraph(stats_text, stats_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_TEAL, spaceBefore=0, spaceAfter=6))

        # Anchos de columna (landscape A4 ~ 762pt usable)
        col_widths = [35, 70, 240, 80, 55, 60, 65, 80]

        for idx_carrera, (carrera_nom, lista_materias) in enumerate(materias_por_carrera.items()):
            # Salto de pagina entre carreras
            if idx_carrera > 0:
                elements.append(PageBreak())

            # Titulo de la carrera
            elements.append(Paragraph(
                f'<font color="#00847C">\u25a0</font>  {carrera_nom} '
                f'<font color="#546E7A" size="10">({len(lista_materias)} materias)</font>',
                section_title_style
            ))
            elements.append(Spacer(1, 4))

            # Ordenar
            lista_materias.sort(key=lambda m: (m.cuatrimestre, m.nombre))

            # Header de tabla
            hdr_style = ParagraphStyle('hdr', parent=cell_center_style, textColor=colors.white, fontName='Helvetica-Bold', fontSize=8)
            hdr_style_l = ParagraphStyle('hdrL', parent=cell_style, textColor=colors.white, fontName='Helvetica-Bold', fontSize=8)
            header_row = [
                Paragraph('<b>#</b>', hdr_style),
                Paragraph('<b>Codigo</b>', hdr_style),
                Paragraph('<b>Nombre de la Materia</b>', hdr_style_l),
                Paragraph('<b>Cuatrimestre</b>', hdr_style),
                Paragraph('<b>Creditos</b>', hdr_style),
                Paragraph('<b>Hrs/Sem</b>', hdr_style),
                Paragraph('<b>Hrs Totales</b>', hdr_style),
                Paragraph('<b>Ciclo Escolar</b>', hdr_style),
            ]
            data = [header_row]

            grupo_horas = 0
            grupo_creditos = 0
            for i, mat in enumerate(lista_materias, 1):
                hrs_totales = mat.get_horas_totales()
                grupo_horas += hrs_totales
                grupo_creditos += mat.creditos
                try:
                    ciclo_info = mat.get_ciclo_escolar()
                    ciclo_text = ciclo_info.get('nombre', '') if isinstance(ciclo_info, dict) else str(ciclo_info)
                except Exception:
                    ciclo_text = ''
                row = [
                    Paragraph(str(i), cell_center_style),
                    Paragraph(f'<b>{mat.codigo}</b>', cell_center_style),
                    Paragraph(mat.nombre, cell_style),
                    Paragraph(f'Cuatrimestre {mat.cuatrimestre}', cell_center_style),
                    Paragraph(str(mat.creditos), cell_center_style),
                    Paragraph(f'{mat.horas_semanales}h', cell_center_style),
                    Paragraph(f'{hrs_totales}h', cell_center_style),
                    Paragraph(ciclo_text, cell_center_style),
                ]
                data.append(row)

            # Subtotales
            totals_row = [
                '', '',
                Paragraph(f'<b>Subtotal: {len(lista_materias)} materias</b>', cell_style),
                '',
                Paragraph(f'<b>{grupo_creditos}</b>', cell_center_style),
                '',
                Paragraph(f'<b>{grupo_horas}h</b>', cell_center_style),
                ''
            ]
            data.append(totals_row)

            table = Table(data, colWidths=col_widths, repeatRows=1)

            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER_BG),
                ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_HEADER_TEXT),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('TOPPADDING', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -2), 0.5, COLOR_BORDER),
                ('LINEBELOW', (0, 0), (-1, 0), 2, COLOR_TEAL_DARK),
                ('BACKGROUND', (0, -1), (-1, -1), COLOR_TOTALS_BG),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (0, -1), (-1, -1), 1.2, COLOR_TEAL_DARK),
                ('LINEBELOW', (0, -1), (-1, -1), 1.2, COLOR_TEAL_DARK),
                ('TOPPADDING', (0, -1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            ]
            for row_idx in range(1, len(data) - 1):
                bg = COLOR_ROW_EVEN if row_idx % 2 == 0 else COLOR_ROW_ODD
                style_cmds.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))
            table.setStyle(TableStyle(style_cmds))
            elements.append(table)

    # Generar PDF con header/footer en cada pagina
    doc.build(elements, onFirstPage=draw_page_header, onLaterPages=draw_page_header)
    pdf = buffer.getvalue()
    buffer.close()

    return pdf

def crear_tabla_materias(materias):
    """Crear datos de tabla para materias (legacy, ya no se usa directamente)"""
    headers = ['Código', 'Nombre', 'Carrera', 'Cuatrimestre', 'Créditos', 'Horas Totales']
    data = [headers]
    
    for materia in materias:
        data.append([
            materia.codigo,
            materia.nombre,
            materia.get_carrera_codigo(),
            f"Cuatrimestre {materia.cuatrimestre}",
            str(materia.creditos),
            str(materia.get_horas_totales())
        ])
    
    return data

def procesar_archivo_carreras(archivo, usuario_id):
    """
    Procesar archivo CSV con datos de carreras
    
    Formato esperado del archivo CSV:
    - codigo, nombre, descripcion, facultad
    
    Args:
        archivo: Archivo CSV cargado
        usuario_id: ID del usuario que está importando (para auditoría)
    
    Returns:
        dict: Resultado de la operación con estadísticas y errores
    """
    resultado = {
        'exito': False,
        'procesados': 0,
        'creados': 0,
        'actualizados': 0,
        'errores': [],
        'carreras_creadas': [],
        'mensaje': ''
    }
    
    try:
        # Leer archivo CSV con diferentes codificaciones
        try:
            df = pd.read_csv(archivo, encoding='utf-8')
        except UnicodeDecodeError:
            archivo.seek(0)
            try:
                df = pd.read_csv(archivo, encoding='latin-1')
            except:
                archivo.seek(0)
                df = pd.read_csv(archivo, encoding='iso-8859-1')
        
        # Limpiar nombres de columnas (eliminar espacios y convertir a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas
        columnas_requeridas = ['codigo', 'nombre']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            columnas_encontradas = ', '.join(df.columns.tolist())
            resultado['mensaje'] = f"Columnas faltantes: {', '.join(columnas_faltantes)}. Columnas encontradas: {columnas_encontradas}"
            return resultado
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                resultado['procesados'] += 1
                
                # Validar datos básicos
                if pd.isna(row['codigo']) or pd.isna(row['nombre']):
                    resultado['errores'].append(f"Fila {index + 2}: Código o nombre vacío")
                    continue
                
                # Limpiar y normalizar datos
                codigo = str(row['codigo']).strip().upper()
                nombre = str(row['nombre']).strip()
                descripcion = str(row['descripcion']).strip() if 'descripcion' in df.columns and not pd.isna(row['descripcion']) else None
                facultad = str(row['facultad']).strip() if 'facultad' in df.columns and not pd.isna(row['facultad']) else None
                
                # Validar longitud de campos
                if len(codigo) < 2 or len(codigo) > 10:
                    resultado['errores'].append(f"Fila {index + 2}: El código '{codigo}' debe tener entre 2 y 10 caracteres")
                    continue
                
                if len(nombre) < 5 or len(nombre) > 150:
                    resultado['errores'].append(f"Fila {index + 2}: El nombre '{nombre}' debe tener entre 5 y 150 caracteres")
                    continue
                
                if descripcion and len(descripcion) > 500:
                    resultado['errores'].append(f"Fila {index + 2}: La descripción es demasiado larga (máximo 500 caracteres)")
                    continue
                
                if facultad and len(facultad) > 100:
                    resultado['errores'].append(f"Fila {index + 2}: El nombre de la facultad es demasiado largo (máximo 100 caracteres)")
                    continue
                
                # Verificar si ya existe una carrera con ese código
                carrera_existente = Carrera.query.filter_by(codigo=codigo, activa=True).first()
                
                if carrera_existente:
                    # Actualizar carrera existente
                    carrera_existente.nombre = nombre
                    if descripcion:
                        carrera_existente.descripcion = descripcion
                    if facultad:
                        carrera_existente.facultad = facultad
                    
                    resultado['actualizados'] += 1
                    resultado['carreras_creadas'].append({
                        'codigo': codigo,
                        'nombre': nombre,
                        'accion': 'actualizada'
                    })
                else:
                    # Verificar si existe una carrera con el mismo nombre
                    carrera_mismo_nombre = Carrera.query.filter_by(nombre=nombre, activa=True).first()
                    if carrera_mismo_nombre:
                        resultado['errores'].append(f"Fila {index + 2}: Ya existe una carrera con el nombre '{nombre}'")
                        continue
                    
                    # Crear nueva carrera
                    nueva_carrera = Carrera(
                        codigo=codigo,
                        nombre=nombre,
                        descripcion=descripcion,
                        facultad=facultad,
                        creada_por=usuario_id
                    )
                    
                    db.session.add(nueva_carrera)
                    resultado['creados'] += 1
                    resultado['carreras_creadas'].append({
                        'codigo': codigo,
                        'nombre': nombre,
                        'accion': 'creada'
                    })
                
            except Exception as e:
                resultado['errores'].append(f"Fila {index + 2}: Error al procesar - {str(e)}")
                continue
        
        # Guardar cambios en la base de datos
        if resultado['creados'] > 0 or resultado['actualizados'] > 0:
            db.session.commit()
            resultado['exito'] = True
            resultado['mensaje'] = f"Importación completada: {resultado['creados']} carreras creadas, {resultado['actualizados']} actualizadas"
        else:
            db.session.rollback()
            resultado['mensaje'] = "No se crearon ni actualizaron carreras"
        
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f"Error al procesar el archivo: {str(e)}"
        resultado['errores'].append(f"Error general: {str(e)}")
    
    return resultado

def generar_plantilla_csv_carreras():
    """
    Generar plantilla CSV para importación de carreras
    
    Returns:
        str: Contenido del archivo CSV de plantilla
    """
    plantilla = "codigo,nombre,descripcion,facultad\n"
    plantilla += "ING-SIS,Ingeniería en Sistemas Computacionales,Carrera de ingeniería enfocada en desarrollo de software,Facultad de Ingeniería\n"
    plantilla += "ADM-EMP,Administración de Empresas,Carrera enfocada en gestión empresarial,Facultad de Ciencias Económicas\n"
    plantilla += "DER,Derecho,Carrera de ciencias jurídicas,Facultad de Derecho\n"
    
    return plantilla

def procesar_archivo_asignaciones(archivo):
    """
    Procesar archivo CSV con asignaciones de materias a profesores
    
    Formato esperado del archivo CSV:
    - profesor_email, materia_codigo
    
    Args:
        archivo: Archivo CSV cargado
    
    Returns:
        dict: Resultado de la operación con estadísticas y errores
    """
    resultado = {
        'exito': False,
        'procesados': 0,
        'asignados': 0,
        'ya_asignados': 0,
        'errores': [],
        'asignaciones_realizadas': [],
        'mensaje': ''
    }
    
    try:
        # Leer archivo CSV con diferentes codificaciones
        try:
            df = pd.read_csv(archivo, encoding='utf-8')
        except UnicodeDecodeError:
            archivo.seek(0)
            try:
                df = pd.read_csv(archivo, encoding='latin-1')
            except:
                archivo.seek(0)
                df = pd.read_csv(archivo, encoding='iso-8859-1')
        
        # Limpiar nombres de columnas (eliminar espacios y convertir a minúsculas)
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas
        columnas_requeridas = ['profesor_email', 'materia_codigo']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            columnas_encontradas = ', '.join(df.columns.tolist())
            resultado['mensaje'] = f"Columnas faltantes: {', '.join(columnas_faltantes)}. Columnas encontradas: {columnas_encontradas}"
            return resultado
        
        # Procesar cada fila
        for index, row in df.iterrows():
            try:
                resultado['procesados'] += 1
                
                # Validar datos básicos
                if pd.isna(row['profesor_email']) or pd.isna(row['materia_codigo']):
                    resultado['errores'].append(f"Fila {index + 2}: Email del profesor o código de materia vacío")
                    continue
                
                # Limpiar y normalizar datos
                profesor_email = str(row['profesor_email']).strip().lower()
                materia_codigo = str(row['materia_codigo']).strip().upper()
                
                # Buscar profesor por email
                profesor = User.query.filter(
                    User.email == profesor_email,
                    User.activo == True,
                    User.rol.in_(['profesor_completo', 'profesor_asignatura'])
                ).first()
                
                if not profesor:
                    resultado['errores'].append(f"Fila {index + 2}: No se encontró profesor activo con email '{profesor_email}'")
                    continue
                
                # Buscar materia por código
                materia = Materia.query.filter(
                    Materia.codigo == materia_codigo,
                    Materia.activa == True
                ).first()
                
                if not materia:
                    resultado['errores'].append(f"Fila {index + 2}: No se encontró materia activa con código '{materia_codigo}'")
                    continue
                
                # Verificar si ya está asignada
                if materia in profesor.materias:
                    resultado['ya_asignados'] += 1
                    continue
                
                # Asignar materia al profesor
                profesor.materias.append(materia)
                resultado['asignados'] += 1
                resultado['asignaciones_realizadas'].append({
                    'profesor': profesor.get_nombre_completo(),
                    'profesor_email': profesor_email,
                    'materia': materia.nombre,
                    'materia_codigo': materia_codigo
                })
                
            except Exception as e:
                resultado['errores'].append(f"Fila {index + 2}: Error al procesar - {str(e)}")
                continue
        
        # Guardar cambios en la base de datos
        if resultado['asignados'] > 0:
            db.session.commit()
            resultado['exito'] = True
            resultado['mensaje'] = f"Importación completada: {resultado['asignados']} asignaciones nuevas, {resultado['ya_asignados']} ya existían"
        else:
            db.session.rollback()
            if resultado['ya_asignados'] > 0:
                resultado['mensaje'] = f"Todas las asignaciones ({resultado['ya_asignados']}) ya existían"
            else:
                resultado['mensaje'] = "No se realizaron asignaciones"
        
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f"Error al procesar el archivo: {str(e)}"
        resultado['errores'].append(f"Error general: {str(e)}")
    
    return resultado

def generar_plantilla_csv_asignaciones():
    """
    Generar plantilla CSV para importación de asignaciones de materias
    
    Returns:
        str: Contenido del archivo CSV de plantilla
    """
    plantilla = "profesor_email,materia_codigo\n"
    plantilla += "profesor1@universidad.edu,MAT-101\n"
    plantilla += "profesor1@universidad.edu,MAT-201\n"
    plantilla += "profesor2@universidad.edu,FIS-101\n"
    plantilla += "profesor2@universidad.edu,FIS-102\n"
    
    return plantilla

def calcular_carga_profesor(profesor):
    """
    Calcular la carga horaria de un profesor basándose en sus materias y horarios.
    Usa los límites configurables desde el panel de administración.

    Args:
        profesor: Objeto User (profesor)

    Returns:
        dict: Información sobre la carga del profesor
    """
    from models import ConfiguracionSistema, AsignacionProfesorGrupo

    # Obtener horarios generados del profesor
    horarios = HorarioAcademico.query.filter_by(
        profesor_id=profesor.id,
        activo=True
    ).all()

    # Calcular horas de horarios ya generados
    horas_horarios = len(horarios)  # Cada horario es 1 hora

    # Calcular horas potenciales de materias asignadas (via relación M2M)
    horas_materias_asignadas = sum(m.horas_semanales or 3 for m in profesor.materias)

    # Calcular horas de asignaciones específicas a grupos
    asignaciones_grupo = AsignacionProfesorGrupo.query.filter_by(
        profesor_id=profesor.id,
        activo=True
    ).all()
    horas_asignaciones_grupo = sum(a.materia.horas_semanales or 3 for a in asignaciones_grupo if a.materia)

    # Total de horas: usar el mayor entre horarios generados y materias asignadas
    # Esto muestra la carga real o potencial del profesor
    total_horas = max(horas_horarios, horas_materias_asignadas, horas_asignaciones_grupo)
    total_materias = len(profesor.materias)

    # Obtener límites desde la configuración del sistema
    if profesor.rol == 'profesor_completo':
        limite_maximo = ConfiguracionSistema.get_config('horas_tiempo_completo', 40)
        limite_recomendado = int(limite_maximo * 0.875)  # 87.5% del máximo
    else:  # profesor_asignatura
        limite_maximo = ConfiguracionSistema.get_config('horas_asignatura', 20)
        limite_recomendado = int(limite_maximo * 0.75)  # 75% del máximo

    # Aplicar límite absoluto del sistema
    limite_absoluto = ConfiguracionSistema.get_config('horas_limite_absoluto', 50)
    limite_maximo = min(limite_maximo, limite_absoluto)
    
    # Determinar estado de carga
    if total_horas == 0:
        estado = 'sin_carga'
        color = 'secondary'
    elif total_horas <= limite_recomendado * 0.5:
        estado = 'baja'
        color = 'info'
    elif total_horas <= limite_recomendado:
        estado = 'adecuada'
        color = 'success'
    elif total_horas <= limite_maximo:
        estado = 'alta'
        color = 'warning'
    else:
        estado = 'sobrecarga'
        color = 'danger'
    
    porcentaje = (total_horas / limite_maximo * 100) if limite_maximo > 0 else 0

    return {
        'total_horas': total_horas,
        'horas_horarios': horas_horarios,  # Horas de horarios ya generados
        'horas_materias': horas_materias_asignadas,  # Horas potenciales de materias M2M
        'horas_grupos': horas_asignaciones_grupo,  # Horas de asignaciones específicas
        'total_materias': total_materias,
        'limite_recomendado': limite_recomendado,
        'limite_maximo': limite_maximo,
        'porcentaje': min(porcentaje, 100),
        'estado': estado,
        'color': color,
        'puede_mas': total_horas < limite_maximo
    }


def procesar_archivo_asignaciones_grupo(archivo):
    """
    Procesar archivo CSV con asignaciones de materias a grupos
    
    Formato esperado del archivo:
    - grupo_codigo, materia_codigo
    
    Ejemplo:
    1MSC1,MAT101
    1MSC1,FIS101
    2MSC3,BD201
    
    Returns:
        dict: Resultado del procesamiento con éxito, procesados, errores, etc.
    """
    resultado = {
        'exito': False,
        'procesados': 0,
        'asignaciones_creadas': 0,
        'errores': [],
        'mensaje': ''
    }
    
    try:
        # Leer archivo CSV
        if archivo.filename.endswith('.csv'):
            try:
                df = pd.read_csv(archivo, encoding='utf-8')
            except:
                archivo.seek(0)
                df = pd.read_csv(archivo, encoding='latin-1')
        else:
            resultado['mensaje'] = 'Solo se permiten archivos CSV'
            return resultado
        
        # Validar columnas
        columnas_requeridas = ['grupo_codigo', 'materia_codigo']
        if not all(col in df.columns for col in columnas_requeridas):
            resultado['mensaje'] = f'El archivo debe tener las columnas: {", ".join(columnas_requeridas)}'
            return resultado
        
        # Eliminar filas vacías
        df = df.dropna(subset=columnas_requeridas)
        
        from models import Grupo, Materia
        
        # Procesar cada fila
        asignaciones_por_grupo = {}  # {grupo_id: [materia_ids]}
        
        for index, row in df.iterrows():
            fila = index + 2  # +2 porque índice 0 + 1 (header) + 1 (base 1)
            
            try:
                grupo_codigo = str(row['grupo_codigo']).strip()
                materia_codigo = str(row['materia_codigo']).strip()
                
                # Buscar grupo
                grupo = Grupo.query.filter_by(codigo=grupo_codigo, activo=True).first()
                if not grupo:
                    resultado['errores'].append(f'Fila {fila}: Grupo "{grupo_codigo}" no encontrado o inactivo')
                    continue
                
                # Buscar materia
                materia = Materia.query.filter_by(codigo=materia_codigo, activa=True).first()
                if not materia:
                    resultado['errores'].append(f'Fila {fila}: Materia "{materia_codigo}" no encontrada o inactiva')
                    continue
                
                # Validar que la materia sea de la misma carrera y cuatrimestre
                if materia.carrera_id != grupo.carrera_id:
                    resultado['errores'].append(
                        f'Fila {fila}: La materia "{materia_codigo}" no pertenece a la carrera del grupo "{grupo_codigo}"'
                    )
                    continue
                
                if materia.cuatrimestre != grupo.cuatrimestre:
                    resultado['errores'].append(
                        f'Fila {fila}: La materia "{materia_codigo}" (cuatrimestre {materia.cuatrimestre}) '
                        f'no coincide con el cuatrimestre del grupo "{grupo_codigo}" (cuatrimestre {grupo.cuatrimestre})'
                    )
                    continue
                
                # Agrupar materias por grupo
                if grupo.id not in asignaciones_por_grupo:
                    asignaciones_por_grupo[grupo.id] = {'grupo': grupo, 'materias': set()}
                
                asignaciones_por_grupo[grupo.id]['materias'].add(materia)
                resultado['procesados'] += 1
                
            except Exception as e:
                resultado['errores'].append(f'Fila {fila}: Error al procesar - {str(e)}')
                continue
        
        # Aplicar asignaciones
        if asignaciones_por_grupo:
            for grupo_id, data in asignaciones_por_grupo.items():
                grupo = data['grupo']
                materias = list(data['materias'])
                
                # Agregar nuevas materias (sin eliminar las existentes)
                materias_actuales = set(grupo.materias)
                materias_nuevas = set(materias) - materias_actuales
                
                if materias_nuevas:
                    grupo.materias.extend(list(materias_nuevas))
                    resultado['asignaciones_creadas'] += len(materias_nuevas)
            
            db.session.commit()
            resultado['exito'] = True
            resultado['mensaje'] = f'{resultado["asignaciones_creadas"]} asignaciones creadas exitosamente'
        else:
            resultado['mensaje'] = 'No se procesaron asignaciones válidas'
        
    except Exception as e:
        resultado['mensaje'] = f'Error al procesar archivo: {str(e)}'
        resultado['errores'].append(str(e))
    
    return resultado


def generar_plantilla_csv_asignaciones_grupo():
    """
    Generar plantilla CSV para importar asignaciones de materias a grupos
    
    Returns:
        str: Contenido del archivo CSV de ejemplo
    """
    return """grupo_codigo,materia_codigo
1MSC1,MAT101
1MSC1,FIS101
1MSC1,PROG101
2MSC3,BD201
2MSC3,WEB201"""


def exportar_asignaciones_grupo_csv(carrera_id=None, cuatrimestre=None):
    """
    Exportar asignaciones actuales de materias a grupos en formato CSV
    
    Args:
        carrera_id: ID de carrera para filtrar (opcional)
        cuatrimestre: Número de cuatrimestre para filtrar (opcional)
    
    Returns:
        str: Contenido CSV con las asignaciones actuales
    """
    from models import Grupo
    
    # Construir query con filtros
    query = Grupo.query.filter_by(activo=True)
    
    if carrera_id:
        query = query.filter_by(carrera_id=carrera_id)
    
    if cuatrimestre:
        query = query.filter_by(cuatrimestre=cuatrimestre)
    
    grupos = query.order_by(Grupo.codigo).all()
    
    # Generar CSV
    lineas = ['grupo_codigo,materia_codigo']
    
    for grupo in grupos:
        for materia in grupo.materias:
            if materia.activa:
                lineas.append(f'{grupo.codigo},{materia.codigo}')
    
    return '\n'.join(lineas)


def auto_asignar_materias_grupo(carrera_id, cuatrimestre):
    """
    Auto-asignar todas las materias del cuatrimestre a los grupos correspondientes
    
    Args:
        carrera_id: ID de la carrera
        cuatrimestre: Número de cuatrimestre
    
    Returns:
        dict: Resultado con éxito, grupos procesados, asignaciones creadas
    """
    resultado = {
        'exito': False,
        'grupos_procesados': 0,
        'asignaciones_creadas': 0,
        'mensaje': ''
    }
    
    try:
        from models import Grupo, Materia
        
        # Obtener grupos del cuatrimestre y carrera
        grupos = Grupo.query.filter_by(
            carrera_id=carrera_id,
            cuatrimestre=cuatrimestre,
            activo=True
        ).all()
        
        if not grupos:
            resultado['mensaje'] = 'No se encontraron grupos activos para esta carrera y cuatrimestre'
            return resultado
        
        # Obtener materias del cuatrimestre y carrera
        materias = Materia.query.filter_by(
            carrera_id=carrera_id,
            cuatrimestre=cuatrimestre,
            activa=True
        ).all()
        
        if not materias:
            resultado['mensaje'] = 'No se encontraron materias activas para esta carrera y cuatrimestre'
            return resultado
        
        # Asignar todas las materias a cada grupo
        for grupo in grupos:
            materias_actuales = set(grupo.materias)
            materias_nuevas = set(materias) - materias_actuales
            
            if materias_nuevas:
                grupo.materias.extend(list(materias_nuevas))
                resultado['asignaciones_creadas'] += len(materias_nuevas)
            
            resultado['grupos_procesados'] += 1
        
        db.session.commit()
        resultado['exito'] = True
        resultado['mensaje'] = (
            f'Se asignaron materias a {resultado["grupos_procesados"]} grupos. '
            f'Total de asignaciones creadas: {resultado["asignaciones_creadas"]}'
        )
        
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f'Error al auto-asignar materias: {str(e)}'
    
    return resultado
