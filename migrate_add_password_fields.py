#!/usr/bin/env python3
"""
Script de migración para agregar campos de contraseña temporal
"""

import sqlite3
import os

def migrate_database():
    """Agregar campos requiere_cambio_password y password_temporal a la tabla user"""
    
    # Ruta a la base de datos
    db_path = os.path.join('instance', 'sistema_academico.db')
    
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos en {db_path}")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Verificando estructura de la tabla user...")
        
        # Obtener información de las columnas existentes
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"📋 Columnas actuales: {', '.join(column_names)}")
        
        # Verificar si las columnas ya existen
        needs_migration = False
        
        if 'requiere_cambio_password' not in column_names:
            print("\n➕ Agregando columna 'requiere_cambio_password'...")
            cursor.execute("""
                ALTER TABLE user 
                ADD COLUMN requiere_cambio_password BOOLEAN DEFAULT 0
            """)
            print("✅ Columna 'requiere_cambio_password' agregada")
            needs_migration = True
        else:
            print("ℹ️  La columna 'requiere_cambio_password' ya existe")
        
        if 'password_temporal' not in column_names:
            print("\n➕ Agregando columna 'password_temporal'...")
            cursor.execute("""
                ALTER TABLE user 
                ADD COLUMN password_temporal VARCHAR(100)
            """)
            print("✅ Columna 'password_temporal' agregada")
            needs_migration = True
        else:
            print("ℹ️  La columna 'password_temporal' ya existe")
        
        if needs_migration:
            # Guardar cambios
            conn.commit()
            print("\n✅ Migración completada exitosamente")
            
            # Verificar la nueva estructura
            cursor.execute("PRAGMA table_info(user)")
            new_columns = cursor.fetchall()
            new_column_names = [col[1] for col in new_columns]
            print(f"\n📋 Columnas después de la migración: {', '.join(new_column_names)}")
        else:
            print("\n✅ No se requiere migración, todas las columnas ya existen")
        
        # Cerrar conexión
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ Error de SQLite: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        if conn:
            conn.close()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 MIGRACIÓN DE BASE DE DATOS")
    print("   Agregando campos de contraseña temporal")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Migración finalizada correctamente")
        print("=" * 60)
        print("\n✅ Ahora puedes ejecutar la aplicación normalmente:")
        print("   python app.py")
    else:
        print("\n" + "=" * 60)
        print("❌ La migración falló")
        print("=" * 60)
        print("\n⚠️  Revisa los errores anteriores")
