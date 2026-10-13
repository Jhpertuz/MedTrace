from functools import wraps
import base64
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from .extensions import db
from .models import Equipo, ReporteFalla, Usuario
from .services import PRIORITY_ORDER, ampliar_plazo, confirmar_grupo, crear_reporte, guardar_revision, registrar_equipo, transition
from .vision import ImageError, detectar_marcadores, generar_marcador_png

bp = Blueprint("main", __name__)
STATUS_LABELS = {
    "reportado": "Reportado",
    "en_revision": "En revisión",
    "en_mantenimiento": "En mantenimiento",
    "reparado": "Reparado: verificar y liberar",
    "cerrado": "Cerrado",
}


def engineer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(Usuario, user_id) if user_id else None
        if not user or user.rol != "ingeniero":
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    return db.session.get(Usuario, session["user_id"])


@bp.get("/health")
def health():
    try:
        db.session.execute(select(1)); return jsonify(status="ok")
    except Exception:
        return jsonify(status="error"), 503


@bp.get("/station")
def station():
    return render_template("station.html")


@bp.post("/api/identify")
def identify():
    image = request.files.get("image")
    if not image: return jsonify(status="invalid_image", message="Debe enviar una imagen."), 400
    try: markers = detectar_marcadores(image.read())
    except ImageError as error: return jsonify(status="invalid_image", message=str(error)), 400
    if not markers: return jsonify(status="marker_not_found", message="No se detectó ningún marcador."), 422
    if len(markers) != 1: return jsonify(status="multiple_markers", message="Capture un único equipo."), 422
    equipment = Equipo.query.filter_by(aruco_id=markers[0]["id"]).first()
    if not equipment: return jsonify(status="equipment_not_found", marker_id=markers[0]["id"], message="El marcador no está registrado."), 404
    return jsonify(status="equipment_identified", marker_id=equipment.aruco_id, equipment={"id": equipment.id, "nombre": equipment.nombre, "tipo": equipment.tipo, "serial": equipment.serial, "estado_operativo": equipment.estado_operativo})


@bp.post("/api/reports")
def reports():
    data = request.get_json(silent=True) or request.form
    try:
        equipo_id = int(data.get("equipo_id", ""))
    except (TypeError, ValueError): return jsonify(error="Debe identificar un equipo válido."), 400
    equipment = db.session.get(Equipo, equipo_id)
    if not equipment: return jsonify(error="El equipo identificado no existe."), 404
    try: report = crear_reporte(equipment, data.get("reportado_por", ""), data.get("descripcion", ""), data.get("impacto_operativo", ""))
    except ValueError as error: return jsonify(error=str(error)), 400
    return jsonify(id=report.id, prioridad=report.prioridad, puntaje=report.puntaje_prioridad, validacion_respaldo_pendiente=report.validacion_respaldo_pendiente), 201


