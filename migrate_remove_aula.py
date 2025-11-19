"""
Script de migración para eliminar el campo aula de la tabla horario_academico
"""
from app import app
import sqlite3
import os

def migrate():
    """Eliminar columna aula de horario_academico"""
    
    with app.app_context():
        # Obtener la ruta de la base de datos
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            # Para SQLite relativo, usar la carpeta instance
            db_filename = db_uri.replace('sqlite:///', '')
            if not db_filename.startswith('/'):  # Es una ruta relativa
                db_path = os.path.join(app.instance_path, db_filename)
            else:
                db_path = db_filename
        else:
            db_path = os.path.join(app.instance_path, 'sistema_academico.db')
        
        print("🔄 Iniciando migración para eliminar campo 'aula'...")
        print(f"📂 Base de datos: {db_path}")
        
        try:
            # Conectar directamente a SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar si la columna existe
            cursor.execute("PRAGMA table_info(horario_academico)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'aula' not in columns:
                print("✅ La columna 'aula' ya no existe. No se requiere migración.")
                conn.close()
                return
            
            print("📋 Eliminando columna 'aula'...")
            print("ℹ️  SQLite requiere recrear la tabla para eliminar columnas...")
            
            # SQLite no soporta DROP COLUMN directamente, necesitamos recrear la tabla
            # 1. Crear tabla temporal con la nueva estructura
            cursor.execute("""
                CREATE TABLE horario_academico_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profesor_id INTEGER NOT NULL,
                    materia_id INTEGER NOT NULL,
                    horario_id INTEGER NOT NULL,
                    dia_semana VARCHAR(10) NOT NULL,
                    grupo VARCHAR(10) NOT NULL DEFAULT 'A',
                    periodo_academico VARCHAR(20),
                    version_nombre VARCHAR(100),
                    activo BOOLEAN DEFAULT 1,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                    creado_por INTEGER NOT NULL,
                    FOREIGN KEY (profesor_id) REFERENCES user (id),
                    FOREIGN KEY (materia_id) REFERENCES materia (id),
                    FOREIGN KEY (horario_id) REFERENCES horario (id),
                    FOREIGN KEY (creado_por) REFERENCES user (id)
                )
            """)
            
            # 2. Copiar datos de la tabla vieja a la nueva (sin la columna aula)
            cursor.execute("""
                INSERT INTO horario_academico_new 
                (id, profesor_id, materia_id, horario_id, dia_semana, grupo, 
                 periodo_academico, version_nombre, activo, fecha_creacion, creado_por)
                SELECT id, profesor_id, materia_id, horario_id, dia_semana, grupo,
                       periodo_academico, version_nombre, activo, fecha_creacion, creado_por
                FROM horario_academico
            """)
            
            # 3. Eliminar tabla vieja
            cursor.execute("DROP TABLE horario_academico")
            
            # 4. Renombrar tabla nueva
            cursor.execute("ALTER TABLE horario_academico_new RENAME TO horario_academico")
            
            conn.commit()
            print("✅ Columna 'aula' eliminada exitosamente")
            
            conn.close()
            print("\n🎉 ¡Migración completada exitosamente!")
            print("💡 La columna 'aula' ha sido removida de todos los horarios")
            print("💡 Reinicia la aplicación Flask para que los cambios tomen efecto")
            
        except Exception as e:
            print(f"\n❌ Error durante la migración: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
                conn.close()

if __name__ == '__main__':
    migrate()
