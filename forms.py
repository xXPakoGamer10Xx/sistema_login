from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, SubmitField, IntegerField, TimeField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
from models import User, Horario, Carrera, Materia
import re

def validate_not_zero(form, field):
    """Validador personalizado para asegurar que el valor no sea 0"""
    if field.data == 0:
        raise ValidationError('Debe seleccionar una opción válida')

def clean_phone_number(phone):
    """Limpia el número de teléfono eliminando caracteres no numéricos"""
    if phone:
        return re.sub(r'\D', '', phone)
    return phone

class LoginForm(FlaskForm):
    """Formulario de inicio de sesión"""
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    """Formulario de registro de usuario"""
    username = StringField('Usuario', validators=[
        DataRequired(), 
        Length(min=4, max=20, message='El usuario debe tener entre 4 y 20 caracteres')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message='Ingrese un email válido')
    ])
    
    nombre = StringField('Nombre', validators=[
        DataRequired(), 
        Length(min=2, max=50, message='El nombre debe tener entre 2 y 50 caracteres')
    ])
    
    apellido = StringField('Apellido', validators=[
        DataRequired(), 
        Length(min=2, max=50, message='El apellido debe tener entre 2 y 50 caracteres')
    ])
    
    telefono = StringField('Teléfono', validators=[
        Length(min=10, max=10, message='El teléfono debe tener exactamente 10 dígitos')
    ])
    
    password = PasswordField('Contraseña', validators=[
        DataRequired(), 
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    
    password2 = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(), 
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    
    rol = SelectField('Rol', choices=[
        ('', 'Seleccione un rol'),
        ('admin', 'Administrador'),
        ('jefe_carrera', 'Jefe de Carrera'),
        ('profesor', 'Profesor')
    ], validators=[DataRequired(message='Debe seleccionar un rol')])
    
    tipo_profesor = SelectField('Tipo de Profesor', choices=[
        ('', 'Seleccione tipo de profesor'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ])
    
    carrera = SelectMultipleField('Carrera', validators=[Optional()])
    
    otra_carrera = BooleanField('¿Estás inscrito en otra carrera además de la que seleccionaste?', validators=[Optional()])
    
    submit = SubmitField('Registrarse')
    
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera.choices = [('', 'Seleccione una carrera')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]
    
    def validate_telefono(self, telefono):
        """Limpiar teléfono de caracteres no numéricos"""
        if telefono.data:
            telefono.data = clean_phone_number(telefono.data)
            if len(telefono.data) != 10:
                raise ValidationError('El teléfono debe tener exactamente 10 dígitos')
    
    def validate_username(self, username):
        """Validar que el usuario no exista"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nombre de usuario ya está en uso. Elija uno diferente.')
    
    def validate_email(self, email):
        """Validar que el email no exista"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email ya está registrado. Elija uno diferente.')
    
    def validate_tipo_profesor(self, tipo_profesor):
        """Validar tipo de profesor si se seleccionó profesor como rol"""
        if self.rol.data == 'profesor' and not tipo_profesor.data:
            raise ValidationError('Debe seleccionar el tipo de profesor.')
    
    def validate_carrera(self, carrera):
        """Validar carrera si se seleccionó profesor o jefe de carrera como rol"""
        if self.rol.data in ['profesor', 'jefe_carrera'] and (not carrera.data or len(carrera.data) == 0):
            if self.rol.data == 'profesor':
                raise ValidationError('Los profesores deben seleccionar al menos una carrera.')
            elif self.rol.data == 'jefe_carrera':
                raise ValidationError('Los jefes de carrera deben seleccionar al menos una carrera.')
        
        # Nota: Ahora permitimos que múltiples jefes puedan estar en la misma carrera
        # y un jefe puede estar en múltiples carreras
    
    def get_final_rol(self):
        """Obtener el rol final basado en la selección"""
        if self.rol.data == 'profesor':
            return self.tipo_profesor.data
        return self.rol.data

class HorarioForm(FlaskForm):
    """Formulario para crear/editar horarios"""
    nombre = StringField('Nombre del Período', validators=[
        DataRequired(message='El nombre es obligatorio'),
        Length(min=2, max=100, message='El nombre debe tener entre 2 y 100 caracteres')
    ])
    
    turno = SelectField('Turno', choices=[
        ('', 'Seleccione un turno'),
        ('matutino', 'Matutino'),
        ('vespertino', 'Vespertino')
    ], validators=[DataRequired(message='Debe seleccionar un turno')])
    
    hora_inicio = TimeField('Hora de Inicio', validators=[
        DataRequired(message='La hora de inicio es obligatoria')
    ])
    
    hora_fin = TimeField('Hora de Fin', validators=[
        DataRequired(message='La hora de fin es obligatoria')
    ])
    
    orden = IntegerField('Orden', validators=[
        DataRequired(message='El orden es obligatorio'),
        NumberRange(min=1, max=20, message='El orden debe estar entre 1 y 20')
    ])
    
    submit = SubmitField('Guardar Horario')
    
    def validate_hora_fin(self, hora_fin):
        """Validar que la hora de fin sea posterior a la de inicio"""
        if self.hora_inicio.data and hora_fin.data:
            if hora_fin.data <= self.hora_inicio.data:
                raise ValidationError('La hora de fin debe ser posterior a la hora de inicio.')
    
    def validate_orden(self, orden):
        """Validar que el orden no esté duplicado en el mismo turno"""
        if self.turno.data and orden.data:
            # En caso de edición, excluir el horario actual de la validación
            query = Horario.query.filter_by(turno=self.turno.data, orden=orden.data, activo=True)
            
            # Si estamos editando, excluir el horario actual
            if hasattr(self, '_horario_id') and self._horario_id:
                query = query.filter(Horario.id != self._horario_id)
            
            if query.first():
                raise ValidationError(f'Ya existe un período con orden {orden.data} en el turno {self.turno.data}.')

class EliminarHorarioForm(FlaskForm):
    """Formulario para confirmar eliminación de horario"""
    submit = SubmitField('Confirmar Eliminación')

class CarreraForm(FlaskForm):
    """Formulario para crear/editar carreras"""
    nombre = StringField('Nombre de la Carrera', validators=[
        DataRequired(message='El nombre es obligatorio'),
        Length(min=5, max=150, message='El nombre debe tener entre 5 y 150 caracteres')
    ])
    
    codigo = StringField('Código', validators=[
        DataRequired(message='El código es obligatorio'),
        Length(min=2, max=10, message='El código debe tener entre 2 y 10 caracteres')
    ])
    
    descripcion = TextAreaField('Descripción', validators=[
        Optional(),
        Length(max=500, message='La descripción no puede exceder 500 caracteres')
    ])
    
    facultad = StringField('Facultad', validators=[
        Optional(),
        Length(max=100, message='La facultad no puede exceder 100 caracteres')
    ])
    
    jefe_carrera_id = SelectField('Jefe de Carrera', 
                                 choices=[(0, 'Sin asignar')],
                                 validators=[Optional()],
                                 coerce=int)
    
    submit = SubmitField('Guardar Carrera')
    
    def __init__(self, *args, **kwargs):
        super(CarreraForm, self).__init__(*args, **kwargs)
        try:
            # Cargar SOLO usuarios que son jefes de carrera
            jefes_disponibles = User.query.filter(
                User.rol == 'jefe_carrera',
                User.activo == True
            ).order_by(User.nombre, User.apellido).all()
            
            self.jefe_carrera_id.choices = [(0, 'Sin asignar')] + [
                (user.id, f"{user.nombre} {user.apellido} - {user.email}")
                for user in jefes_disponibles
            ]
        except Exception as e:
            print(f"Error cargando opciones de jefe de carrera: {e}")
            self.jefe_carrera_id.choices = [(0, 'Sin asignar')]
    
    def validate_codigo(self, codigo):
        """Validar que el código no esté duplicado"""
        # En caso de edición, excluir la carrera actual de la validación
        query = Carrera.query.filter_by(codigo=codigo.data.upper(), activa=True)
        
        if hasattr(self, '_carrera_id') and self._carrera_id:
            query = query.filter(Carrera.id != self._carrera_id)
        
        if query.first():
            raise ValidationError(f'Ya existe una carrera con código {codigo.data.upper()}.')
    
    def validate_nombre(self, nombre):
        """Validar que el nombre no esté duplicado"""
        query = Carrera.query.filter_by(nombre=nombre.data, activa=True)
        
        if hasattr(self, '_carrera_id') and self._carrera_id:
            query = query.filter(Carrera.id != self._carrera_id)
        
        if query.first():
            raise ValidationError('Ya existe una carrera con este nombre.')

class ImportarCarrerasForm(FlaskForm):
    """Formulario para importar carreras desde archivo CSV"""
    archivo = FileField('Archivo CSV', validators=[
        DataRequired(message='Debe seleccionar un archivo'),
        FileAllowed(['csv'], 'Solo se permiten archivos CSV')
    ])
    
    submit = SubmitField('Importar Carreras')

class ImportarAsignacionesGrupoForm(FlaskForm):
    """Formulario para importar asignaciones masivas de materias a grupos desde CSV"""
    archivo = FileField('Archivo CSV', validators=[
        DataRequired(message='Debe seleccionar un archivo'),
        FileAllowed(['csv'], 'Solo se permiten archivos CSV')
    ])
    
    submit = SubmitField('Importar Asignaciones')

class ImportarAsignacionesForm(FlaskForm):
    """Formulario para importar asignaciones de materias desde archivo CSV"""
    archivo = FileField('Archivo CSV', validators=[
        DataRequired(message='Debe seleccionar un archivo'),
        FileAllowed(['csv'], 'Solo se permiten archivos CSV')
    ])
    
    submit = SubmitField('Importar Asignaciones')

class ImportarProfesoresForm(FlaskForm):
    """Formulario para importar profesores desde archivo CSV/Excel"""
    archivo = FileField('Archivo CSV/Excel', validators=[
        DataRequired(message='Debe seleccionar un archivo'),
        FileAllowed(['csv', 'xlsx', 'xls'], 'Solo se permiten archivos CSV o Excel')
    ])
    
    carrera_defecto = SelectField('Carrera por Defecto', validators=[
        Optional()
    ])
    
    submit = SubmitField('Importar Profesores')
    
    def __init__(self, *args, **kwargs):
        super(ImportarProfesoresForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera_defecto.choices = [('', 'Sin carrera por defecto')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]

class FiltrarProfesoresForm(FlaskForm):
    """Formulario para filtrar profesores"""
    carrera = SelectField('Filtrar por Carrera', validators=[Optional()])
    tipo_profesor = SelectField('Tipo de Profesor', choices=[
        ('', 'Todos los tipos'),
        ('profesor_completo', 'Tiempo Completo'),
        ('profesor_asignatura', 'Por Asignatura')
    ], validators=[Optional()])
    
    submit = SubmitField('Filtrar')
    
    def __init__(self, *args, **kwargs):
        super(FiltrarProfesoresForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera.choices = [('', 'Todas las carreras')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]

class ExportarProfesoresForm(FlaskForm):
    """Formulario para exportar profesores a PDF"""
    carrera = SelectField('Carrera a Exportar', validators=[Optional()])
    incluir_contacto = SelectField('Incluir Información de Contacto', choices=[
        ('si', 'Sí'),
        ('no', 'No')
    ], default='si')
    
    submit = SubmitField('Exportar a PDF')
    
    def __init__(self, *args, **kwargs):
        super(ExportarProfesoresForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera.choices = [('', 'Todas las carreras')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]

class EliminarCarreraForm(FlaskForm):
    """Formulario para confirmar eliminación de carrera"""
    submit = SubmitField('Confirmar Eliminación')

class MateriaForm(FlaskForm):
    """Formulario para crear/editar materias"""
    nombre = StringField('Nombre de la Materia', validators=[
        DataRequired(message='El nombre es obligatorio'),
        Length(min=3, max=200, message='El nombre debe tener entre 3 y 200 caracteres')
    ])
    
    codigo = StringField('Código', validators=[
        DataRequired(message='El código es obligatorio'),
        Length(min=3, max=20, message='El código debe tener entre 3 y 20 caracteres')
    ])
    
    descripcion = TextAreaField('Descripción', validators=[
        Optional(),
        Length(max=500, message='La descripción no puede exceder 500 caracteres')
    ])
    
    cuatrimestre = IntegerField('Cuatrimestre', validators=[
        DataRequired(message='El cuatrimestre es obligatorio'),
        NumberRange(min=0, max=10, message='El cuatrimestre debe estar entre 0 y 10')
    ])
    
    creditos = IntegerField('Créditos', validators=[
        DataRequired(message='Los créditos son obligatorios'),
        NumberRange(min=1, max=10, message='Los créditos deben estar entre 1 y 10')
    ], default=3)
    
    horas_semanales = IntegerField('Horas Semanales', validators=[
        DataRequired(message='Las horas semanales son obligatorias'),
        NumberRange(min=1, max=50, message='Las horas semanales deben estar entre 1 y 50')
    ], default=5)
    
    carrera = SelectField('Carrera', validators=[DataRequired(message='Debe seleccionar una carrera')])
    
    submit = SubmitField('Guardar Materia')
    
    def __init__(self, *args, **kwargs):
        super(MateriaForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera.choices = [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]
    
    def validate_codigo(self, codigo):
        """Validar que el código no esté duplicado"""
        # En caso de edición, excluir la materia actual de la validación
        query = Materia.query.filter_by(codigo=codigo.data.upper(), activa=True)
        
        if hasattr(self, '_materia_id') and self._materia_id:
            query = query.filter(Materia.id != self._materia_id)
        
        if query.first():
            raise ValidationError(f'Ya existe una materia con código {codigo.data.upper()}.')

class ImportarMateriasForm(FlaskForm):
    """Formulario para importar materias desde archivo CSV/Excel"""
    archivo = FileField('Archivo CSV/Excel', validators=[
        DataRequired(message='Debe seleccionar un archivo'),
        FileAllowed(['csv', 'xlsx', 'xls'], 'Solo se permiten archivos CSV o Excel')
    ])
    
    carrera_defecto = SelectField('Carrera por Defecto', validators=[
        Optional()
    ])
    
    restar_horas = IntegerField('Restar Horas a cada Materia', validators=[
        Optional(),
        NumberRange(min=0, max=20, message='Las horas a restar deben estar entre 0 y 20')
    ], default=0)
    
    submit = SubmitField('Importar Materias')
    
    def __init__(self, *args, **kwargs):
        super(ImportarMateriasForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera_defecto.choices = [('', 'Sin carrera por defecto')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]

class FiltrarMateriasForm(FlaskForm):
    """Formulario para filtrar materias"""
    carrera = SelectField('Filtrar por Carrera', validators=[Optional()])
    ciclo = SelectField('Filtrar por Ciclo Escolar', choices=[
        ('', 'Todos los ciclos'),
        ('1', 'Ciclo 1 (Cuatrimestres 1, 4, 7, 10)'),
        ('2', 'Ciclo 2 (Cuatrimestres 2, 5, 8)'),
        ('3', 'Ciclo 3 (Cuatrimestres 0, 3, 6, 9)')
    ], validators=[Optional()])
    cuatrimestre = SelectField('Filtrar por Cuatrimestre', choices=[
        ('', 'Todos los cuatrimestres'),
        ('0', 'Cuatrimestre 0'),
        ('1', 'Cuatrimestre 1'),
        ('2', 'Cuatrimestre 2'),
        ('3', 'Cuatrimestre 3'),
        ('4', 'Cuatrimestre 4'),
        ('5', 'Cuatrimestre 5'),
        ('6', 'Cuatrimestre 6'),
        ('7', 'Cuatrimestre 7'),
        ('8', 'Cuatrimestre 8'),
        ('9', 'Cuatrimestre 9'),
        ('10', 'Cuatrimestre 10')
    ], validators=[Optional()])
    
    submit = SubmitField('Filtrar')
    
    def __init__(self, *args, **kwargs):
        super(FiltrarMateriasForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        self.carrera.choices = [('', 'Todas las carreras')] + [
            (str(c.id), f"{c.codigo} - {c.nombre}") 
            for c in Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        ]

class ExportarMateriasForm(FlaskForm):
    """Formulario para exportar materias a PDF"""
    carrera = SelectField('Carrera a Exportar', validators=[Optional()])
    cuatrimestre = SelectField('Cuatrimestre a Exportar', choices=[
        ('', 'Todos los cuatrimestres'),
        ('0', 'Cuatrimestre 0'),
        ('1', 'Cuatrimestre 1'),
        ('2', 'Cuatrimestre 2'),
        ('3', 'Cuatrimestre 3'),
        ('4', 'Cuatrimestre 4'),
        ('5', 'Cuatrimestre 5'),
        ('6', 'Cuatrimestre 6'),
        ('7', 'Cuatrimestre 7'),
        ('8', 'Cuatrimestre 8'),
        ('9', 'Cuatrimestre 9'),
        ('10', 'Cuatrimestre 10')
    ], validators=[Optional()])
    
    submit = SubmitField('Exportar a PDF')

class GenerarHorariosForm(FlaskForm):
    """Formulario para generar horarios académicos"""
    version_nombre = StringField('Nombre de esta versión (opcional)', validators=[
        Optional(),
        Length(max=100, message='El nombre no puede exceder 100 caracteres')
    ], description='Ej: "Versión Final", "Borrador 1", "Prueba Matutino". Si no se especifica, se genera automáticamente.')
    """Formulario para generar horarios académicos automáticamente"""
    
    # Ahora solo se necesita seleccionar el grupo
    # El grupo ya contiene: carrera, cuatrimestre, turno, materias y profesores asignados
    grupo_id = SelectField('Grupo', coerce=int, choices=[], validators=[
        DataRequired(message='Debe seleccionar un grupo'),
        validate_not_zero
    ])
    
    dias_semana = SelectField('Días de la semana', choices=[
        ('lunes_viernes', 'Lunes a Viernes'),
        ('lunes_sabado', 'Lunes a Sábado'),
        ('personalizado', 'Personalizado')
    ], default='lunes_viernes', validators=[DataRequired()])
    
    # Campos para selección personalizada de días
    lunes = SelectField('Lunes', choices=[('si', 'Sí'), ('no', 'No')], default='si')
    martes = SelectField('Martes', choices=[('si', 'Sí'), ('no', 'No')], default='si')
    miercoles = SelectField('Miércoles', choices=[('si', 'Sí'), ('no', 'No')], default='si')
    jueves = SelectField('Jueves', choices=[('si', 'Sí'), ('no', 'No')], default='si')
    viernes = SelectField('Viernes', choices=[('si', 'Sí'), ('no', 'No')], default='si')
    sabado = SelectField('Sábado', choices=[('si', 'Sí'), ('no', 'No')], default='no')
    
    submit = SubmitField('Generar Horarios')

class EditarHorarioAcademicoForm(FlaskForm):
    """Formulario para editar un horario académico"""
    
    profesor_id = SelectField('Profesor', choices=[], validators=[DataRequired()])
    horario_id = SelectField('Horario', choices=[], validators=[DataRequired()])
    dia_semana = SelectField('Día', choices=[
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado')
    ], validators=[DataRequired()])
    
    grupo = StringField('Grupo', validators=[DataRequired(), Length(max=10)])
    
    submit = SubmitField('Guardar Cambios')

class EliminarHorarioAcademicoForm(FlaskForm):
    """Formulario para confirmar eliminación de horario académico"""
    
    confirmacion = StringField('Escriba "ELIMINAR" para confirmar', 
                              validators=[DataRequired(), 
                                        Length(min=8, max=8, message='Debe escribir exactamente "ELIMINAR"')])
    
    submit = SubmitField('Eliminar Horario')

class DisponibilidadProfesorForm(FlaskForm):
    """Formulario para gestionar disponibilidad de profesores"""
    
    profesor_id = SelectField('Profesor', validators=[DataRequired()], choices=[])
    dia_semana = SelectField('Día de la semana', validators=[DataRequired()], choices=[
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado')
    ])
    
    submit = SubmitField('Guardar Disponibilidad')

class EditarDisponibilidadProfesorForm(FlaskForm):
    """Formulario para editar disponibilidad de un profesor específico"""
    
    horario_id = SelectField('Horario', validators=[DataRequired()], choices=[])
    disponible = SelectField('Disponibilidad', validators=[DataRequired()], choices=[
        ('True', 'Disponible'),
        ('False', 'No disponible')
    ])
    
    submit = SubmitField('Actualizar')

class AgregarProfesorForm(FlaskForm):
    """Formulario para que administradores agreguen profesores manualmente"""
    
    username = StringField('Nombre de Usuario', validators=[
        DataRequired(message='El nombre de usuario es obligatorio'),
        Length(min=4, max=20, message='El usuario debe tener entre 4 y 20 caracteres')
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message='El email es obligatorio'),
        Email(message='Ingrese un email válido')
    ])
    
    nombre = StringField('Nombre', validators=[
        DataRequired(message='El nombre es obligatorio'),
        Length(min=2, max=50, message='El nombre debe tener entre 2 y 50 caracteres')
    ])
    
    apellido = StringField('Apellido', validators=[
        DataRequired(message='El apellido es obligatorio'),
        Length(min=2, max=50, message='El apellido debe tener entre 2 y 50 caracteres')
    ])
    
    telefono = StringField('Teléfono', validators=[
        Length(min=10, max=10, message='El teléfono debe tener exactamente 10 dígitos')
    ])

    password = PasswordField('Contraseña', validators=[
        DataRequired(message='La contraseña es obligatoria'),
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    
    password2 = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(message='La confirmación de contraseña es obligatoria'),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    
    tipo_profesor = SelectField('Tipo de Profesor', validators=[DataRequired(message='Debe seleccionar el tipo de profesor')], choices=[
        ('', 'Seleccione tipo de profesor'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ])
    
    # Ahora soporta múltiples carreras como en EditarUsuarioForm
    carreras = SelectMultipleField('Carreras', coerce=int, validators=[DataRequired(message='Debe seleccionar al menos una carrera')])
    
    submit = SubmitField('Crear Profesor')
    
    def __init__(self, *args, **kwargs):
        super(AgregarProfesorForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras (ahora múltiples)
        from models import Carrera
        carreras_activas = Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        self.carreras.choices = [
            (c.id, f"{c.codigo} - {c.nombre}") 
            for c in carreras_activas
        ]
    
    def get_disponibilidades_data(self):
        """Obtener los datos de disponibilidad del formulario"""
        from flask import request
        disponibilidades = []
        
        # Procesar todos los campos que empiecen con 'disp_' desde request.form
        for field_name in request.form.keys():
            if field_name.startswith('disp_'):
                parts = field_name.split('_')
                if len(parts) >= 3:
                    horario_id = parts[1]
                    dia_semana = parts[2]
                    disponible = True  # Si está en request.form, está marcado
                    
                    disponibilidades.append({
                        'horario_id': int(horario_id),
                        'dia_semana': dia_semana,
                        'disponible': disponible
                    })
        
        return disponibilidades
    
    def validate_telefono(self, telefono):
        """Limpiar teléfono de caracteres no numéricos"""
        if telefono.data:
            telefono.data = clean_phone_number(telefono.data)
            if len(telefono.data) != 10:
                raise ValidationError('El teléfono debe tener exactamente 10 dígitos')
    
    def validate_username(self, username):
        """Validar que el usuario no exista"""
        from models import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nombre de usuario ya está en uso. Elija uno diferente.')
    
    def validate_email(self, email):
        """Validar que el email no exista"""
        from models import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email ya está registrado. Elija uno diferente.')

# Formularios para Gestión de Usuarios (solo administradores)

class AgregarUsuarioForm(FlaskForm):
    """Formulario para agregar nuevo usuario"""
    username = StringField('Usuario', validators=[
        DataRequired(),
        Length(min=4, max=20, message='El usuario debe tener entre 4 y 20 caracteres')
    ])

    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Ingrese un email válido')
    ])

    nombre = StringField('Nombre', validators=[
        DataRequired(),
        Length(min=2, max=50, message='El nombre debe tener entre 2 y 50 caracteres')
    ])

    apellido = StringField('Apellido', validators=[
        DataRequired(),
        Length(min=2, max=50, message='El apellido debe tener entre 2 y 50 caracteres')
    ])

    telefono = StringField('Teléfono', validators=[
        Optional(),
        Length(min=10, max=10, message='El teléfono debe tener exactamente 10 dígitos')
    ])

    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])

    password2 = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])

    # Ahora roles es un campo de selección múltiple para permitir múltiples roles
    # Usamos Optional() porque los checkboxes en el HTML no se procesan igual que un select multiple
    roles_seleccionados = SelectMultipleField('Roles', choices=[
        ('admin', 'Administrador'),
        ('jefe_carrera', 'Jefe de Carrera'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    # Campo legacy para compatibilidad (se mantiene oculto o se establece automáticamente)
    rol = SelectField('Rol Principal', choices=[
        ('', 'Seleccione un rol'),
        ('admin', 'Administrador'),
        ('jefe_carrera', 'Jefe de Carrera'),
        ('profesor', 'Profesor'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    tipo_profesor = SelectField('Tipo de Profesor', choices=[
        ('', 'Seleccione tipo de profesor'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    # Ahora tanto jefes de carrera como profesores usan el mismo campo de múltiples carreras
    carreras = SelectMultipleField('Carreras', coerce=int, validators=[Optional()])

    activo = BooleanField('Usuario Activo', default=True)

    submit = SubmitField('Crear Usuario')

    def __init__(self, *args, **kwargs):
        super(AgregarUsuarioForm, self).__init__(*args, **kwargs)
        # Llenar opciones de carreras
        carreras_activas = Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        
        self.carreras.choices = [
            (c.id, f"{c.codigo} - {c.nombre}")
            for c in carreras_activas
        ]

    def validate_telefono(self, telefono):
        """Limpiar teléfono de caracteres no numéricos"""
        if telefono.data:
            telefono.data = clean_phone_number(telefono.data)
            if len(telefono.data) != 10:
                raise ValidationError('El teléfono debe tener exactamente 10 dígitos')
    
    def validate_username(self, username):
        """Validar que el usuario no exista"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nombre de usuario ya está en uso. Elija uno diferente.')

    def validate_email(self, email):
        """Validar que el email no exista"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email ya está registrado. Elija uno diferente.')

    def validate_carreras(self, carreras):
        """Validar carreras si se seleccionó un rol que requiera carrera"""
        roles = self.get_roles_list()
        requiere_carrera = any(r in roles for r in ['jefe_carrera', 'profesor_completo', 'profesor_asignatura'])
        
        if requiere_carrera and (not carreras.data or len(carreras.data) == 0):
            raise ValidationError('Los profesores y jefes de carrera deben seleccionar al menos una carrera.')
    
    def validate_roles_seleccionados(self, roles_seleccionados):
        """Validar que se haya seleccionado al menos un rol"""
        roles = self.get_roles_list()
        if not roles:
            raise ValidationError('Debe seleccionar al menos un rol.')
            
    def get_roles_list(self):
        """Obtener la lista de roles seleccionados desde request.form (checkboxes)"""
        from flask import request
        # Los checkboxes se envían como una lista con el mismo nombre
        roles = request.form.getlist('roles_seleccionados')
        return roles if roles else []
    
    def get_primary_rol(self):
        """Obtener el rol principal para el campo legacy"""
        roles = self.get_roles_list()
        # Prioridad: admin > jefe_carrera > profesor_completo > profesor_asignatura
        if 'admin' in roles:
            return 'admin'
        elif 'jefe_carrera' in roles:
            return 'jefe_carrera'
        elif 'profesor_completo' in roles:
            return 'profesor_completo'
        elif 'profesor_asignatura' in roles:
            return 'profesor_asignatura'
        return roles[0] if roles else ''
    
    def is_profesor(self):
        """Verificar si alguno de los roles seleccionados es de profesor"""
        roles = self.get_roles_list()
        return 'profesor_completo' in roles or 'profesor_asignatura' in roles
    
    def get_disponibilidades_data(self):
        """Obtener los datos de disponibilidad del formulario"""
        from flask import request
        disponibilidades = []
        
        # Procesar todos los campos que empiecen con 'disp_' desde request.form
        for field_name in request.form.keys():
            if field_name.startswith('disp_'):
                parts = field_name.split('_')
                if len(parts) >= 3:
                    horario_id = parts[1]
                    dia_semana = parts[2]
                    disponible = True  # Si está en request.form, está marcado
                    
                    disponibilidades.append({
                        'horario_id': int(horario_id),
                        'dia_semana': dia_semana,
                        'disponible': disponible
                    })
        
        return disponibilidades

class EditarUsuarioForm(FlaskForm):
    """Formulario para editar usuario existente"""
    username = StringField('Usuario', validators=[
        DataRequired(),
        Length(min=4, max=20, message='El usuario debe tener entre 4 y 20 caracteres')
    ])

    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Ingrese un email válido')
    ])

    nombre = StringField('Nombre', validators=[
        DataRequired(),
        Length(min=2, max=50, message='El nombre debe tener entre 2 y 50 caracteres')
    ])

    apellido = StringField('Apellido', validators=[
        DataRequired(),
        Length(min=2, max=50, message='El apellido debe tener entre 2 y 50 caracteres')
    ])

    telefono = StringField('Teléfono', validators=[
        Optional(),
        Length(min=10, max=10, message='El teléfono debe tener exactamente 10 dígitos')
    ])

    rol = SelectField('Rol', choices=[
        ('', 'Seleccione un rol'),
        ('admin', 'Administrador'),
        ('jefe_carrera', 'Jefe de Carrera'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    # Ahora roles es un campo de selección múltiple para permitir múltiples roles
    # Usamos Optional porque en el formulario de jefe de carrera no se incluye este campo
    roles_seleccionados = SelectMultipleField('Roles', choices=[
        ('admin', 'Administrador'),
        ('jefe_carrera', 'Jefe de Carrera'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    tipo_profesor = SelectField('Tipo de Profesor', choices=[
        ('', 'Seleccione tipo de profesor'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ], validators=[Optional()])

    # Ahora tanto jefes de carrera como profesores usan el mismo campo de múltiples carreras
    carreras = SelectMultipleField('Carreras', coerce=int, validators=[Optional()])

    activo = BooleanField('Usuario Activo')

    submit = SubmitField('Actualizar Usuario')

    def __init__(self, user=None, *args, **kwargs):
        super(EditarUsuarioForm, self).__init__(*args, **kwargs)
        self.user = user
        # Llenar opciones de carreras
        carreras_activas = Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        self.carreras.choices = [
            (c.id, f"{c.codigo} - {c.nombre}")
            for c in carreras_activas
        ]

    def validate_telefono(self, telefono):
        """Limpiar teléfono de caracteres no numéricos"""
        if telefono.data:
            telefono.data = clean_phone_number(telefono.data)
            if len(telefono.data) != 10:
                raise ValidationError('El teléfono debe tener exactamente 10 dígitos')
    
    def validate_username(self, username):
        """Validar que el usuario no exista (excepto el actual)"""
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != self.user.id:
            raise ValidationError('Este nombre de usuario ya está en uso. Elija uno diferente.')

    def validate_email(self, email):
        """Validar que el email no exista (excepto el actual)"""
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != self.user.id:
            raise ValidationError('Este email ya está registrado. Elija uno diferente.')

    def validate_carreras(self, carreras):
        """Validar carreras si se seleccionó un rol que requiera carrera"""
        roles = self.get_roles_list()
        requiere_carrera = any(r in roles for r in ['jefe_carrera', 'profesor_completo', 'profesor_asignatura'])
        
        if requiere_carrera and (not carreras.data or len(carreras.data) == 0):
            raise ValidationError('Los profesores y jefes de carrera deben seleccionar al menos una carrera.')
    
    def validate_roles_seleccionados(self, roles_seleccionados):
        """Validar que se haya seleccionado al menos un rol"""
        roles = self.get_roles_list()
        if not roles:
            raise ValidationError('Debe seleccionar al menos un rol.')
            
    def get_roles_list(self):
        """Obtener la lista de roles seleccionados desde request.form (checkboxes)"""
        from flask import request
        # Los checkboxes se envían como una lista con el mismo nombre
        roles = request.form.getlist('roles_seleccionados')
        return roles if roles else []
    
    def get_primary_rol(self):
        """Obtener el rol principal para el campo legacy"""
        roles = self.get_roles_list()
        # Prioridad: admin > jefe_carrera > profesor_completo > profesor_asignatura
        if 'admin' in roles:
            return 'admin'
        elif 'jefe_carrera' in roles:
            return 'jefe_carrera'
        elif 'profesor_completo' in roles:
            return 'profesor_completo'
        elif 'profesor_asignatura' in roles:
            return 'profesor_asignatura'
        return roles[0] if roles else ''
    
    def get_final_rol(self):
        """Alias para get_primary_rol - obtener el rol final para el campo legacy"""
        return self.get_primary_rol()

    
    def is_profesor(self):
        """Verificar si alguno de los roles seleccionados es de profesor"""
        roles = self.get_roles_list()
        return 'profesor_completo' in roles or 'profesor_asignatura' in roles
    
    def get_disponibilidades_data(self):
        """Obtener los datos de disponibilidad del formulario"""
        from flask import request
        disponibilidades = []
        
        # Procesar todos los campos que empiecen con 'disp_' desde request.form
        for field_name in request.form.keys():
            if field_name.startswith('disp_'):
                parts = field_name.split('_')
                if len(parts) >= 3:
                    horario_id = parts[1]
                    dia_semana = parts[2]
                    disponible = True  # Si está en request.form, está marcado
                    
                    disponibilidades.append({
                        'horario_id': int(horario_id),
                        'dia_semana': dia_semana,
                        'disponible': disponible
                    })
        
        return disponibilidades

class EliminarUsuarioForm(FlaskForm):
    """Formulario para confirmar eliminación de usuario"""
    confirmacion = StringField('Escriba "ELIMINAR" para confirmar', validators=[
        DataRequired(),
        Length(min=8, max=8, message='Debe escribir exactamente "ELIMINAR"')
    ])

    submit = SubmitField('Eliminar Usuario')

    def validate_confirmacion(self, confirmacion):
        """Validar que se haya escrito exactamente "ELIMINAR" """
        if confirmacion.data != 'ELIMINAR':
            raise ValidationError('Debe escribir exactamente "ELIMINAR" para confirmar la eliminación.')

class AsignarMateriasProfesorForm(FlaskForm):
    """Formulario para asignar materias a un profesor"""
    materias = SelectMultipleField('Materias', coerce=int, validators=[
        DataRequired(message='Debe seleccionar al menos una materia')
    ])
    
    submit = SubmitField('Asignar Materias')
    
    def __init__(self, profesor=None, *args, **kwargs):
        super(AsignarMateriasProfesorForm, self).__init__(*args, **kwargs)
        self.profesor = profesor
        
        # Obtener carreras del profesor
        if profesor and profesor.carreras:
            # Filtrar materias por las carreras del profesor
            carrera_ids = [c.id for c in profesor.carreras]
            materias_disponibles = Materia.query.filter(
                Materia.carrera_id.in_(carrera_ids),
                Materia.activa == True
            ).order_by(Materia.cuatrimestre, Materia.nombre).all()
        else:
            # Si no tiene carreras, mostrar todas las materias activas
            materias_disponibles = Materia.query.filter_by(activa=True).order_by(
                Materia.cuatrimestre, Materia.nombre
            ).all()
        
        # Crear opciones agrupadas por cuatrimestre
        self.materias.choices = [
            (m.id, f"Cuatri {m.cuatrimestre} - {m.codigo}: {m.nombre} ({m.get_carrera_codigo()})")
            for m in materias_disponibles
        ]

class GrupoForm(FlaskForm):
    """Formulario para crear/editar grupos"""
    numero_grupo = IntegerField('Número de Grupo', validators=[
        DataRequired(message='El número de grupo es requerido'),
        NumberRange(min=1, max=99, message='El número debe estar entre 1 y 99')
    ])
    
    turno = SelectField('Turno', choices=[
        ('', 'Seleccione un turno'),
        ('M', 'Matutino'),
        ('V', 'Vespertino')
    ], validators=[DataRequired(message='Debe seleccionar un turno')])
    
    carrera = SelectField('Carrera', coerce=int, validators=[DataRequired(message='Debe seleccionar una carrera')])
    
    cuatrimestre = SelectField('Cuatrimestre', choices=[
        (-1, 'Seleccione un cuatrimestre'),
        (0, 'Propedéutico (0)'),
        (1, '1er Cuatrimestre'),
        (2, '2do Cuatrimestre'),
        (3, '3er Cuatrimestre'),
        (4, '4to Cuatrimestre'),
        (5, '5to Cuatrimestre'),
        (6, '6to Cuatrimestre'),
        (7, '7mo Cuatrimestre'),
        (8, '8vo Cuatrimestre'),
        (9, '9no Cuatrimestre'),
        (10, '10mo Cuatrimestre')
    ], coerce=int, validators=[DataRequired(message='Debe seleccionar un cuatrimestre')])
    
    submit = SubmitField('Guardar Grupo')
    
    def __init__(self, *args, **kwargs):
        super(GrupoForm, self).__init__(*args, **kwargs)
        # Cargar carreras activas
        from models import Carrera
        carreras = Carrera.query.filter_by(activa=True).order_by(Carrera.nombre).all()
        self.carrera.choices = [(0, 'Seleccione una carrera')] + [
            (c.id, f"{c.codigo} - {c.nombre}") for c in carreras
        ]

class AsignarMateriasGrupoForm(FlaskForm):
    """Formulario para asignar materias a un grupo"""
    materias = SelectMultipleField('Materias', coerce=int, validators=[
        DataRequired(message='Debe seleccionar al menos una materia')
    ])
    submit = SubmitField('Guardar Materias')
    
    def __init__(self, grupo=None, *args, **kwargs):
        super(AsignarMateriasGrupoForm, self).__init__(*args, **kwargs)
        
        from models import Materia
        
        if grupo:
            # Filtrar materias por carrera y cuatrimestre del grupo
            materias_disponibles = Materia.query.filter(
                Materia.carrera_id == grupo.carrera_id,
                Materia.cuatrimestre == grupo.cuatrimestre,
                Materia.activa == True
            ).order_by(Materia.codigo).all()
        else:
            materias_disponibles = []
        
        # Crear opciones
        self.materias.choices = [
            (m.id, f"{m.codigo} - {m.nombre} ({m.creditos} créditos)")
            for m in materias_disponibles
        ]

class CambiarPasswordProfesorForm(FlaskForm):
    """Formulario para que el administrador cambie la contraseña de un profesor"""
    nueva_password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(message='La contraseña es obligatoria'),
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    
    confirmar_password = PasswordField('Confirmar Nueva Contraseña', validators=[
        DataRequired(message='Debe confirmar la contraseña'),
        EqualTo('nueva_password', message='Las contraseñas deben coincidir')
    ])
    
    submit = SubmitField('Cambiar Contraseña')

class CambiarPasswordObligatorioForm(FlaskForm):
    """Formulario para cambio obligatorio de contraseña temporal"""
    password_actual = PasswordField('Contraseña Temporal Actual', validators=[
        DataRequired(message='La contraseña actual es obligatoria')
    ])
    
    nueva_password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(message='La nueva contraseña es obligatoria'),
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    
    confirmar_password = PasswordField('Confirmar Nueva Contraseña', validators=[
        DataRequired(message='Debe confirmar la contraseña'),
        EqualTo('nueva_password', message='Las contraseñas deben coincidir')
    ])
    
    submit = SubmitField('Cambiar Contraseña')