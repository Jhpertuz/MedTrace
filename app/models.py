from datetime import datetime, timezone
from sqlalchemy import JSON
from .extensions import db


def now():
    return datetime.now(timezone.utc)


class Equipo(db.Model):
    __tablename__ = "equipos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    serial = db.Column(db.String(100), nullable=False, unique=True)
    aruco_id = db.Column(db.Integer, nullable=False, unique=True)
    grupo_respaldo = db.Column(db.String(80), nullable=True)
    criticidad = db.Column(db.String(30), nullable=False)
    nivel_uso = db.Column(db.String(15), nullable=False)
    estado_operativo = db.Column(db.String(30), nullable=False, default="operativo")
    reportes = db.relationship("ReporteFalla", back_populates="equipo", lazy=True)
    __table_args__ = (db.CheckConstraint("aruco_id >= 0 AND aruco_id <= 249", name="aruco_id_range"),)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(30), nullable=False)


class ReporteFalla(db.Model):
    __tablename__ = "reportes_falla"
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos.id"), nullable=False)
    reportado_por = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    impacto_operativo = db.Column(db.String(30), nullable=False)
    puntaje_prioridad = db.Column(db.Integer, nullable=True)
    prioridad = db.Column(db.String(15), nullable=True)
    cantidad_respaldos_al_calcular = db.Column(db.Integer, nullable=True)
    reincidencias_90d = db.Column(db.Integer, nullable=True)
    validacion_respaldo_pendiente = db.Column(db.Boolean, nullable=False, default=False)
    estado = db.Column(db.String(30), nullable=False, default="reportado")
    diagnostico = db.Column(db.Text, nullable=True)
    dias_estimados = db.Column(db.Integer, nullable=True)
    dias_estimados_iniciales = db.Column(db.Integer, nullable=True)
    reporte_final_mantenimiento = db.Column(db.Text, nullable=True)
    reporte_liberacion = db.Column(db.Text, nullable=True)
    mantenimiento_started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    respaldo_confirmado = db.Column(db.Boolean, nullable=False, default=False)
    verificacion_funcional = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    equipo = db.relationship("Equipo", back_populates="reportes")
    historial = db.relationship("HistorialReporte", back_populates="reporte", order_by=lambda: [HistorialReporte.created_at, HistorialReporte.id], lazy=True)


class HistorialReporte(db.Model):
    __tablename__ = "historial_reportes"
    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes_falla.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    estado_anterior = db.Column(db.String(30), nullable=False)
    estado_nuevo = db.Column(db.String(30), nullable=False)
    observacion = db.Column(db.Text, nullable=True)
    tipo_evento = db.Column(db.String(40), nullable=False, default="transicion_estado")
    detalles = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    reporte = db.relationship("ReporteFalla", back_populates="historial")
    usuario = db.relationship("Usuario")
