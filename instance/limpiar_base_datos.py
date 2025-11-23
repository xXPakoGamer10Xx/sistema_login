import sqlite3
import sys
import os

# --- Constantes de Configuración ---
DB_NAME = 'sistema_academico.db'

# --- Lista de tablas a limpiar (Orden Crítico por Foreign Keys) ---
TABLAS_A_LIMPIAR = [
    'disponibilidad_profesor',
    'horario_academico',
    'profesor_materias',
    'grupo_materias',
    'user_carreras',    
    'usuario_carrera',
    'grupo',
    'materia',
    # 'user' y 'carrera' se limpian aparte para proteger al admin
]

def verificar_db():
    """Verifica si el archivo de base de datos existe."""
    if not os.path.exists(DB_NAME):
        print(f"❌ Error: No se encuentra el archivo '{DB_NAME}'.")
        sys.exit(1)

def obtener_admin_id(cursor):
    """Obtiene el ID del usuario 'admin' para no borrarlo."""
    cursor.execute("SELECT id FROM user WHERE username = 'admin'")
    resultado = cursor.fetchone()
    if not resultado:
        print("⚠️ Advertencia: No se encontró al usuario 'admin'. Se borrarán TODOS los usuarios.", file=sys.stderr)
        return None
    return resultado[0]

def limpiar_tablas(cursor, admin_id):
    """Borra datos y reinicia secuencias de autoincrement."""
    print("\n--- 🧹 LIMPIEZA DE BASE DE DATOS ---")
    
    # 1. Limpiar tablas estándar
    for tabla in TABLAS_A_LIMPIAR:
        try:
            # Verificar si la tabla existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}';")
            if cursor.fetchone():
                print(f"  - Vaciando tabla: {tabla}")
                cursor.execute(f"DELETE FROM {tabla};")
                
                # REINICIAR AUTOINCREMENT
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (tabla,))
            else:
                print(f"  - Saltando {tabla} (no existe)")
        except sqlite3.Error as e:
            print(f"    ❌ Error limpiando {tabla}: {e}")

    # 2. Limpiar USER (excepto admin)
    print("  - Limpiando 'user' (preservando admin)...")
    if admin_id:
        cursor.execute("DELETE FROM user WHERE id != ?;", (admin_id,))
    else:
        cursor.execute("DELETE FROM user;")
    
    # Reiniciar contador de user
    cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'user'")

    # 3. Limpiar CARRERA
    print("  - Limpiando 'carrera'...")
    try:
        cursor.execute("DELETE FROM carrera;")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'carrera'")
    except sqlite3.Error as e:
        print(f"    ❌ Error limpiando carrera: {e}")

    print("--- Limpieza completada ---\n")

def main():
    verificar_db()
    
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Obtener ID de admin para protegerlo
        admin_id = obtener_admin_id(cursor)
        
        # Ejecutar limpieza
        limpiar_tablas(cursor, admin_id)
        
        conn.commit()
        print("\n✅ BASE DE DATOS LIMPIA (Autoincrement reiniciado).")
        
    except sqlite3.Error as e:
        print(f"\n❌ Error CRÍTICO de Base de Datos: {e}")
        if conn: conn.rollback()
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()