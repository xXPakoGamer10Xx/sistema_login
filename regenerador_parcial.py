"""
REGENERADOR PARCIAL DE HORARIOS

Este módulo maneja la regeneración parcial de horarios cuando un profesor
cambia su disponibilidad. Solo regenera los horarios afectados, no todos.

Funcionalidades:
1. Detectar qué horarios se ven afectados por un cambio de disponibilidad
2. Crear backups antes de regenerar
3. Regenerar solo las materias afectadas
4. Restaurar desde backups anteriores
"""

import json
import logging
from datetime import datetime
from flask_login import current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegeneradorParcial:
    """
    Detecta y regenera solo los horarios afectados por un cambio de disponibilidad.
    
    Flujo:
    1. Recibir profesor_id y slots de disponibilidad que cambiaron
    2. Buscar HorarioAcademico donde:
       - profesor_id == profesor afectado
       - dia_semana+horario_id coinciden con slots que ya NO están disponibles
    3. Obtener los grupos afectados de esos horarios
    4. Crear backup de horarios afectados
    5. Para cada grupo afectado:
       - Eliminar SOLO los horarios de las materias que imparte ese profesor
       - Regenerar usando GeneradorHorariosMejorado solo para esas materias
    """
    
    def __init__(self, profesor_id, db_session=None):
        """
        Inicializar el regenerador.
        
        Args:
            profesor_id: ID del profesor que cambió su disponibilidad
            db_session: Sesión de base de datos (opcional, usa db.session por defecto)
        """
        self.profesor_id = profesor_id
        self.db = db_session
        self.horarios_afectados = []
        self.grupos_afectados = set()
        self.materias_afectadas = set()
        
    def _get_db(self):
        """Obtener sesión de base de datos"""
        if self.db:
            return self.db
        from models import db
        return db.session
    
    def detectar_horarios_afectados(self, cambios_disponibilidad=None):
        """
        Detecta qué horarios académicos se ven afectados por cambios de disponibilidad.
        
        Args:
            cambios_disponibilidad: Lista de cambios en formato:
                [{'dia_semana': str, 'horario_id': int, 'disponible_antes': bool, 'disponible_ahora': bool}]
                Si es None, busca cambios no procesados en HistorialCambioDisponibilidad
        
        Returns:
            Lista de HorarioAcademico afectados (donde el profesor ya no está disponible)
        """
        from models import HorarioAcademico, HistorialCambioDisponibilidad, DisponibilidadProfesor
        
        # Si no se proporcionan cambios, buscar en historial no procesado
        if cambios_disponibilidad is None:
            cambios_db = HistorialCambioDisponibilidad.query.filter_by(
                profesor_id=self.profesor_id,
                procesado=False
            ).all()
            
            cambios_disponibilidad = []
            for cambio in cambios_db:
                # Solo nos interesan los slots que pasaron de disponible a no disponible
                if cambio.disponibilidad_anterior and not cambio.disponibilidad_nueva:
                    cambios_disponibilidad.append({
                        'dia_semana': cambio.dia_semana,
                        'horario_id': cambio.horario_id,
                        'disponible_antes': cambio.disponibilidad_anterior,
                        'disponible_ahora': cambio.disponibilidad_nueva
                    })
        
        # Buscar horarios académicos en conflicto
        self.horarios_afectados = []
        
        for cambio in cambios_disponibilidad:
            # Solo procesar slots que pasaron de disponible a no disponible
            if not cambio.get('disponible_ahora', True):
                horarios = HorarioAcademico.query.filter(
                    HorarioAcademico.profesor_id == self.profesor_id,
                    HorarioAcademico.dia_semana == cambio['dia_semana'],
                    HorarioAcademico.horario_id == cambio['horario_id'],
                    HorarioAcademico.activo == True
                ).all()
                
                self.horarios_afectados.extend(horarios)
        
        # Extraer grupos y materias afectadas
        for horario in self.horarios_afectados:
            self.grupos_afectados.add(horario.grupo)
            self.materias_afectadas.add(horario.materia_id)
        
        return self.horarios_afectados
    
    def detectar_grupos_afectados(self):
        """
        Obtiene la lista de grupos que tienen horarios afectados.
        
        Returns:
            Set de códigos de grupos afectados
        """
        if not self.horarios_afectados:
            self.detectar_horarios_afectados()
        
        return self.grupos_afectados
    
    def get_resumen_conflictos(self):
        """
        Genera un resumen de los conflictos detectados para mostrar al usuario.
        
        Returns:
            Dict con información estructurada de los conflictos
        """
        from models import User, Grupo
        
        if not self.horarios_afectados:
            self.detectar_horarios_afectados()
        
        profesor = User.query.get(self.profesor_id)
        
        # Agrupar por slot (dia + hora)
        conflictos_por_slot = {}
        for horario in self.horarios_afectados:
            slot_key = f"{horario.dia_semana}_{horario.horario_id}"
            if slot_key not in conflictos_por_slot:
                conflictos_por_slot[slot_key] = {
                    'dia_semana': horario.get_dia_display(),
                    'hora': f"{horario.get_hora_inicio_str()}-{horario.get_hora_fin_str()}",
                    'horarios': []
                }
            conflictos_por_slot[slot_key]['horarios'].append({
                'id': horario.id,
                'materia': horario.get_materia_nombre(),
                'materia_codigo': horario.get_materia_codigo(),
                'grupo': horario.grupo
            })
        
        return {
            'profesor_id': self.profesor_id,
            'profesor_nombre': profesor.get_nombre_completo() if profesor else 'N/A',
            'total_horarios_afectados': len(self.horarios_afectados),
            'total_grupos_afectados': len(self.grupos_afectados),
            'grupos_lista': list(self.grupos_afectados),
            'conflictos_por_slot': list(conflictos_por_slot.values())
        }
    
    def crear_backup_horarios(self, nombre=None, descripcion=None, creado_por=None):
        """
        Crea una copia de seguridad de los horarios antes de eliminarlos.
        
        Args:
            nombre: Nombre personalizado para el backup
            descripcion: Descripción del motivo del backup
            creado_por: ID del usuario que crea el backup
        
        Returns:
            ID de la versión creada para poder revertir
        """
        from models import VersionHorario, db, HorarioAcademico
        
        if not self.horarios_afectados:
            self.detectar_horarios_afectados()
        
        if not self.horarios_afectados:
            return None  # No hay nada que respaldar
        
        # Serializar datos de horarios
        datos = []
        for h in self.horarios_afectados:
            datos.append({
                'profesor_id': h.profesor_id,
                'materia_id': h.materia_id,
                'horario_id': h.horario_id,
                'dia_semana': h.dia_semana,
                'grupo': h.grupo,
                'periodo_academico': h.periodo_academico,
                'version_nombre': h.version_nombre,
                'activo': h.activo
            })
        
        # Determinar carrera (usar la del primer horario si está disponible)
        carrera_id = None
        if self.horarios_afectados and self.horarios_afectados[0].materia:
            carrera_id = self.horarios_afectados[0].materia.carrera_id
        
        # Crear backup
        nombre_version = nombre or f"Backup pre-regeneración {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        version = VersionHorario(
            nombre_version=nombre_version,
            descripcion=descripcion or f"Backup automático antes de regenerar horarios del profesor ID {self.profesor_id}",
            datos_horarios=json.dumps(datos, ensure_ascii=False),
            total_horarios=len(datos),
            grupos_afectados=','.join(self.grupos_afectados),
            profesor_origen_id=self.profesor_id,
            carrera_id=carrera_id,
            creado_por=creado_por
        )
        
        db.session.add(version)
        db.session.commit()
        
        logger.info(f"Backup creado: {version.id} con {len(datos)} horarios")
        return version.id
    
    def regenerar_parcial(self, version_nombre=None, dias_semana=None, creado_por=None):
        """
        Regenera solo las materias afectadas del profesor en los grupos afectados.
        
        Args:
            version_nombre: Nombre para la nueva versión de horarios
            dias_semana: Lista de días válidos (por defecto lunes-viernes)
            creado_por: ID del usuario que realiza la regeneración
        
        Returns:
            Dict con resultado:
            {
                'exito': bool,
                'backup_id': int or None,
                'horarios_eliminados': int,
                'horarios_regenerados': int,
                'grupos_procesados': list,
                'errores': list
            }
        """
        from models import db, HorarioAcademico, Grupo
        from generador_horarios_mejorado import GeneradorHorariosMejorado
        
        resultado = {
            'exito': True,
            'backup_id': None,
            'horarios_eliminados': 0,
            'horarios_regenerados': 0,
            'grupos_procesados': [],
            'errores': []
        }
        
        try:
            # 1. Detectar horarios afectados
            if not self.horarios_afectados:
                self.detectar_horarios_afectados()
            
            if not self.horarios_afectados:
                resultado['mensaje'] = 'No se encontraron horarios afectados'
                return resultado
            
            # 2. Crear backup
            resultado['backup_id'] = self.crear_backup_horarios(
                descripcion=f"Regeneración parcial por cambio de disponibilidad",
                creado_por=creado_por
            )
            
            # 3. Eliminar horarios afectados
            horarios_ids = [h.id for h in self.horarios_afectados]
            HorarioAcademico.query.filter(HorarioAcademico.id.in_(horarios_ids)).update(
                {'activo': False}, synchronize_session=False
            )
            db.session.commit()
            resultado['horarios_eliminados'] = len(horarios_ids)
            
            # 4. Obtener grupos para regenerar
            grupos_codigos = list(self.grupos_afectados)
            grupos = Grupo.query.filter(Grupo.codigo.in_(grupos_codigos), Grupo.activo == True).all()
            grupos_ids = [g.id for g in grupos]
            
            if not grupos_ids:
                resultado['mensaje'] = 'No se encontraron grupos activos para regenerar'
                return resultado
            
            # 5. Regenerar para cada grupo
            dias = dias_semana or ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
            periodo = f"{datetime.now().year}-regeneracion-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            for grupo_id in grupos_ids:
                grupo = Grupo.query.get(grupo_id)
                try:
                    db.session.expire_all()
                    
                    generador = GeneradorHorariosMejorado(
                        grupos_ids=[grupo_id],
                        periodo_academico=periodo,
                        version_nombre=version_nombre or f"Regeneración parcial - {grupo.codigo}",
                        creado_por=creado_por,
                        dias_semana=dias,
                        tiempo_limite=30
                    )
                    
                    res = generador.generar()
                    
                    if res['exito']:
                        db.session.commit()
                        resultado['horarios_regenerados'] += res.get('horarios_generados', 0)
                        resultado['grupos_procesados'].append(grupo.codigo)
                    else:
                        resultado['errores'].append(f"Error en grupo {grupo.codigo}: {res.get('mensaje', 'Error desconocido')}")
                        
                except Exception as e:
                    db.session.rollback()
                    resultado['errores'].append(f"Excepción en grupo {grupo.codigo}: {str(e)}")
                    logger.error(f"Error regenerando grupo {grupo.codigo}: {e}")
            
            # 6. Marcar cambios como procesados
            from models import HistorialCambioDisponibilidad
            HistorialCambioDisponibilidad.query.filter_by(
                profesor_id=self.profesor_id,
                procesado=False
            ).update({'procesado': True}, synchronize_session=False)
            db.session.commit()
            
            resultado['exito'] = len(resultado['errores']) == 0
            resultado['mensaje'] = f"Regeneración {'exitosa' if resultado['exito'] else 'parcial'}: {resultado['horarios_regenerados']} horarios generados"
            
        except Exception as e:
            resultado['exito'] = False
            resultado['errores'].append(f"Error general: {str(e)}")
            logger.error(f"Error en regeneración parcial: {e}")
        
        return resultado


