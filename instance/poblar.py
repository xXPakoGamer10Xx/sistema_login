import sqlite3
import itertools
import sys
from faker import Faker

# --- Constantes de Configuración ---
DB_NAME = 'sistema_academico.db'
NUM_CARRERAS = 3
NUM_MAESTROS = 18
MATERIAS_PER_GRUPO = 7

# IDs iniciales para tablas sin AUTOINCREMENT
JEFE_ID_START = 50
MAESTRO_ID_START = 100
CARRERA_ID_START = 1
MATERIA_ID_START = 1

# --- Lista de tablas a limpiar (en orden de dependencia) ---
TABLAS_A_LIMPIAR = [
    'disponibilidad_profesor',
    'horario_academico',
    'profesor_materias',
    'grupo_materias',
    'usuario_carrera',
    'user_carreras',     # <-- Corregido (antes decía user_cerreras)
    'grupo',
    'materia',
    # 'user' y 'carrera' se manejan por separado al final
]

def obtener_admin_id(cursor):
    """Obtiene el ID del usuario 'admin' para usarlo en 'creado_por'."""
    cursor.execute("SELECT id FROM user WHERE username = 'admin'")
    resultado = cursor.fetchone()
    if not resultado:
        print("Error: No se encontró al usuario 'admin'.", file=sys.stderr)
        print("Asegúrate de que exista un usuario con username = 'admin'.", file=sys.stderr)
        return None
    return resultado[0]

def obtener_horarios_matutinos(cursor):
    """Obtiene todos los IDs de horarios matutinos (no receso)."""
    cursor.execute("""
        SELECT id FROM horario 
        WHERE turno = 'matutino' AND nombre NOT LIKE '%Receso%' 
    """)
    ids = [row[0] for row in cursor.fetchall()]
    if not ids:
        print("Advertencia: No se encontraron horarios matutinos en la tabla 'horario'.")
        print("La tabla 'disponibilidad_profesor' no se poblará.")
    return ids

def limpiar_tablas(cursor, admin_id):
    """Borra datos de las tablas, protegiendo al admin."""
    print("--- 🧹 Iniciando limpieza de tablas ---")
    for tabla in TABLAS_A_LIMPIAR:
        try:
            print(f"  - Limpiando {tabla}...")
            cursor.execute(f"DELETE FROM {tabla};")
        except sqlite3.Error as e:
            print(f"    Error limpiando {tabla}: {e}")
    
    # --- MANEJAR USUARIOS Y CARRERAS AL FINAL ---
    print("  - Limpiando 'user' (excepto admin)...")
    try:
        cursor.execute("DELETE FROM user WHERE id != ?;", (admin_id,))
    except sqlite3.Error as e:
        print(f"    Error limpiando user: {e}")

    print("  - Limpiando 'carrera'...")
    try:
        cursor.execute("DELETE FROM carrera;")
    except sqlite3.Error as e:
        print(f"    Error limpiando carrera: {e}")
    
    print("  - Reseteando secuencia de 'grupo'...")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'grupo';")
    print("--- Limpieza completada ---\n")


