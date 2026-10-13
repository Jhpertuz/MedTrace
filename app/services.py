from datetime import datetime, timedelta, timezone
from sqlalchemy import exists, select
from werkzeug.security import generate_password_hash
from .extensions import db
from .models import Equipo, HistorialReporte, ReporteFalla, Usuario

IMPACTS = {"detiene_servicio": 35, "degradado": 20, "sin_impacto": 5}
CRITICALITY = {"soporte_vital": 25, "diagnostico_terapia": 15, "apoyo": 8}
USAGE = {"alto": 10, "medio": 5, "bajo": 2}
OPEN_STATES = ("reportado", "en_revision", "en_mantenimiento", "reparado")
PRIORITY_ORDER = {"critica": 4, "alta": 3, "media": 2, "baja": 1}


def calcular_prioridad(impacto_operativo, criticidad, cantidad_respaldos, nivel_uso, reincidencias):
    if impacto_operativo not in IMPACTS or criticidad not in CRITICALITY or nivel_uso not in USAGE:
        raise ValueError("Factor de prioridad desconocido.")
    if not isinstance(cantidad_respaldos, int) or not isinstance(reincidencias, int) or cantidad_respaldos < 0 or reincidencias < 0:
        raise ValueError("Las cantidades deben ser enteros no negativos.")
    backup = 15 if cantidad_respaldos == 0 else 6 if cantidad_respaldos == 1 else 0
    recurrence = 0 if reincidencias == 0 else 5 if reincidencias < 3 else 15
    score = IMPACTS[impacto_operativo] + CRITICALITY[criticidad] + backup + USAGE[nivel_uso] + recurrence
    if impacto_operativo == "detiene_servicio" and cantidad_respaldos == 0:
        priority = "critica"
    elif score >= 70: priority = "critica"
    elif score >= 50: priority = "alta"
    elif score >= 30: priority = "media"
    else: priority = "baja"
    return score, priority


def contar_respaldos(equipo):
    if not equipo.grupo_respaldo:
        return None
    open_for_candidate = exists(select(ReporteFalla.id).where(
        ReporteFalla.equipo_id == Equipo.id, ReporteFalla.estado.in_(OPEN_STATES)))
    return db.session.scalar(select(db.func.count(Equipo.id)).where(
        Equipo.grupo_respaldo == equipo.grupo_respaldo, Equipo.id != equipo.id,
        Equipo.estado_operativo == "operativo", ~open_for_candidate))


def reincidencias(equipo_id, at=None):
    at = at or datetime.now(timezone.utc)
    return db.session.scalar(select(db.func.count(ReporteFalla.id)).where(
        ReporteFalla.equipo_id == equipo_id, ReporteFalla.created_at >= at - timedelta(days=90),
        ReporteFalla.created_at < at)) or 0


def _event(report, user, event_type, observation=None, details=None):
    state = report.estado
    db.session.add(HistorialReporte(reporte=report, usuario=user, estado_anterior=state,
        estado_nuevo=state, tipo_evento=event_type, observacion=observation, detalles=details))


def crear_reporte(equipo, reportado_por, descripcion, impacto_operativo):
    if not reportado_por.strip() or not descripcion.strip() or impacto_operativo not in IMPACTS:
        raise ValueError("Reportante, descripción e impacto válido son obligatorios.")
    report = ReporteFalla(equipo=equipo, reportado_por=reportado_por.strip(), descripcion=descripcion.strip(), impacto_operativo=impacto_operativo)
    with db.session.no_autoflush:
        backups = contar_respaldos(equipo)
        recurrences = reincidencias(equipo.id)
    if backups is None:
        report.validacion_respaldo_pendiente = True
    else:
        report.cantidad_respaldos_al_calcular = backups
        report.reincidencias_90d = recurrences
        report.puntaje_prioridad, report.prioridad = calcular_prioridad(impacto_operativo, equipo.criticidad, backups, equipo.nivel_uso, recurrences)
    db.session.add(report)
    db.session.flush()
    db.session.add(HistorialReporte(reporte_id=report.id, usuario_id=None, estado_anterior="reportado", estado_nuevo="reportado",
        tipo_evento="reporte_creado", observacion="Reporte registrado en estación",
        detalles={"equipo_id": equipo.id, "aruco_id": equipo.aruco_id, "reportado_por": report.reportado_por,
                  "descripcion": report.descripcion, "impacto_operativo": impacto_operativo,
                  "prioridad": report.prioridad, "puntaje": report.puntaje_prioridad}))
    db.session.commit()
    return report