def restaurar_version(version_id, creado_por=None):
    """
    Restaura horarios desde una versión guardada.
    
    Args:
        version_id: ID de la versión a restaurar
        creado_por: ID del usuario que restaura
    
    Returns:
        Dict con resultado de la restauración
    """
    from models import VersionHorario, HorarioAcademico, db
    
    resultado = {
        'exito': False,
        'horarios_restaurados': 0,
        'mensaje': ''
    }
    
    try:
        version = VersionHorario.query.get(version_id)
        if not version:
            resultado['mensaje'] = 'Versión no encontrada'
            return resultado
        
        # Parsear datos
        datos = version.get_horarios_data()
        if not datos:
            resultado['mensaje'] = 'No hay datos para restaurar'
            return resultado
        
        # Primero, desactivar horarios actuales de los grupos afectados
        grupos = version.get_grupos_lista()
        if grupos:
            HorarioAcademico.query.filter(
                HorarioAcademico.grupo.in_(grupos),
                HorarioAcademico.activo == True
            ).update({'activo': False}, synchronize_session=False)
        
        # Recrear horarios desde el backup
        for dato in datos:
            nuevo_horario = HorarioAcademico(
                profesor_id=dato['profesor_id'],
                materia_id=dato['materia_id'],
                horario_id=dato['horario_id'],
                dia_semana=dato['dia_semana'],
                grupo=dato['grupo'],
                periodo_academico=dato.get('periodo_academico'),
                version_nombre=f"Restaurado desde: {version.nombre_version}",
                creado_por=creado_por
            )
            db.session.add(nuevo_horario)
            resultado['horarios_restaurados'] += 1
        
        # Marcar versión como restaurada
        version.restaurado = True
        version.fecha_restauracion = datetime.utcnow()
        
        db.session.commit()
        
        resultado['exito'] = True
        resultado['mensaje'] = f'Se restauraron {resultado["horarios_restaurados"]} horarios correctamente'
        
    except Exception as e:
        db.session.rollback()
        resultado['mensaje'] = f'Error al restaurar: {str(e)}'
        logger.error(f"Error restaurando versión {version_id}: {e}")
    
    return resultado


def detectar_conflictos_disponibilidad(profesor_id):
    """
    Función de conveniencia para detectar conflictos sin instanciar la clase.
    
    Args:
        profesor_id: ID del profesor
    
    Returns:
        Dict con resumen de conflictos
    """
    regenerador = RegeneradorParcial(profesor_id)
    regenerador.detectar_horarios_afectados()
    return regenerador.get_resumen_conflictos()