def poblar_datos(cursor, admin_id, horario_ids):
    """Puebla la base de datos con datos falsos."""
    print("--- 🚀 Iniciando población de datos ---")
    fake = Faker('es_ES')
    
    maestro_ids = []
    carrera_ids = []
    all_materia_ids = []
    
    current_maestro_id = MAESTRO_ID_START
    current_carrera_id = CARRERA_ID_START
    current_materia_id = MATERIA_ID_START

    password_hash = "pbkdf2:sha256:600000$7xMrlT01REbkRtFJ$bf58e295f01fad23ffc98268ca55b98808f8e34e0c786db6fcbee0f7d225c412"

    # --- 1. Crear Carreras, Jefes, Grupos y Materias ---
    print(f"Creando {NUM_CARRERAS} carreras (c/u con 1 jefe, 1 grupo, cuatri 0, matutino)...")
    
    for i in range(NUM_CARRERAS):
        carrera_id = current_carrera_id + i
        carrera_ids.append(carrera_id)
        
        # Crear Carrera
        nombre_carrera = f"Ingeniería en {fake.job().split(' ')[-1]} Aplicada"
        codigo_carrera = f"I{fake.lexify(text='???').upper()}{i}"
        facultad = f"Facultad de {fake.word().capitalize()}"
        
        cursor.execute("""
            INSERT INTO carrera (id, nombre, codigo, descripcion, facultad, activa, fecha_creacion, creada_por)
            VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, ?)
        """, (carrera_id, nombre_carrera, codigo_carrera, f"Descripción de {nombre_carrera}", facultad, admin_id))
        print(f"  - Carrera creada: '{nombre_carrera}' (ID: {carrera_id})")

        # Crear Jefe de Carrera
        jefe_id = JEFE_ID_START + i
        jefe_nombre = fake.first_name()
        jefe_apellido = fake.last_name()
        jefe_username = f"jefe.{codigo_carrera.lower()}"
        jefe_email = f"{jefe_username}@example.com"
        
        cursor.execute("""
            INSERT INTO user (
                id, username, email, password_hash, nombre, apellido, rol, 
                carrera_id, 
                fecha_registro, activo, requiere_cambio_password
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1, 0)
        """, (jefe_id, jefe_username, jefe_email, password_hash, jefe_nombre, jefe_apellido, 'jefe_carrera', carrera_id))
        
        # Insertar en user_carreras también para el jefe
        cursor.execute("INSERT INTO user_carreras (user_id, carrera_id) VALUES (?, ?)", (jefe_id, carrera_id))

        # Crear Grupo
        codigo_grupo = f"{codigo_carrera}-001-M"
        cursor.execute("""
            INSERT INTO grupo (codigo, numero_grupo, turno, cuatrimestre, carrera_id, activo, creado_por)
            VALUES (?, 1, 'M', 0, ?, 1, ?)
        """, (codigo_grupo, carrera_id, admin_id))
        grupo_id = cursor.lastrowid

        # Crear Materias (Horas corregidas: 2 teóricas, 2 prácticas)
        materias_para_grupo = []
        for j in range(MATERIAS_PER_GRUPO):
            materia_id = current_materia_id
            current_materia_id += 1
            nombre_materia = f"{fake.job().title()} {j+1}"
            codigo_materia = f"{codigo_carrera}-M{j+1}"
            
            cursor.execute("""
                INSERT INTO materia (
                    id, nombre, codigo, descripcion, cuatrimestre, creditos, horas_teoricas, 
                    horas_practicas, carrera_id, activa, fecha_creacion, creado_por
                ) VALUES (?, ?, ?, ?, 0, 4, 2, 2, ?, 1, CURRENT_TIMESTAMP, ?)
            """, (materia_id, nombre_materia, codigo_materia, f"Descripción de {nombre_materia}", carrera_id, admin_id))

            materias_para_grupo.append(materia_id)
            all_materia_ids.append(materia_id)
        
        for mat_id in materias_para_grupo:
            cursor.execute("INSERT INTO grupo_materias (grupo_id, materia_id) VALUES (?, ?)", (grupo_id, mat_id))
    
    print(f"\nTotal de materias creadas: {len(all_materia_ids)}\n")

    # --- 2. Crear Maestros (Con Carrera Asignada) ---
    print(f"Creando {NUM_MAESTROS} maestros y asignándoles carrera...")
    
    # Ciclo para asignar carreras equitativamente a los profesores
    carrera_cycle = itertools.cycle(carrera_ids)

    for i in range(NUM_MAESTROS):
        nombre = fake.first_name()
        apellido = fake.last_name()
        username = f"{nombre.lower()}.{apellido.lower()}{i}"
        email = f"{username}@example.com"
        maestro_id = current_maestro_id + i
        
        # Asignamos una carrera del ciclo
        carrera_asignada = next(carrera_cycle)
        
        # Insertar Maestro con carrera_id
        cursor.execute("""
            INSERT INTO user (
                id, username, email, password_hash, nombre, apellido, rol, tipo_profesor, 
                carrera_id,  -- <== Asignación de carrera
                fecha_registro, activo, requiere_cambio_password
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1, 0)
        """, (
            maestro_id, username, email, password_hash, nombre, apellido, 
            'profesor_completo', 'profesor_completo', 
            carrera_asignada
        ))
        
        # Insertar relación en tabla intermedia user_carreras
        cursor.execute("INSERT INTO user_carreras (user_id, carrera_id) VALUES (?, ?)", (maestro_id, carrera_asignada))
        
        maestro_ids.append(maestro_id)
    print(f"Maestros creados (IDs {maestro_ids[0]} a {maestro_ids[-1]}).\n")


    # --- 3. Asignar Maestros a Materias ---
    print(f"Asignando {len(maestro_ids)} maestros a {len(all_materia_ids)} materias...")
    maestro_cycle = itertools.cycle(maestro_ids)
    
    asignaciones = {}
    for materia_id in all_materia_ids:
        maestro_id = next(maestro_cycle)
        cursor.execute("INSERT INTO profesor_materias (profesor_id, materia_id) VALUES (?, ?)", (maestro_id, materia_id))
        asignaciones[maestro_id] = asignaciones.get(maestro_id, 0) + 1
    
    print("Asignación completada.\n")
    
    # --- 4. Poblar Disponibilidad ---
    if not horario_ids:
        print("--- Población de disponibilidad OMITIDA (no se encontraron horarios) ---")
        return

    print(f"Poblando disponibilidad (100%) para maestros en {len(horario_ids)} horarios matutinos...")
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
    
    for maestro_id in maestro_ids:
        for dia in dias:
            for horario_id in horario_ids:
                cursor.execute("""
                    INSERT INTO disponibilidad_profesor (
                        profesor_id, horario_id, dia_semana, disponible, activo, fecha_creacion, creado_por
                    ) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, ?)
                """, (maestro_id, horario_id, dia, 1, admin_id))
    print("--- Población de disponibilidad completada ---")


def main():
    """Función principal."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        admin_id = obtener_admin_id(cursor)
        if admin_id is None:
            return
        print(f"Usuario 'admin' encontrado con ID: {admin_id}\n")
        
        horario_ids = obtener_horarios_matutinos(cursor)
        
        limpiar_tablas(cursor, admin_id)
        poblar_datos(cursor, admin_id, horario_ids)
        
        conn.commit()
        print("\n✅ ¡Éxito! La base de datos ha sido limpiada y poblada correctamente.")
        
    except sqlite3.Error as e:
        print(f"\n❌ Error de SQLite: {e}", file=sys.stderr)
        if conn: conn.rollback()
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}", file=sys.stderr)
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()