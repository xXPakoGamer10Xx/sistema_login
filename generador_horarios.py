"""
Módulo para generación automática de horarios académicos usando Google OR-Tools CP-SAT Solver
"""
from models import db, User, Horario, Carrera, Materia, HorarioAcademico
from datetime import datetime
from collections import defaultdict
import math

# Importación condicional de ortools
try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
    print("✅ OR-Tools cargado correctamente")
except ImportError as e:
    print(f"⚠️  OR-Tools no disponible: {e}")
    print("📦 Para instalarlo: pip install ortools")
    ORTOOLS_AVAILABLE = False
    cp_model = None

class GeneradorHorariosOR:
    """Clase para generar horarios académicos automáticamente usando Google OR-Tools"""

    def __init__(self, carrera_id, cuatrimestre, turno='matutino', dias_semana=None,
                 periodo_academico='2025-1', version_nombre=None, creado_por=None, grupo_id=None):
        """
        Inicializar el generador de horarios con OR-Tools

        Args:
            carrera_id: ID de la carrera
            cuatrimestre: Número del cuatrimestre
            turno: 'matutino', 'vespertino' o 'ambos'
            dias_semana: Lista de días de la semana ['lunes', 'martes', etc.]
            periodo_academico: Período académico (ej: '2025-1')
            version_nombre: Etiqueta de la versión (ej: 'Final', 'Borrador 1')
            creado_por: ID del usuario que genera los horarios
            grupo_id: (Nuevo) ID del grupo - si se proporciona, se usarán las materias y profesores del grupo
        """
        if not ORTOOLS_AVAILABLE:
            raise ImportError("OR-Tools no está disponible. Use GeneradorHorariosSinOR como alternativa.")
            
        self.carrera_id = carrera_id
        self.cuatrimestre = cuatrimestre
        self.turno = turno
        self.dias_semana = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        self.periodo_academico = periodo_academico
        self.version_nombre = version_nombre
        self.creado_por = creado_por
        self.grupo_id = grupo_id  # Nuevo parámetro

        # Datos del proceso
        self.profesores = []
        self.materias = []
        self.horarios = []
        self.disponibilidades = {}  # Cache de disponibilidades por profesor
        self.grupo = None  # Objeto Grupo si se proporciona grupo_id

        # Modelo CP-SAT
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Variables de decisión
        self.variables = {}  # (profesor_id, materia_id, horario_id, dia_idx) -> BoolVar

        # Resultados
        self.horarios_generados = []
        self.solucion_encontrada = False

    def cargar_datos(self):
        """Cargar datos necesarios para la generación"""
        from models import DisponibilidadProfesor, Grupo

        # Si se proporciona grupo_id, usar los datos del grupo
        if self.grupo_id:
            self.grupo = Grupo.query.get(self.grupo_id)
            if not self.grupo:
                raise ValueError(f"No se encontró el grupo con ID {self.grupo_id}")
            
            # Actualizar parámetros con los datos del grupo
            self.carrera_id = self.grupo.carrera_id
            self.cuatrimestre = self.grupo.cuatrimestre
            # Convertir turno de 'M'/'V' a 'matutino'/'vespertino'
            self.turno = 'matutino' if self.grupo.turno == 'M' else 'vespertino'
            
            # Obtener materias del grupo
            self.materias = [m for m in self.grupo.materias if m.activa]
            
            # Obtener profesores que imparten esas materias (solo los activos)
            profesores_set = set()
            for materia in self.materias:
                for profesor in materia.profesores:
                    if profesor.activo:
                        profesores_set.add(profesor)
            self.profesores = list(profesores_set)
            
            print(f"📚 Cargando datos del grupo {self.grupo.codigo}:")
            print(f"   - Carrera: {self.grupo.get_carrera_nombre()}")
            print(f"   - Cuatrimestre: {self.grupo.cuatrimestre}")
            print(f"   - Turno: {self.grupo.get_turno_display()} ({self.turno})")
            print(f"   - Materias asignadas: {len(self.materias)}")
            print(f"   - Profesores asignados: {len(self.profesores)}")
        else:
            # Enfoque legacy: cargar por carrera y cuatrimestre
            # Cargar profesores de la carrera
            self.profesores = User.query.filter(
                User.carrera_id == self.carrera_id,
                User.rol.in_(['profesor_completo', 'profesor_asignatura']),
                User.activo == True
            ).all()

            # Cargar materias del cuatrimestre
            self.materias = Materia.query.filter(
                Materia.carrera_id == self.carrera_id,
                Materia.cuatrimestre == self.cuatrimestre,
                Materia.activa == True
            ).all()
            
            print(f"📚 Cargando datos (modo legacy):")
            print(f"   - Carrera ID: {self.carrera_id}")
            print(f"   - Cuatrimestre: {self.cuatrimestre}")

        # Validaciones
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles para esta carrera")
        
        if not self.materias:
            raise ValueError("❌ No hay materias disponibles para este cuatrimestre")

        # Cargar horarios según el turno
        if self.turno == 'ambos':
            self.horarios = Horario.query.filter_by(activo=True).order_by(Horario.orden).all()
            print(f"⏰ Usando TODOS los horarios (ambos turnos)")
        else:
            self.horarios = Horario.query.filter_by(
                turno=self.turno,
                activo=True
            ).order_by(Horario.orden).all()
            print(f"⏰ Filtrando horarios solo del turno: {self.turno}")

        if not self.horarios:
            raise ValueError(f"❌ No hay horarios configurados para el turno {self.turno}")
        
        # Mostrar rango de horarios cargados
        if self.horarios:
            print(f"   📍 Horarios cargados: {self.horarios[0].get_hora_inicio_str()} - {self.horarios[-1].get_hora_fin_str()}")
            print(f"   📊 Total de bloques horarios: {len(self.horarios)}")

        # Cargar disponibilidades de profesores
        self.cargar_disponibilidades()

        # Validar horas de materias
        self.validar_horas_materias()

        print(f"✅ Datos cargados: {len(self.profesores)} profesores, {len(self.materias)} materias, {len(self.horarios)} horarios")

    def validar_horas_materias(self):
        """Validar que todas las materias tengan horas configuradas correctamente"""
        print("🔍 Validando horas de materias...")
        
        materias_sin_horas = []
        materias_con_horas = []
        total_horas_semanales = 0
        
        for materia in self.materias:
            horas_totales = materia.get_horas_totales()
            
            if horas_totales == 0:
                materias_sin_horas.append(materia)
            else:
                materias_con_horas.append((materia, horas_totales))
                total_horas_semanales += horas_totales
        
        # Mostrar resumen
        if materias_sin_horas:
            print(f"   ⚠️  {len(materias_sin_horas)} materias SIN horas configuradas:")
            for materia in materias_sin_horas:
                print(f"      - {materia.codigo} ({materia.nombre})")
            print(f"   📝 Estas materias usarán 3 horas por defecto")
        
        if materias_con_horas:
            print(f"   ✓ {len(materias_con_horas)} materias con horas configuradas:")
            for materia, horas in materias_con_horas:
                print(f"      - {materia.codigo}: {materia.horas_teoricas}h teóricas + {materia.horas_practicas}h prácticas = {horas}h/semana")
        
        print(f"   📊 Total horas semanales requeridas: {total_horas_semanales} horas")
        
        # Calcular si hay suficientes bloques horarios disponibles
        bloques_disponibles = len(self.horarios) * len(self.dias_semana)
        print(f"   📅 Bloques horarios disponibles: {bloques_disponibles} ({len(self.horarios)} horarios × {len(self.dias_semana)} días)")
        
        if total_horas_semanales > bloques_disponibles:
            print(f"   ⚠️  ADVERTENCIA: Se requieren {total_horas_semanales} horas pero solo hay {bloques_disponibles} bloques disponibles")

    def cargar_disponibilidades(self):
        """Cargar las disponibilidades de todos los profesores"""
        from models import DisponibilidadProfesor

        print("📋 Cargando disponibilidades de profesores...")
        
        for profesor in self.profesores:
            disponibilidades_profesor = DisponibilidadProfesor.query.filter(
                DisponibilidadProfesor.profesor_id == profesor.id,
                DisponibilidadProfesor.activo == True
            ).all()

            # Crear diccionario de disponibilidad por día y horario
            disponibilidad_dict = {}
            total_horas_disponibles = 0
            
            for dia in self.dias_semana:
                disponibilidad_dict[dia] = {}
                for horario in self.horarios:
                    # Buscar registro de disponibilidad específico
                    disp = next((d for d in disponibilidades_profesor
                               if d.dia_semana == dia and d.horario_id == horario.id), None)
                    
                    # IMPORTANTE: Si hay registro, usar su valor. Si NO hay registro, NO está disponible
                    # Esto asegura que el profesor solo pueda dar clases en las horas que marcó como disponibles
                    if disp:
                        disponibilidad_dict[dia][horario.id] = disp.disponible
                        if disp.disponible:
                            total_horas_disponibles += 1
                    else:
                        # Si no hay registro de disponibilidad, asumir NO disponible
                        # (el profesor debe marcar explícitamente sus horas disponibles)
                        disponibilidad_dict[dia][horario.id] = False

            self.disponibilidades[profesor.id] = disponibilidad_dict
            
            print(f"   ✓ {profesor.get_nombre_completo()}: {total_horas_disponibles} horas disponibles")
            
            # Advertencia si el profesor tiene muy pocas horas disponibles
            if total_horas_disponibles < 5:
                print(f"   ⚠️  ADVERTENCIA: Profesor {profesor.get_nombre_completo()} tiene solo {total_horas_disponibles} horas disponibles")

    def validar_datos(self):
        """Validar que hay suficientes datos para generar horarios"""
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles para esta carrera")

        if not self.materias:
            raise ValueError("❌ No hay materias disponibles para este cuatrimestre")

        if not self.horarios:
            raise ValueError(f"❌ No hay horarios disponibles para el turno {self.turno}")

        # Verificar que hay suficientes profesores para las materias
        if len(self.profesores) < len(self.materias):
            print(f"⚠️  Advertencia: Hay {len(self.profesores)} profesores para {len(self.materias)} materias")

        return True

    def crear_variables_decision(self):
        """Crear variables de decisión booleanas para el modelo CP-SAT"""
        print("🔧 Creando variables de decisión...")

        for profesor in self.profesores:
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx, dia in enumerate(self.dias_semana):
                        # Variable booleana: 1 si se asigna este profesor a esta materia en este horario y día
                        var_name = f"P{profesor.id}_M{materia.id}_H{horario.id}_D{dia_idx}"
                        self.variables[(profesor.id, materia.id, horario.id, dia_idx)] = self.model.NewBoolVar(var_name)

        print(f"✅ Creadas {len(self.variables)} variables de decisión")

    def agregar_restricciones(self):
        """Agregar todas las restricciones al modelo CP-SAT"""
        print("🔒 Agregando restricciones...")

        # 1. Cada materia debe tener exactamente las horas requeridas por semana
        self.restriccion_horas_materia()

        # 2. Un profesor no puede tener dos clases al mismo tiempo
        self.restriccion_no_conflicto_profesor()

        # 3. Un profesor no puede dar clases cuando no está disponible
        self.restriccion_disponibilidad_profesor()

        # 4. Un aula/horario no puede tener dos clases al mismo tiempo (simplificado)
        self.restriccion_no_conflicto_horario()

        # 5. Restricciones de carga horaria por profesor (semanal)
        self.restriccion_carga_horaria_profesor()

        # 6. Restricción: máximo 8 horas diarias por profesor
        self.restriccion_horas_diarias_profesor()

        # 7. Restricciones de distribución óptima de horas por materia (máx 3 horas seguidas)
        self.restriccion_distribucion_horas_materia()

        # 8. Restricciones para evitar conflictos entre carreras
        self.restriccion_conflictos_entre_carreras()

        print("✅ Todas las restricciones agregadas")

    def restriccion_horas_materia(self):
        """
        Cada materia debe tener exactamente las horas requeridas por semana
        Usa horas_teoricas + horas_practicas configuradas en cada materia
        """
        print("📚 Aplicando restricción de horas semanales por materia...")
        
        for materia in self.materias:
            horas_requeridas = self.calcular_horas_semanales_materia(materia)

            # Suma de todas las asignaciones para esta materia debe ser igual a horas requeridas
            asignaciones_materia = []
            for profesor in self.profesores:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_materia.append(var)

            if asignaciones_materia:
                self.model.Add(sum(asignaciones_materia) == horas_requeridas)
                print(f"   ✓ {materia.codigo} ({materia.nombre}): {materia.horas_teoricas}h teóricas + {materia.horas_practicas}h prácticas = {horas_requeridas}h/semana")

    def restriccion_no_conflicto_profesor(self):
        """Un profesor no puede tener dos clases al mismo tiempo"""
        for profesor in self.profesores:
            for horario in self.horarios:
                for dia_idx in range(len(self.dias_semana)):
                    # En un mismo horario y día, un profesor solo puede tener una materia
                    asignaciones_profesor_horario = []
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor_horario.append(var)

                    if asignaciones_profesor_horario:
                        self.model.Add(sum(asignaciones_profesor_horario) <= 1)

    def restriccion_disponibilidad_profesor(self):
        """Un profesor solo puede dar clases en las horas que marcó como disponibles"""
        print("📅 Aplicando restricción de disponibilidad de profesores...")
        
        restricciones_aplicadas = 0
        
        for profesor in self.profesores:
            for horario in self.horarios:
                for dia_idx, dia in enumerate(self.dias_semana):
                    # Verificar si el profesor está disponible en este horario y día
                    disponible = self.verificar_disponibilidad_profesor(profesor.id, horario.id, dia)

                    if not disponible:
                        # El profesor NO está disponible: forzar que no tenga clase
                        for materia in self.materias:
                            var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                self.model.Add(var == 0)
                                restricciones_aplicadas += 1
        
        print(f"   ✓ Se aplicaron {restricciones_aplicadas} restricciones de disponibilidad")

    def restriccion_no_conflicto_horario(self):
        """Un horario no puede tener dos clases al mismo tiempo (simplificación)"""
        # Esta es una simplificación. En un sistema real, consideraríamos aulas específicas
        for horario in self.horarios:
            for dia_idx in range(len(self.dias_semana)):
                # En un mismo horario y día, máximo una clase (simplificación)
                asignaciones_horario = []
                for profesor in self.profesores:
                    for materia in self.materias:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_horario.append(var)

                if asignaciones_horario:
                    self.model.Add(sum(asignaciones_horario) <= 1)

    def restriccion_carga_horaria_profesor(self):
        """Restricciones de carga horaria máxima por profesor (semanal)"""
        for profesor in self.profesores:
            # Calcular carga horaria máxima según tipo de profesor
            if profesor.is_profesor_completo():
                max_horas = 40  # 40 horas semanales para tiempo completo
            else:
                max_horas = 20  # 20 horas semanales para asignatura

            # Suma de todas las asignaciones del profesor
            asignaciones_profesor = []
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor.append(var)

            if asignaciones_profesor:
                self.model.Add(sum(asignaciones_profesor) <= max_horas)

    def restriccion_horas_diarias_profesor(self):
        """Un profesor no puede trabajar más de 8 horas al día"""
        for profesor in self.profesores:
            for dia_idx in range(len(self.dias_semana)):
                # Suma de todas las horas asignadas en este día
                asignaciones_profesor_dia = []
                for materia in self.materias:
                    for horario in self.horarios:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_profesor_dia.append(var)
                
                if asignaciones_profesor_dia:
                    # Máximo 8 horas por día
                    self.model.Add(sum(asignaciones_profesor_dia) <= 8)
                    print(f"✓ Restricción: Profesor {profesor.get_nombre_completo()} - máx 8h/día en {self.dias_semana[dia_idx]}")

    def restriccion_distribucion_horas_materia(self):
        """
        Distribuir horas de manera óptima:
        - Máximo 3 horas SEGUIDAS de la misma materia por día
        - Preferir distribución uniforme a lo largo de la semana
        """
        print("📊 Aplicando restricción de distribución de horas por materia...")
        
        for materia in self.materias:
            horas_requeridas = self.calcular_horas_semanales_materia(materia)
            
            # RESTRICCIÓN PRINCIPAL: Máximo 3 horas por día de la misma materia
            for dia_idx in range(len(self.dias_semana)):
                asignaciones_materia_dia = []
                for profesor in self.profesores:
                    for horario in self.horarios:
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            asignaciones_materia_dia.append(var)
                
                if asignaciones_materia_dia:
                    # ⚠️ IMPORTANTE: Máximo 3 horas por día de la misma materia
                    self.model.Add(sum(asignaciones_materia_dia) <= 3)
            
            print(f"   ✓ Materia {materia.codigo}: {horas_requeridas}h/semana, máx 3h/día")
            
            # Distribución preferida: si son 5 horas, preferir 1 hora por día
            if horas_requeridas == 5:
                for dia_idx in range(len(self.dias_semana)):
                    asignaciones_materia_dia = []
                    for profesor in self.profesores:
                        for horario in self.horarios:
                            var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_materia_dia.append(var)
                    
                    if asignaciones_materia_dia:
                        # Preferir 1 hora por día para materias de 5 horas
                        self.model.Add(sum(asignaciones_materia_dia) <= 1)
            
            # Para materias con muchas horas, distribuir en varios días
            elif horas_requeridas > 5:
                dias_minimos = min(len(self.dias_semana), math.ceil(horas_requeridas / 3))
                dias_con_clase = []
                
                for dia_idx in range(len(self.dias_semana)):
                    # Variable que indica si hay clase este día
                    dia_tiene_clase = self.model.NewBoolVar(f"materia_{materia.id}_dia_{dia_idx}")
                    
                    asignaciones_materia_dia = []
                    for profesor in self.profesores:
                        for horario in self.horarios:
                            var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                            if var is not None:
                                asignaciones_materia_dia.append(var)
                    
                    if asignaciones_materia_dia:
                        # Si hay al menos una clase, el día tiene clase
                        self.model.Add(sum(asignaciones_materia_dia) >= dia_tiene_clase)
                        self.model.Add(sum(asignaciones_materia_dia) <= 3 * dia_tiene_clase)
                        dias_con_clase.append(dia_tiene_clase)
                
                # Forzar distribución en múltiples días
                if dias_con_clase:
                    self.model.Add(sum(dias_con_clase) >= dias_minimos)

    def restriccion_conflictos_entre_carreras(self):
        """Evitar que profesores tengan clases simultáneas en diferentes carreras"""
        # Obtener todos los profesores que imparten en múltiples carreras
        profesores_multiples_carreras = []
        
        for profesor in self.profesores:
            # Verificar si el profesor imparte en otras carreras
            carreras_profesor = set()
            
            # Agregar la carrera actual
            carreras_profesor.add(self.carrera_id)
            
            # Buscar materias del profesor en otras carreras
            otras_materias = Materia.query.filter(
                Materia.id.in_([m.id for m in profesor.materias]),
                Materia.carrera_id != self.carrera_id,
                Materia.activa == True
            ).all()
            
            for materia in otras_materias:
                carreras_profesor.add(materia.carrera_id)
            
            if len(carreras_profesor) > 1:
                profesores_multiples_carreras.append(profesor.id)
                print(f"⚠️  Profesor {profesor.get_nombre_completo()} imparte en {len(carreras_profesor)} carreras")
        
        # Para profesores que imparten en múltiples carreras, verificar conflictos
        for profesor_id in profesores_multiples_carreras:
            # Obtener horarios académicos existentes de otras carreras para este profesor
            horarios_existentes = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == profesor_id,
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).join(Materia).filter(
                Materia.carrera_id != self.carrera_id
            ).all()
            
            # Para cada horario existente, evitar asignaciones conflictivas
            for horario_existente in horarios_existentes:
                dia_idx = self.dias_semana.index(horario_existente.dia_semana) if horario_existente.dia_semana in self.dias_semana else -1
                
                if dia_idx >= 0:
                    # No asignar este profesor en el mismo horario y día
                    for materia in self.materias:
                        var = self.variables.get((profesor_id, materia.id, horario_existente.horario_id, dia_idx))
                        if var is not None:
                            self.model.Add(var == 0)  # Forzar que no se asigne

    def agregar_funcion_objetivo(self):
        """Agregar función objetivo para optimizar la distribución"""
        print("🎯 Agregando función objetivo...")

        # Objetivo: minimizar la varianza en la carga horaria de profesores
        # (distribuir equitativamente la carga de trabajo)

        # Calcular la carga horaria de cada profesor
        cargas_horarias = []
        for profesor in self.profesores:
            carga_profesor = []
            for materia in self.materias:
                for horario in self.horarios:
                    for dia_idx in range(len(self.dias_semana)):
                        var = self.variables.get((profesor.id, materia.id, horario.id, dia_idx))
                        if var is not None:
                            carga_profesor.append(var)

            if carga_profesor:
                cargas_horarias.append(sum(carga_profesor))

        if cargas_horarias:
            # En lugar de minimizar varianza (que requiere operaciones no soportadas),
            # minimizamos la diferencia entre la carga máxima y mínima
            # Esto es más simple y logra una distribución más equitativa
            
            n_profesores = len(cargas_horarias)
            if n_profesores > 1:
                # Crear variables para max y min
                max_carga = self.model.NewIntVar(0, 50, 'max_carga')
                min_carga = self.model.NewIntVar(0, 50, 'min_carga')
                
                # max_carga debe ser mayor o igual a todas las cargas
                for carga in cargas_horarias:
                    self.model.Add(max_carga >= carga)
                
                # min_carga debe ser menor o igual a todas las cargas
                for carga in cargas_horarias:
                    self.model.Add(min_carga <= carga)
                
                # Minimizar la diferencia entre máximo y mínimo
                diferencia = max_carga - min_carga
                self.model.Minimize(diferencia)

    def resolver_modelo(self):
        """Resolver el modelo CP-SAT"""
        print("🧠 Resolviendo modelo CP-SAT...")

        # Configurar solver
        self.solver.parameters.max_time_in_seconds = 300.0  # 5 minutos máximo
        self.solver.parameters.num_search_workers = 8  # Usar múltiples hilos

        # Resolver
        status = self.solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            self.solucion_encontrada = True
            print("✅ ¡Solución encontrada!")
            return True
        else:
            print(f"❌ No se encontró solución. Estado: {status}")
            return False

    def interpretar_solucion(self):
        """Interpretar la solución encontrada y crear los horarios académicos"""
        print("📋 Interpretando solución...")

        # Limpiar horarios existentes para este período y carrera
        HorarioAcademico.query.filter(
            HorarioAcademico.periodo_academico == self.periodo_academico,
            HorarioAcademico.activo == True
        ).update({'activo': False})
        db.session.commit()

        horarios_creados = []

        # Recorrer todas las variables para encontrar asignaciones
        for (profesor_id, materia_id, horario_id, dia_idx), var in self.variables.items():
            if self.solver.Value(var) == 1:  # Si la variable es verdadera
                dia = self.dias_semana[dia_idx]

                # Crear horario académico
                horario_academico = HorarioAcademico(
                    profesor_id=profesor_id,
                    materia_id=materia_id,
                    horario_id=horario_id,
                    dia_semana=dia,
                    periodo_academico=self.periodo_academico,
                    version_nombre=self.version_nombre,
                    creado_por=self.creado_por
                )

                db.session.add(horario_academico)
                horarios_creados.append(horario_academico)

                print(f"📅 Asignado: Prof {profesor_id} → Materia {materia_id} en {dia} horario {horario_id}")

        # Confirmar cambios
        db.session.commit()
        self.horarios_generados = horarios_creados

        print(f"✅ Se crearon {len(horarios_creados)} horarios académicos")
        return horarios_creados

    def calcular_horas_semanales_materia(self, materia):
        """
        Calcular horas semanales necesarias para una materia
        Usa las horas teóricas + horas prácticas configuradas en la materia
        """
        # Obtener horas totales (teóricas + prácticas)
        horas_teoricas = materia.horas_teoricas if materia.horas_teoricas else 0
        horas_practicas = materia.horas_practicas if materia.horas_practicas else 0
        horas_totales = horas_teoricas + horas_practicas
        
        # Validación: mínimo 1 hora, máximo razonable 15 horas
        if horas_totales < 1:
            print(f"⚠️  Advertencia: Materia {materia.codigo} no tiene horas configuradas. Usando 3 horas por defecto.")
            return 3
        
        if horas_totales > 15:
            print(f"⚠️  Advertencia: Materia {materia.codigo} tiene {horas_totales} horas (muy alto). Limitando a 15 horas.")
            return 15
        
        return horas_totales

    def verificar_disponibilidad_profesor(self, profesor_id, horario_id, dia_semana):
        """Verificar si un profesor está disponible en ese horario y día"""
        if profesor_id not in self.disponibilidades:
            return True  # Si no hay registro de disponibilidad, asumir disponible

        disponibilidad_dia = self.disponibilidades[profesor_id].get(dia_semana, {})
        return disponibilidad_dia.get(horario_id, True)  # Por defecto disponible

    def generar_horarios(self):
        """Generar horarios académicos usando OR-Tools"""
        print("🚀 Iniciando generación de horarios con Google OR-Tools CP-SAT...")
        print("="*70)
        print("📋 RESTRICCIONES APLICADAS:")
        print("   1. ✓ Cada materia debe tener sus horas semanales requeridas")
        print("   2. ✓ Un profesor NO puede tener dos clases simultáneas")
        print("   3. ✓ Profesores SOLO dan clases en horas marcadas como disponibles")
        print("   4. ✓ Máximo 3 HORAS SEGUIDAS de la misma materia por día")
        print("   5. ✓ Máximo 8 HORAS de trabajo por día por profesor")
        print("   6. ✓ Carga máxima semanal: 40h (tiempo completo) / 20h (asignatura)")
        print("   7. ✓ Sin conflictos de horario entre carreras")
        print("="*70)

        try:
            # Cargar y validar datos
            self.cargar_datos()
            self.validar_datos()

            # Crear modelo
            self.crear_variables_decision()
            self.agregar_restricciones()
            self.agregar_funcion_objetivo()

            # Resolver
            if self.resolver_modelo():
                horarios_generados = self.interpretar_solucion()
                estadisticas = self.obtener_estadisticas()

                return {
                    'exito': True,
                    'mensaje': f'✅ Se generaron {len(horarios_generados)} horarios académicos exitosamente usando OR-Tools',
                    'estadisticas': estadisticas,
                    'horarios_generados': horarios_generados,
                    'algoritmo': 'Google OR-Tools CP-SAT Solver'
                }
            else:
                return {
                    'exito': False,
                    'mensaje': '❌ No se pudo encontrar una solución factible con las restricciones dadas',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': 'Google OR-Tools CP-SAT Solver'
                }

        except Exception as e:
            db.session.rollback()
            return {
                'exito': False,
                'mensaje': f'❌ Error al generar horarios: {str(e)}',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': 'Google OR-Tools CP-SAT Solver'
            }

    def obtener_estadisticas(self):
        """Obtener estadísticas de la generación con detalles de horas por materia"""
        if not self.horarios_generados:
            return {
                'total_horarios': 0,
                'profesores_utilizados': 0,
                'materias_asignadas': 0,
                'materias_totales': len(self.materias),
                'profesores_totales': len(self.profesores),
                'eficiencia': 0.0,
                'horas_por_materia': {}
            }

        total_horarios = len(self.horarios_generados)
        profesores_utilizados = len(set(h.profesor_id for h in self.horarios_generados))
        materias_asignadas = len(set(h.materia_id for h in self.horarios_generados))

        eficiencia = (materias_asignadas / len(self.materias)) * 100 if self.materias else 0

        # Calcular horas asignadas por materia
        horas_por_materia = {}
        for materia in self.materias:
            horas_asignadas = sum(1 for h in self.horarios_generados if h.materia_id == materia.id)
            horas_requeridas = self.calcular_horas_semanales_materia(materia)
            horas_por_materia[materia.codigo] = {
                'nombre': materia.nombre,
                'horas_requeridas': horas_requeridas,
                'horas_asignadas': horas_asignadas,
                'horas_teoricas': materia.horas_teoricas,
                'horas_practicas': materia.horas_practicas,
                'completado': horas_asignadas == horas_requeridas
            }

        return {
            'total_horarios': total_horarios,
            'profesores_utilizados': profesores_utilizados,
            'materias_asignadas': materias_asignadas,
            'materias_totales': len(self.materias),
            'profesores_totales': len(self.profesores),
            'eficiencia': eficiencia,
            'horas_por_materia': horas_por_materia
        }