@bp.route("/engineer/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Usuario.query.filter_by(email=request.form.get("email", "").lower().strip()).first()
        if user and user.rol == "ingeniero" and check_password_hash(user.password_hash, request.form.get("password", "")):
            session.clear(); session["user_id"] = user.id; return redirect(url_for("main.engineer"))
        return render_template("engineer_login.html", error="Credenciales inválidas."), 401
    return render_template("engineer_login.html")


@bp.post("/engineer/logout")
@engineer_required
def logout():
    session.clear(); return redirect(url_for("main.login"))


@bp.get("/engineer")
@engineer_required
def engineer():
    priority_case = case({"critica": 4, "alta": 3, "media": 2, "baja": 1}, value=ReporteFalla.prioridad, else_=0)
    reports = ReporteFalla.query.filter(ReporteFalla.estado != "cerrado").order_by(ReporteFalla.validacion_respaldo_pendiente.desc(), priority_case.desc(), ReporteFalla.puntaje_prioridad.desc(), ReporteFalla.created_at.asc()).all()
    summary = {name: sum(1 for report in reports if report.prioridad == name) for name in PRIORITY_ORDER}
    lanes = {state: [report for report in reports if report.estado == state] for state in ("reportado", "en_revision", "en_mantenimiento", "reparado")}
    counts = {state: db.session.scalar(select(db.func.count(ReporteFalla.id)).where(ReporteFalla.estado == state)) or 0 for state in lanes}
    return render_template("engineer.html", summary=summary, lanes=lanes, counts=counts, status_labels=STATUS_LABELS)


@bp.route("/registro", methods=["GET", "POST"])
@engineer_required
def register_equipment():
    form_values = request.form if request.method == "POST" else {}
    equipment = None
    aruco_image = None
    if request.method == "POST":
        try:
            equipment = registrar_equipo(
                request.form.get("nombre", ""), request.form.get("tipo", ""),
                request.form.get("serial", ""),
                request.form.get("grupo_respaldo", ""), request.form.get("criticidad", ""),
                request.form.get("nivel_uso", ""), request.form.get("estado_operativo", "operativo"),
            )
        except ValueError as error:
            return render_template("registro.html", error=str(error), form_values=form_values), 400
        except IntegrityError:
            db.session.rollback()
            return render_template("registro.html", error="El serial o el ID ArUco ya está registrado. Intente nuevamente.", form_values=form_values), 409
        return redirect(url_for("main.register_equipment", equipo_id=equipment.id))

    equipment_id = request.args.get("equipo_id", type=int)
    if equipment_id:
        equipment = db.session.get(Equipo, equipment_id)
        if not equipment: abort(404)
        aruco_image = "data:image/png;base64," + base64.b64encode(generar_marcador_png(equipment.aruco_id)).decode("ascii")
    return render_template("registro.html", equipment=equipment, aruco_image=aruco_image, form_values=form_values)


@bp.get("/engineer/reports/<int:report_id>")
@engineer_required
def report_detail(report_id):
    report = db.session.get(ReporteFalla, report_id)
    if not report: abort(404)
    return render_template("report_detail.html", report=report, status_labels=STATUS_LABELS, form_values={})


@bp.get("/engineer/equipment/<int:equipment_id>/history")
@engineer_required
def equipment_history(equipment_id):
    equipment = db.session.get(Equipo, equipment_id)
    if not equipment: abort(404)
    return render_template("equipment_history.html", equipment=equipment)


@bp.get("/engineer/history")
@engineer_required
def find_equipment_history():
    serial = request.args.get("serial", "").strip()
    if not serial:
        flash("Escriba el serial del equipo para consultar su historial.", "info")
        return redirect(url_for("main.engineer"))
    equipment = Equipo.query.filter_by(serial=serial).first()
    if not equipment:
        flash("No se encontró un equipo con ese serial.", "info")
        return redirect(url_for("main.engineer"))
    return redirect(url_for("main.equipment_history", equipment_id=equipment.id))


@bp.post("/engineer/reports/<int:report_id>/confirm-backup-group")
@engineer_required
def confirm_backup_group(report_id):
    report = db.session.get(ReporteFalla, report_id)
    if not report: abort(404)
    try: confirmar_grupo(report, request.form.get("grupo_respaldo", ""))
    except ValueError as error: return render_template("report_detail.html", report=report, error=str(error), status_labels=STATUS_LABELS, form_values=request.form), 400
    return redirect(url_for("main.report_detail", report_id=report.id))


@bp.post("/engineer/reports/<int:report_id>/transition")
@engineer_required
def report_transition(report_id):
    report = db.session.get(ReporteFalla, report_id)
    if not report: abort(404)
    days_raw = request.form.get("dias_estimados", "")
    try: days = int(days_raw) if days_raw != "" else None
    except ValueError: days = None
    try:
        transition(report, current_user(), request.form.get("nuevo_estado", ""),
            observacion=request.form.get("observacion", "").strip() or None,
            reporte_final=request.form.get("reporte_final", "").strip() or None,
            reporte_liberacion=request.form.get("reporte_liberacion", "").strip() or None)
    except ValueError as error: return render_template("report_detail.html", report=report, error=str(error), status_labels=STATUS_LABELS, form_values=request.form), 400
    return redirect(url_for("main.report_detail", report_id=report.id))


@bp.post("/engineer/reports/<int:report_id>/review")
@engineer_required
def save_review(report_id):
    report = db.session.get(ReporteFalla, report_id)
    if not report: abort(404)
    try:
        days_raw = request.form.get("dias_estimados", "")
        if not days_raw.strip() or not days_raw.strip().isdigit():
            raise ValueError("Los días estimados deben ser un entero no negativo.")
        days = int(days_raw)
        guardar_revision(report, current_user(), request.form.get("diagnostico", ""), days)
    except (ValueError, TypeError) as error:
        db.session.rollback()
        message = str(error) or "Los días estimados deben ser un entero no negativo."
        return render_template("report_detail.html", report=report, error=message, status_labels=STATUS_LABELS, form_values=request.form), 400
    flash("Diagnóstico y estimación guardados.", "success")
    return redirect(url_for("main.report_detail", report_id=report.id))


@bp.post("/engineer/reports/<int:report_id>/extend-days")
@engineer_required
def extend_days(report_id):
    report = db.session.get(ReporteFalla, report_id)
    if not report: abort(404)
    try:
        days_raw = request.form.get("dias_adicionales", "")
        if not days_raw.strip() or not days_raw.strip().isdigit():
            raise ValueError("Los días adicionales deben ser un entero mayor que cero.")
        days = int(days_raw)
        ampliar_plazo(report, current_user(), days, request.form.get("observacion", ""))
    except (ValueError, TypeError) as error:
        db.session.rollback()
        message = str(error) or "Los días adicionales deben ser un entero mayor que cero."
        return render_template("report_detail.html", report=report, error=message, status_labels=STATUS_LABELS, form_values=request.form), 400
    flash("Plazo ampliado y registrado en el historial.", "success")
    return redirect(url_for("main.report_detail", report_id=report.id))
