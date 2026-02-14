"""
GENERADOR DE HORARIOS - WRAPPER DE UNIFICACIÓN

Este archivo ha sido limpiado para redirigir todas las solicitudes
al nuevo motor robusto en `generador_horarios_mejorado.py`.
"""

from generador_horarios_mejorado import (
    GeneradorHorariosMejorado,
    generar_horarios_secuencial,
    generar_horarios_por_etapas,
    diagnosticar_y_generar
)

# Wrapper para mantener compatibilidad con app.py
def generar_horarios_masivos(
    grupos_ids,
    periodo_academico="2025-1",
    version_nombre=None,
    creado_por=None,
    dias_semana=None,
    usar_generador_mejorado=True, # Ignorado, siempre es True
    modo="secuencial",
):
    """
    Función fachada que redirige al generador secuencial mejorado.
    """
    print("🚀 Usando motor unificado (GeneradorHorariosMejorado)...")
    
    # Por defecto forzamos el modo secuencial que es el más robusto para
    # evitar conflictos y horarios repetitivos/planos.
    return generar_horarios_secuencial(
        grupos_ids=grupos_ids,
        periodo_academico=periodo_academico,
        version_nombre=version_nombre,
        creado_por=creado_por,
        dias_semana=dias_semana,
    )

def generar_horarios_automaticos(
    grupo_id,
    dias_semana=None,
    periodo_academico="2025-1",
    version_nombre=None,
    creado_por=None
):
    """
    Generar horarios para un solo grupo usando el motor mejorado.
    """
    print(f"🚀 Generando horarios para grupo {grupo_id} con motor mejorado...")
    
    return generar_horarios_secuencial(
        grupos_ids=[grupo_id],
        periodo_academico=periodo_academico,
        version_nombre=version_nombre,
        creado_por=creado_por,
        dias_semana=dias_semana,
    )