class GeneradorHorariosSinOR:
    """Generador de horarios que funciona sin OR-Tools como respaldo"""
    
    def __init__(self, carrera_id, cuatrimestre, turno='matutino', dias_semana=None,
                 periodo_academico='2025-1', version_nombre=None, creado_por=None, grupo_id=None):
        """Inicializar el generador de horarios sin OR-Tools"""
        self.carrera_id = carrera_id
        self.cuatrimestre = cuatrimestre
        self.turno = turno
        self.dias_semana = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        self.periodo_academico = periodo_academico
        self.version_nombre = version_nombre
        self.creado_por = creado_por
        self.grupo_id = grupo_id  # Nuevo parámetro
        
        # Datos del proceso
        self.profesores = []
        self.materias = []
        self.horarios = []
        self.disponibilidades = {}
        self.horarios_generados = []
        self.grupo = None  # Objeto Grupo si se proporciona grupo_id
        
        # Cache para evitar conflictos
        self.asignaciones_profesor = defaultdict(list)  # profesor_id -> [(horario_id, dia)]
        self.asignaciones_horario = defaultdict(list)   # (horario_id, dia) -> materia_id
    
    def cargar_datos(self):
        """Cargar datos necesarios para la generación"""
        from models import DisponibilidadProfesor, Grupo

        # Si se proporciona grupo_id, usar los datos del grupo
        if self.grupo_id:
            self.grupo = Grupo.query.get(self.grupo_id)
            if not self.grupo:
                raise ValueError(f"No se encontró el grupo con ID {self.grupo_id}")
            
            # Obtener materias del grupo
            self.materias = [m for m in self.grupo.materias if m.activa]
            
            # Obtener profesores que imparten esas materias (solo los activos)
            profesores_set = set()
            for materia in self.materias:
                for profesor in materia.profesores:
                    if profesor.activo:
                        profesores_set.add(profesor)
            self.profesores = list(profesores_set)
            
            print(f"📚 Cargando datos del grupo {self.grupo.codigo} (algoritmo respaldo):")
            print(f"   - Materias asignadas: {len(self.materias)}")
            print(f"   - Profesores asignados: {len(self.profesores)}")
        else:
            # Enfoque legacy: cargar por carrera y cuatrimestre
            # Cargar profesores de la carrera
            self.profesores = User.query.filter(
                User.carrera_id == self.carrera_id,
                User.rol.in_(['profesor_completo', 'profesor_asignatura']),
                User.activo == True
            ).all()

            # Cargar materias del cuatrimestre
            self.materias = Materia.query.filter(
                Materia.carrera_id == self.carrera_id,
                Materia.cuatrimestre == self.cuatrimestre,
                Materia.activa == True
            ).all()

        # Validaciones
        if not self.profesores:
            raise ValueError("❌ No hay profesores disponibles")
        
        if not self.materias:
            raise ValueError("❌ No hay materias disponibles")

        # Cargar horarios según el turno
        if self.turno == 'ambos':
            self.horarios = Horario.query.filter_by(activo=True).order_by(Horario.orden).all()
        else:
            self.horarios = Horario.query.filter_by(
                turno=self.turno,
                activo=True
            ).order_by(Horario.orden).all()

        # Cargar disponibilidades
        self.cargar_disponibilidades()
        
        # Cargar horarios existentes de otras carreras para evitar conflictos
        self.cargar_conflictos_existentes()

        print(f"✅ Datos cargados: {len(self.profesores)} profesores, {len(self.materias)} materias, {len(self.horarios)} horarios")
    
    def cargar_disponibilidades(self):
        """Cargar disponibilidades de profesores"""
        from models import DisponibilidadProfesor
        
        for profesor in self.profesores:
            disponibilidades_profesor = DisponibilidadProfesor.query.filter(
                DisponibilidadProfesor.profesor_id == profesor.id,
                DisponibilidadProfesor.activo == True
            ).all()

            disponibilidad_dict = {}
            for dia in self.dias_semana:
                disponibilidad_dict[dia] = {}
                for horario in self.horarios:
                    disp = next((d for d in disponibilidades_profesor
                               if d.dia_semana == dia and d.horario_id == horario.id), None)
                    disponibilidad_dict[dia][horario.id] = disp.disponible if disp else True

            self.disponibilidades[profesor.id] = disponibilidad_dict
    
    def cargar_conflictos_existentes(self):
        """Cargar horarios existentes para evitar conflictos"""
        for profesor in self.profesores:
            horarios_existentes = HorarioAcademico.query.filter(
                HorarioAcademico.profesor_id == profesor.id,
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).join(Materia).filter(
                Materia.carrera_id != self.carrera_id
            ).all()
            
            for horario_existente in horarios_existentes:
                if horario_existente.dia_semana in self.dias_semana:
                    clave_horario = (horario_existente.horario_id, horario_existente.dia_semana)
                    self.asignaciones_profesor[profesor.id].append(clave_horario)
    
    def generar_horarios(self):
        """Generar horarios usando algoritmo greedy mejorado"""
        print("🚀 Iniciando generación con algoritmo de respaldo...")
        
        try:
            self.cargar_datos()
            
            if not self.profesores or not self.materias or not self.horarios:
                return {
                    'exito': False,
                    'mensaje': "❌ Datos insuficientes para generar horarios",
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': 'Algoritmo de Respaldo'
                }
            
            # Limpiar horarios existentes
            HorarioAcademico.query.filter(
                HorarioAcademico.periodo_academico == self.periodo_academico,
                HorarioAcademico.activo == True
            ).update({'activo': False})
            db.session.commit()
            
            # Generar asignaciones
            exito = self.asignar_materias_a_profesores()
            
            if exito:
                estadisticas = self.obtener_estadisticas()
                return {
                    'exito': True,
                    'mensaje': f'✅ Se generaron {len(self.horarios_generados)} horarios académicos usando algoritmo de respaldo',
                    'estadisticas': estadisticas,
                    'horarios_generados': self.horarios_generados,
                    'algoritmo': 'Algoritmo de Respaldo (Greedy Mejorado)'
                }
            else:
                return {
                    'exito': False,
                    'mensaje': "❌ No se pudieron asignar todas las materias con las restricciones dadas",
                    'estadisticas': None,
                    'horarios_generados': self.horarios_generados,
                    'algoritmo': 'Algoritmo de Respaldo'
                }
                
        except Exception as e:
            db.session.rollback()
            return {
                'exito': False,
                'mensaje': f'❌ Error al generar horarios: {str(e)}',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': 'Algoritmo de Respaldo'
            }
    
    def asignar_materias_a_profesores(self):
        """Asignar materias a profesores usando algoritmo greedy"""
        materias_pendientes = list(self.materias)
        
        print(f"\n📊 Iniciando asignación de {len(materias_pendientes)} materias")
        print(f"👥 Profesores disponibles: {len(self.profesores)}")
        for profesor in self.profesores:
            print(f"   - {profesor.get_nombre_completo()}: {len(profesor.materias)} materias asignadas")
        
        # Ordenar materias por horas requeridas (descendente) y por dificultad de asignación
        materias_pendientes.sort(key=lambda m: (-self.calcular_horas_semanales_materia(m), m.nombre))
        
        materias_asignadas_exitosamente = 0
        
        for materia in materias_pendientes:
            print(f"\n📚 Procesando materia: {materia.nombre} (ID: {materia.id})")
            print(f"   Horas requeridas: {self.calcular_horas_semanales_materia(materia)}")
            
            # Buscar profesores que pueden impartir esta materia
            profesores_disponibles = [p for p in self.profesores if materia in p.materias]
            
            print(f"   Profesores que pueden impartir esta materia: {len(profesores_disponibles)}")
            for p in profesores_disponibles:
                print(f"      - {p.get_nombre_completo()}")
            
            if not profesores_disponibles:
                print(f"   ⚠️  No hay profesores disponibles para {materia.nombre}")
                print(f"   📋 Verificando: esta materia está en las materias de los profesores?")
                for profesor in self.profesores:
                    materia_ids = [m.id for m in profesor.materias]
                    print(f"      - {profesor.get_nombre_completo()}: materias {materia_ids}")
                continue
            
            # Ordenar profesores por carga actual (ascendente)
            profesores_disponibles.sort(key=lambda p: len(self.asignaciones_profesor[p.id]))
            
            asignado = False
            for profesor in profesores_disponibles:
                if self.asignar_materia_a_profesor(materia, profesor):
                    print(f"   ✅ {materia.nombre} asignada a {profesor.get_nombre_completo()}")
                    asignado = True
                    materias_asignadas_exitosamente += 1
                    break
            
            if not asignado:
                print(f"   ❌ No se pudo asignar {materia.nombre}")
                print(f"   📊 Resumen hasta ahora: {materias_asignadas_exitosamente}/{len(materias_pendientes)} materias asignadas")
                return False
        
        print(f"\n✅ Todas las materias fueron asignadas exitosamente!")
        print(f"📊 Total: {materias_asignadas_exitosamente}/{len(materias_pendientes)} materias")
        return True
    
    def asignar_materia_a_profesor(self, materia, profesor):
        """Asignar una materia específica a un profesor específico"""
        horas_requeridas = self.calcular_horas_semanales_materia(materia)
        horarios_asignados = []
        
        # Estrategia de distribución según horas requeridas
        if horas_requeridas <= 5:
            # 1-5 horas: distribuir una hora por día preferentemente
            horarios_asignados = self.distribuir_horas_dispersas(profesor, materia, horas_requeridas)
        else:
            # Más de 5 horas: permitir hasta 3 horas por día
            horarios_asignados = self.distribuir_horas_agrupadas(profesor, materia, horas_requeridas)
        
        if len(horarios_asignados) == horas_requeridas:
            # Crear los horarios académicos
            for horario_id, dia in horarios_asignados:
                horario_academico = HorarioAcademico(
                    profesor_id=profesor.id,
                    materia_id=materia.id,
                    horario_id=horario_id,
                    dia_semana=dia,
                    periodo_academico=self.periodo_academico,
                    version_nombre=self.version_nombre,
                    creado_por=self.creado_por
                )
                db.session.add(horario_academico)
                self.horarios_generados.append(horario_academico)
                
                # Actualizar cache
                self.asignaciones_profesor[profesor.id].append((horario_id, dia))
                self.asignaciones_horario[(horario_id, dia)].append(materia.id)
            
            db.session.commit()
            return True
        
        return False
    
    def distribuir_horas_dispersas(self, profesor, materia, horas_requeridas):
        """Distribuir horas de manera dispersa (ideal para materias de 1-5 horas)"""
        horarios_asignados = []
        dias_utilizados = set()
        
        # Intentar asignar una hora por día
        for dia in self.dias_semana:
            if len(horarios_asignados) >= horas_requeridas:
                break
                
            horario_encontrado = self.buscar_horario_disponible(profesor, dia, 1)
            if horario_encontrado:
                horarios_asignados.extend(horario_encontrado)
                dias_utilizados.add(dia)
        
        # Si faltan horas, asignar máximo 2 horas adicionales por día ya utilizado
        if len(horarios_asignados) < horas_requeridas:
            for dia in dias_utilizados:
                if len(horarios_asignados) >= horas_requeridas:
                    break
                    
                horas_adicionales_dia = sum(1 for h, d in horarios_asignados if d == dia)
                if horas_adicionales_dia < 2:  # Máximo 2 horas por día
                    horario_encontrado = self.buscar_horario_disponible(profesor, dia, 1)
                    if horario_encontrado:
                        horarios_asignados.extend(horario_encontrado)
        
        return horarios_asignados
    
    def distribuir_horas_agrupadas(self, profesor, materia, horas_requeridas):
        """Distribuir horas permitiendo agrupación (para materias de más de 5 horas)"""
        horarios_asignados = []
        
        # Calcular distribución óptima
        dias_necesarios = min(len(self.dias_semana), math.ceil(horas_requeridas / 3))
        horas_por_dia = horas_requeridas // dias_necesarios
        horas_extra = horas_requeridas % dias_necesarios
        
        dias_asignados = 0
        for dia in self.dias_semana:
            if dias_asignados >= dias_necesarios:
                break
                
            horas_dia = horas_por_dia + (1 if dias_asignados < horas_extra else 0)
            horas_dia = min(horas_dia, 3)  # Máximo 3 horas por día
            
            horarios_dia = self.buscar_horario_disponible(profesor, dia, horas_dia)
            if len(horarios_dia) == horas_dia:
                horarios_asignados.extend(horarios_dia)
                dias_asignados += 1
        
        return horarios_asignados
    
    def buscar_horario_disponible(self, profesor, dia, horas_necesarias):
        """Buscar horarios disponibles para un profesor en un día específico"""
        horarios_encontrados = []
        
        for horario in self.horarios:
            if len(horarios_encontrados) >= horas_necesarias:
                break
                
            # Verificar disponibilidad del profesor
            if not self.verificar_disponibilidad_profesor(profesor.id, horario.id, dia):
                continue
            
            # Verificar que no haya conflictos
            clave_horario = (horario.id, dia)
            if clave_horario in self.asignaciones_profesor[profesor.id]:
                continue
            
            # Verificar que el horario no esté ocupado
            if self.asignaciones_horario[clave_horario]:
                continue
            
            horarios_encontrados.append((horario.id, dia))
        
        return horarios_encontrados
    
    def verificar_disponibilidad_profesor(self, profesor_id, horario_id, dia_semana):
        """Verificar disponibilidad de un profesor"""
        if profesor_id not in self.disponibilidades:
            return True
        
        disponibilidad_dia = self.disponibilidades[profesor_id].get(dia_semana, {})
        return disponibilidad_dia.get(horario_id, True)
    
    def calcular_horas_semanales_materia(self, materia):
        """Calcular horas semanales necesarias para una materia"""
        horas_totales = materia.get_horas_totales()
        return max(horas_totales if horas_totales > 0 else 3, 1)
    
    def obtener_estadisticas(self):
        """Obtener estadísticas de la generación"""
        if not self.horarios_generados:
            return {
                'total_horarios': 0,
                'profesores_utilizados': 0,
                'materias_asignadas': 0,
                'materias_totales': len(self.materias),
                'profesores_totales': len(self.profesores),
                'eficiencia': 0.0
            }

        total_horarios = len(self.horarios_generados)
        profesores_utilizados = len(set(h.profesor_id for h in self.horarios_generados))
        materias_asignadas = len(set(h.materia_id for h in self.horarios_generados))
        eficiencia = (materias_asignadas / len(self.materias)) * 100 if self.materias else 0

        return {
            'total_horarios': total_horarios,
            'profesores_utilizados': profesores_utilizados,
            'materias_asignadas': materias_asignadas,
            'materias_totales': len(self.materias),
            'profesores_totales': len(self.profesores),
            'eficiencia': round(eficiencia, 2)
        }


