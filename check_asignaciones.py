from app import app, db
from models import User, Materia, Grupo, AsignacionProfesorGrupo

with app.app_context():
    # Buscar los profesores
    print('=== PROFESORES ===')
    profesores = User.query.filter(User.nombre.ilike('%angel%') | User.nombre.ilike('%emiliano%')).all()
    for p in profesores:
        print(f'ID: {p.id}, Nombre: {p.nombre} {p.apellido}, Rol: {p.rol}, Activo: {p.activo}')
    
    print('\n=== MATERIA FUNDAMENTO DE REDES ===')
    materias = Materia.query.filter(Materia.nombre.ilike('%fundamento%redes%')).all()
    for m in materias:
        print(f'ID: {m.id}, Nombre: {m.nombre}, Codigo: {m.codigo}, Horas: {m.horas_semanales}')
        print(f'  Profesores asignados (M2M): {[f"{p.nombre} {p.apellido}" for p in m.profesores]}')
    
    print('\n=== ASIGNACIONES PROFESOR-GRUPO (AsignacionProfesorGrupo) ===')
    if materias:
        for m in materias:
            asigs = AsignacionProfesorGrupo.query.filter_by(materia_id=m.id).all()
            if not asigs:
                print(f'NO HAY ASIGNACIONES ESPECIFICAS PARA: {m.nombre}')
            for a in asigs:
                grupo = Grupo.query.get(a.grupo_id)
                profesor = User.query.get(a.profesor_id)
                print(f'Materia: {m.nombre}')
                print(f'  Grupo: {grupo.codigo if grupo else "N/A"}')
                print(f'  Profesor: {profesor.nombre if profesor else "N/A"} {profesor.apellido if profesor else ""}')
                print(f'  Activo: {a.activo}')
                print('---')