def confirmar_grupo(reporte, grupo):
    if not grupo or not grupo.strip(): raise ValueError("El grupo compatible es obligatorio.")
    reporte.equipo.grupo_respaldo = grupo.strip()
    backups = contar_respaldos(reporte.equipo)
    recurrences = reincidencias(reporte.equipo_id, reporte.created_at)
    reporte.cantidad_respaldos_al_calcular = backups; reporte.reincidencias_90d = recurrences
    reporte.puntaje_prioridad, reporte.prioridad = calcular_prioridad(reporte.impacto_operativo, reporte.equipo.criticidad, backups, reporte.equipo.nivel_uso, recurrences)
    reporte.validacion_respaldo_pendiente = False; db.session.commit()


def guardar_revision(reporte, user, diagnostico, dias_estimados):
    if reporte.estado != "en_revision":
        raise ValueError("El diagnóstico solo se puede actualizar durante la revisión.")
    if not diagnostico or not diagnostico.strip():
        raise ValueError("El diagnóstico inicial es obligatorio.")
    if not isinstance(dias_estimados, int) or dias_estimados < 0:
        raise ValueError("Los días estimados deben ser un entero no negativo.")
    old_diagnosis, old_days = reporte.diagnostico, reporte.dias_estimados
    reporte.diagnostico = diagnostico.strip()
    reporte.dias_estimados = dias_estimados
    if reporte.dias_estimados_iniciales is None:
        reporte.dias_estimados_iniciales = dias_estimados
    _event(reporte, user, "revision_guardada", "Diagnóstico y estimación guardados",
        {"diagnostico_anterior": old_diagnosis, "diagnostico": reporte.diagnostico,
         "dias_estimados_anterior": old_days, "dias_estimados": dias_estimados})
    db.session.commit()


def ampliar_plazo(reporte, user, dias_adicionales, observacion):
    if reporte.estado != "en_mantenimiento":
        raise ValueError("El plazo solo se amplía durante el mantenimiento.")
    if not isinstance(dias_adicionales, int) or dias_adicionales <= 0:
        raise ValueError("Los días adicionales deben ser un entero mayor que cero.")
    if not observacion or not observacion.strip():
        raise ValueError("Explique el motivo de la ampliación.")
    anterior = reporte.dias_estimados or 0
    reporte.dias_estimados = anterior + dias_adicionales
    _event(reporte, user, "plazo_ampliado", observacion.strip(),
        {"dias_anterior": anterior, "dias_adicionales": dias_adicionales, "dias_nuevo": reporte.dias_estimados})
    db.session.commit()


def registrar_equipo(nombre, tipo, serial, grupo_respaldo, criticidad, nivel_uso, estado_operativo="operativo"):
    if not nombre or not nombre.strip() or not tipo or not tipo.strip() or not serial or not serial.strip():
        raise ValueError("Nombre, tipo y serial son obligatorios.")
    if criticidad not in CRITICALITY:
        raise ValueError("Seleccione una criticidad válida.")
    if nivel_uso not in USAGE:
        raise ValueError("Seleccione un nivel de uso válido.")
    if estado_operativo not in ("operativo", "fuera_servicio", "mantenimiento"):
        raise ValueError("Seleccione un estado operativo válido.")
    serial = serial.strip()
    if Equipo.query.filter_by(serial=serial).first():
        raise ValueError("El serial ya está asignado a otro equipo.")
    # Assign the next ID after the highest allocated one. Check availability
    # explicitly; the database unique constraint remains the final safeguard
    # if two registrations happen at the same time.
    aruco_id = (db.session.query(db.func.max(Equipo.aruco_id)).scalar() or -1) + 1
    while aruco_id <= 249 and Equipo.query.filter_by(aruco_id=aruco_id).first():
        aruco_id += 1
    if aruco_id > 249:
        raise ValueError("No quedan IDs ArUco disponibles (rango 0–249).")
    equipment = Equipo(nombre=nombre.strip(), tipo=tipo.strip(), serial=serial, aruco_id=aruco_id,
        grupo_respaldo=grupo_respaldo.strip() or None if grupo_respaldo else None,
        criticidad=criticidad, nivel_uso=nivel_uso, estado_operativo=estado_operativo)
    db.session.add(equipment)
    db.session.commit()
    return equipment


