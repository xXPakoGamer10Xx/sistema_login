"""
Script para limpiar asignaciones duplicadas de profesor-grupo-materia.
Deja solo una asignación activa por cada combinación grupo-materia.
"""
from app import app, db
from models import User, Materia, Grupo, AsignacionProfesorGrupo
from collections import defaultdict

with app.app_context():
    print("=" * 60)
    print("🔍 BUSCANDO ASIGNACIONES DUPLICADAS...")
    print("=" * 60)
    
    # Encontrar todas las combinaciones grupo_id + materia_id con múltiples activos
    duplicados = defaultdict(list)
    
    asignaciones = AsignacionProfesorGrupo.query.filter_by(activo=True).all()
    
    for asig in asignaciones:
        key = (asig.grupo_id, asig.materia_id)
        duplicados[key].append(asig)
    
    # Filtrar solo las que tienen más de una asignación activa
    duplicados_reales = {k: v for k, v in duplicados.items() if len(v) > 1}
    
    if not duplicados_reales:
        print("\n✅ No se encontraron asignaciones duplicadas.")
        print("   Cada grupo-materia tiene un único profesor asignado.")
    else:
        print(f"\n⚠️ Se encontraron {len(duplicados_reales)} combinaciones con múltiples profesores activos:\n")
        
        total_desactivadas = 0
        
        for (grupo_id, materia_id), asigs in duplicados_reales.items():
            grupo = Grupo.query.get(grupo_id)
            materia = Materia.query.get(materia_id)
            grupo_codigo = grupo.codigo if grupo else f"Grupo ID:{grupo_id}"
            materia_nombre = materia.nombre if materia else f"Materia ID:{materia_id}"
            
            print(f"📌 {grupo_codigo} / {materia_nombre}")
            
            # Ordenar por ID (el más reciente primero)
            asigs_ordenadas = sorted(asigs, key=lambda x: x.id, reverse=True)
            
            # El primero (más reciente) se mantiene activo
            mantener = asigs_ordenadas[0]
            profesor_mantener = User.query.get(mantener.profesor_id)
            print(f"   ✅ Mantener: {profesor_mantener.nombre if profesor_mantener else 'N/A'} (ID asig: {mantener.id})")
            
            # Los demás se desactivan
            for asig in asigs_ordenadas[1:]:
                profesor = User.query.get(asig.profesor_id)
                print(f"   ❌ Desactivar: {profesor.nombre if profesor else 'N/A'} (ID asig: {asig.id})")
                asig.activo = False
                total_desactivadas += 1
            
            print()
        
        # Confirmar antes de guardar
        print("=" * 60)
        respuesta = input(f"¿Desactivar {total_desactivadas} asignaciones duplicadas? (s/n): ")
        
        if respuesta.lower() == 's':
            db.session.commit()
            print(f"\n✅ Se desactivaron {total_desactivadas} asignaciones duplicadas.")
            print("   Ahora cada grupo-materia tiene un único profesor activo.")
        else:
            db.session.rollback()
            print("\n⚠️ Operación cancelada. No se realizaron cambios.")
