"""
Script de migración para añadir el campo version_nombre a la tabla horario_academico
"""
from app import app, db
from models import HorarioAcademico, init_db
import sqlite3
import os

def migrate():
    """Añadir columna version_nombre a horario_academico"""
    
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
        
        print("🔄 Iniciando migración...")
        print(f"📂 Base de datos: {db_path}")
        
        # Verificar si la base de datos existe y tiene contenido
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("⚠️  Base de datos vacía o no existe. Inicializando...")
            init_db()
            print("✅ Base de datos inicializada")
        
        try:
            # Conectar directamente a SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='horario_academico'")
            if not cursor.fetchone():
                print("⚠️  Tabla 'horario_academico' no existe. Creando tablas...")
                conn.close()
                db.create_all()
                print("✅ Tablas creadas")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
            
            # Verificar si la columna ya existe
            cursor.execute("PRAGMA table_info(horario_academico)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'version_nombre' in columns:
                print("✅ La columna 'version_nombre' ya existe. No se requiere migración.")
                conn.close()
                return
            
            # Añadir la columna version_nombre
            print("➕ Añadiendo columna 'version_nombre'...")
            cursor.execute("""
                ALTER TABLE horario_academico 
                ADD COLUMN version_nombre VARCHAR(100)
            """)
            
            conn.commit()
            print("✅ Columna 'version_nombre' añadida exitosamente")
            
            # Actualizar registros existentes con un nombre de versión por defecto
            cursor.execute("SELECT COUNT(*) FROM horario_academico")
            total_registros = cursor.fetchone()[0]
            
            if total_registros > 0:
                print(f"🔄 Actualizando {total_registros} registros existentes...")
                cursor.execute("""
                    UPDATE horario_academico 
                    SET version_nombre = 'Versión anterior'
                    WHERE version_nombre IS NULL
                """)
                
                conn.commit()
                print(f"✅ {total_registros} registros actualizados")
            else:
                print("ℹ️  No hay registros existentes para actualizar")
            
            conn.close()
            print("\n🎉 ¡Migración completada exitosamente!")
            print("💡 Ahora puedes generar nuevos horarios con nombres de versión personalizados")
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