def transition(reporte, user, new_state, diagnostico=None, dias_estimados=None, respaldo_confirmado=False, verificacion_funcional=False, observacion=None, reporte_final=None, reporte_liberacion=None):
    allowed = {"reportado": {"en_revision"}, "en_revision": {"en_mantenimiento"}, "en_mantenimiento": {"reparado"}, "reparado": {"cerrado", "en_mantenimiento"}}
    if new_state not in allowed.get(reporte.estado, set()):
        raise ValueError("Transición de estado no permitida.")
    previous = reporte.estado
    if previous == "en_revision" and new_state == "en_mantenimiento":
        if not reporte.diagnostico or reporte.dias_estimados is None:
            raise ValueError("Guarde primero el diagnóstico y los días estimados de la revisión.")
    if previous == "en_mantenimiento" and new_state == "reparado":
        if not reporte_final or not reporte_final.strip():
            raise ValueError("Registre el reporte final de mantenimiento.")
        reporte.reporte_final_mantenimiento = reporte_final.strip()
    if previous == "reparado" and new_state == "cerrado":
        if not reporte_liberacion or not reporte_liberacion.strip():
            raise ValueError("Registre el reporte de liberación.")
        reporte.reporte_liberacion = reporte_liberacion.strip()
    if previous == "reparado" and new_state == "en_mantenimiento" and not (observacion and observacion.strip()):
        raise ValueError("Explique por qué el equipo vuelve a mantenimiento.")

    reporte.estado = new_state
    if new_state == "en_revision" and reporte.impacto_operativo == "detiene_servicio":
        reporte.equipo.estado_operativo = "fuera_servicio"
    elif new_state == "en_mantenimiento":
        reporte.equipo.estado_operativo = "mantenimiento"
        if reporte.mantenimiento_started_at is None:
            reporte.mantenimiento_started_at = datetime.now(timezone.utc)
    elif new_state == "reparado":
        reporte.equipo.estado_operativo = "mantenimiento"
    elif new_state == "cerrado":
        reporte.equipo.estado_operativo = "operativo"

    event_type = {"en_revision": "revision_iniciada",
        "en_mantenimiento": "mantenimiento_iniciado" if previous == "en_revision" else "retorno_a_mantenimiento",
        "reparado": "mantenimiento_finalizado", "cerrado": "equipo_liberado"}[new_state]
    event_observation = (reporte_final.strip() if new_state == "reparado" else
        reporte_liberacion.strip() if new_state == "cerrado" else observacion.strip() if observacion else None)
    details = {}
    if new_state == "en_mantenimiento": details = {"diagnostico": reporte.diagnostico, "dias_estimados": reporte.dias_estimados}
    elif new_state == "reparado": details = {"reporte_final_mantenimiento": reporte.reporte_final_mantenimiento}
    elif new_state == "cerrado": details = {"reporte_liberacion": reporte.reporte_liberacion}
    db.session.add(HistorialReporte(reporte=reporte, usuario=user, estado_anterior=previous,
        estado_nuevo=new_state, observacion=event_observation, tipo_evento=event_type, detalles=details))
    db.session.commit()


def seed_app(app):
    if not Usuario.query.filter_by(email=app.config["INITIAL_ENGINEER_EMAIL"]).first():
        db.session.add(Usuario(nombre="Ingeniero Demo", email=app.config["INITIAL_ENGINEER_EMAIL"], password_hash=generate_password_hash(app.config["INITIAL_ENGINEER_PASSWORD"]), rol="ingeniero"))
    demos = [("Ventilador UCI", "Ventilador", "VENT-42", 42, "ventilacion", "soporte_vital", "alto"), ("Ventilador respaldo", "Ventilador", "VENT-43", 43, "ventilacion", "soporte_vital", "alto"), ("Monitor multiparámetro", "Monitor", "MON-44", 44, "monitoreo", "diagnostico_terapia", "medio"), ("Monitor respaldo", "Monitor", "MON-45", 45, "monitoreo", "diagnostico_terapia", "medio"), ("Monitor respaldo 2", "Monitor", "MON-46", 46, "monitoreo", "diagnostico_terapia", "medio")]
    for nombre, tipo, serial, aruco, grupo, crit, uso in demos:
        if not Equipo.query.filter_by(serial=serial).first(): db.session.add(Equipo(nombre=nombre, tipo=tipo, serial=serial, aruco_id=aruco, grupo_respaldo=grupo, criticidad=crit, nivel_uso=uso, estado_operativo="operativo"))
    db.session.commit()
