"""
Script de migración standalone para eliminar el campo aula de la tabla horario_academico
"""
import sqlite3
import os

def migrate():
    """Eliminar columna aula de horario_academico"""
    
    # Ruta directa a la base de datos
    db_path = '/Users/franciscotapia/Documents/sistema_login/instance/sistema_academico.db'
    
    print("🔄 Iniciando migración para eliminar campo 'aula'...")
    print(f"📂 Base de datos: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: No se encontró la base de datos en {db_path}")
        return
    
    try:
        # Conectar directamente a SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que la columna aula existe
        cursor.execute("PRAGMA table_info(horario_academico)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'aula' not in column_names:
            print("✅ La columna 'aula' ya no existe en la tabla horario_academico")
            conn.close()
            return
        
        print(f"📊 Columnas actuales: {', '.join(column_names)}")
        
        # SQLite no soporta DROP COLUMN directamente
        # Necesitamos crear una nueva tabla sin la columna aula
        
        # 1. Crear tabla temporal sin el campo aula
        print("1️⃣ Creando tabla temporal sin columna 'aula'...")
        cursor.execute("""
            CREATE TABLE horario_academico_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL,
                materia_id INTEGER,
                profesor_id INTEGER,
                dia VARCHAR(10),
                hora_inicio TIME,
                hora_fin TIME,
                periodo_academico VARCHAR(50),
                activo BOOLEAN DEFAULT 1,
                version_nombre VARCHAR(100),
                FOREIGN KEY(grupo_id) REFERENCES grupo (id) ON DELETE CASCADE,
                FOREIGN KEY(materia_id) REFERENCES materia (id) ON DELETE CASCADE,
                FOREIGN KEY(profesor_id) REFERENCES user (id) ON DELETE CASCADE
            )
        """)
        
        # 2. Copiar datos de la tabla original (excluyendo aula)
        print("2️⃣ Copiando datos a la nueva tabla...")
        cursor.execute("""
            INSERT INTO horario_academico_new 
            (id, grupo_id, materia_id, profesor_id, dia, hora_inicio, hora_fin, 
             periodo_academico, activo, version_nombre)
            SELECT id, grupo_id, materia_id, profesor_id, dia, hora_inicio, hora_fin,
                   periodo_academico, activo, version_nombre
            FROM horario_academico
        """)
        
        rows_copied = cursor.rowcount
        print(f"   ✅ {rows_copied} registros copiados")
        
        # 3. Eliminar tabla original
        print("3️⃣ Eliminando tabla original...")
        cursor.execute("DROP TABLE horario_academico")
        
        # 4. Renombrar tabla nueva
        print("4️⃣ Renombrando tabla nueva...")
        cursor.execute("ALTER TABLE horario_academico_new RENAME TO horario_academico")
        
        # Verificar resultado
        cursor.execute("PRAGMA table_info(horario_academico)")
        new_columns = cursor.fetchall()
        new_column_names = [col[1] for col in new_columns]
        
        print(f"📊 Columnas finales: {', '.join(new_column_names)}")
        
        # Confirmar cambios
        conn.commit()
        print("✅ Migración completada exitosamente")
        print(f"✅ {rows_copied} registros migrados")
        print("✅ Campo 'aula' eliminado de horario_academico")
        
    except sqlite3.Error as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("🔒 Conexión a la base de datos cerrada")

if __name__ == '__main__':
    migrate()