def generar_horarios_automaticos(grupo_id=None, dias_semana=None,
                                periodo_academico='2025-1', version_nombre=None, creado_por=None,
                                # Parámetros legacy (mantener compatibilidad)
                                carrera_id=None, cuatrimestre=None, turno='matutino'):
    """
    Función principal para generar horarios académicos automáticamente
    
    NUEVO ENFOQUE (recomendado):
        - grupo_id: ID del grupo que ya tiene materias, profesores y turno asignados
        
    ENFOQUE LEGACY (mantener compatibilidad):
        - carrera_id, cuatrimestre, turno: Se usará si no se proporciona grupo_id
    
    Usa OR-Tools si está disponible, sino usa algoritmo de respaldo

    Returns:
        dict: Resultado de la generación con estadísticas
    """
    try:
        # Validar que se proporcione grupo_id o los parámetros legacy
        if grupo_id is None and (carrera_id is None or cuatrimestre is None):
            return {
                'exito': False,
                'mensaje': '❌ Debe proporcionar grupo_id o carrera_id/cuatrimestre',
                'estadisticas': None,
                'horarios_generados': [],
                'algoritmo': None
            }
        
        # Si se proporciona grupo_id, extraer los datos del grupo
        if grupo_id is not None:
            from models import Grupo
            
            grupo = Grupo.query.get(grupo_id)
            if not grupo:
                return {
                    'exito': False,
                    'mensaje': f'❌ No se encontró el grupo con ID {grupo_id}',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Validar que el grupo tenga materias asignadas
            if not grupo.materias:
                return {
                    'exito': False,
                    'mensaje': f'❌ El grupo {grupo.codigo} no tiene materias asignadas. Debe asignar materias al grupo primero.',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Validar que las materias tengan profesores asignados
            materias_sin_profesor = grupo.get_materias_sin_profesor()
            if materias_sin_profesor:
                lista_materias = ', '.join([m.nombre for m in materias_sin_profesor])
                return {
                    'exito': False,
                    'mensaje': f'❌ Hay materias sin profesor asignado: {lista_materias}. Debe asignar profesores a todas las materias del grupo.',
                    'estadisticas': None,
                    'horarios_generados': [],
                    'algoritmo': None
                }
            
            # Extraer datos del grupo
            carrera_id = grupo.carrera_id
            cuatrimestre = grupo.cuatrimestre
            turno = 'matutino' if grupo.turno == 'M' else 'vespertino'
        
        if ORTOOLS_AVAILABLE:
            # Usar OR-Tools si está disponible
            generador = GeneradorHorariosOR(
                carrera_id=carrera_id,
                cuatrimestre=cuatrimestre,
                turno=turno,
                dias_semana=dias_semana,
                periodo_academico=periodo_academico,
                version_nombre=version_nombre,
                creado_por=creado_por,
                grupo_id=grupo_id  # Nuevo parámetro
            )
            return generador.generar_horarios()
        else:
            # Usar algoritmo de respaldo
            generador = GeneradorHorariosSinOR(
                carrera_id=carrera_id,
                cuatrimestre=cuatrimestre,
                turno=turno,
                dias_semana=dias_semana,
                periodo_academico=periodo_academico,
                version_nombre=version_nombre,
                creado_por=creado_por,
                grupo_id=grupo_id  # Nuevo parámetro
            )
            return generador.generar_horarios()

    except Exception as e:
        import traceback
        error_detalle = traceback.format_exc()
        print(f"ERROR en generar_horarios_automaticos: {error_detalle}")
        return {
            'exito': False,
            'mensaje': f'❌ Error crítico: {str(e)}',
            'estadisticas': None,
            'horarios_generados': [],
            'algoritmo': 'OR-Tools CP-SAT Solver' if ORTOOLS_AVAILABLE else 'Algoritmo de Respaldo'
        }