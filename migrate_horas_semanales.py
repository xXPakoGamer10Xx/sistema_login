"""
Script de migración: Consolidar horas_teoricas y horas_practicas en horas_semanales
"""
import sqlite3
import os

def migrar_horas_semanales():
    """Migrar de horas_teoricas/horas_practicas a horas_semanales"""
    
    db_path = 'instance/sistema_academico.db'
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos en {db_path}")
        return False
    
    print("🔄 Iniciando migración de sistema de horas...")
    print("=" * 70)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Agregar la columna horas_semanales
        print("\n1️⃣ Agregando columna 'horas_semanales'...")
        try:
            cursor.execute("ALTER TABLE materia ADD COLUMN horas_semanales INTEGER DEFAULT 0")
            conn.commit()
            print("   ✅ Columna 'horas_semanales' agregada")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⚠️  La columna 'horas_semanales' ya existe")
            else:
                raise
        
        # 2. Migrar datos: horas_semanales = horas_teoricas + horas_practicas
        print("\n2️⃣ Migrando datos existentes...")
        cursor.execute("SELECT id, codigo, horas_teoricas, horas_practicas FROM materia")
        materias = cursor.fetchall()
        
        for materia_id, codigo, horas_teoricas, horas_practicas in materias:
            horas_totales = (horas_teoricas or 0) + (horas_practicas or 0)
            cursor.execute(
                "UPDATE materia SET horas_semanales = ? WHERE id = ?",
                (horas_totales, materia_id)
            )
            print(f"   ✓ {codigo}: {horas_teoricas}h teóricas + {horas_practicas}h prácticas → {horas_totales}h semanales")
        
        conn.commit()
        print(f"\n   ✅ {len(materias)} materias migradas")
        
        # 3. Crear tabla nueva sin las columnas antiguas
        print("\n3️⃣ Recreando tabla sin columnas antiguas...")
        
        # Crear tabla temporal con la nueva estructura
        cursor.execute("""
            CREATE TABLE materia_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(200) NOT NULL,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                descripcion TEXT,
                cuatrimestre INTEGER NOT NULL,
                creditos INTEGER NOT NULL DEFAULT 3,
                horas_semanales INTEGER NOT NULL DEFAULT 0,
                carrera_id INTEGER NOT NULL,
                activa BOOLEAN DEFAULT 1,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                creado_por INTEGER NOT NULL,
                FOREIGN KEY (carrera_id) REFERENCES carrera (id),
                FOREIGN KEY (creado_por) REFERENCES user (id)
            )
        """)
        
        # Copiar datos a la nueva tabla
        cursor.execute("""
            INSERT INTO materia_new 
            (id, nombre, codigo, descripcion, cuatrimestre, creditos, horas_semanales, 
             carrera_id, activa, fecha_creacion, creado_por)
            SELECT 
                id, nombre, codigo, descripcion, cuatrimestre, creditos, horas_semanales,
                carrera_id, activa, fecha_creacion, creado_por
            FROM materia
        """)
        
        # Eliminar tabla antigua y renombrar la nueva
        cursor.execute("DROP TABLE materia")
        cursor.execute("ALTER TABLE materia_new RENAME TO materia")
        
        # Recrear índices
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_materia_codigo ON materia(codigo)")
        
        conn.commit()
        print("   ✅ Tabla recreada sin columnas antiguas")
        
        print("\n" + "=" * 70)
        print("✅ Migración completada exitosamente")
        print("\n📊 Resumen:")
        print(f"   - Materias migradas: {len(materias)}")
        print(f"   - Nuevo campo: horas_semanales")
        print(f"   - Campos eliminados: horas_teoricas, horas_practicas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        import traceback
        print(traceback.format_exc())
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    resultado = migrar_horas_semanales()
    if resultado:
        print("\n✅ Puedes continuar usando el sistema con el nuevo formato de horas")
    else:
        print("\n❌ La migración falló. Revisa los errores arriba.")
