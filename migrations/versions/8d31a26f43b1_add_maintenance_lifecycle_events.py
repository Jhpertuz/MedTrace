"""Add maintenance lifecycle fields and structured history events.

Revision ID: 8d31a26f43b1
Revises: 359cc5165fa1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "8d31a26f43b1"
down_revision = "359cc5165fa1"
branch_labels = None
depends_on = None


def _has_column(table, column):
    return column in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}


def upgrade():
    for name, column_type in (("dias_estimados_iniciales", sa.Integer()), ("reporte_final_mantenimiento", sa.Text()), ("reporte_liberacion", sa.Text()), ("mantenimiento_started_at", sa.DateTime(timezone=True))):
        if not _has_column("reportes_falla", name):
            op.add_column("reportes_falla", sa.Column(name, column_type, nullable=True))
    op.execute("UPDATE reportes_falla SET dias_estimados_iniciales = dias_estimados WHERE dias_estimados IS NOT NULL")
    op.execute("UPDATE reportes_falla SET mantenimiento_started_at = updated_at WHERE estado IN ('en_mantenimiento', 'reparado')")
    if not _has_column("historial_reportes", "tipo_evento"):
        op.add_column("historial_reportes", sa.Column("tipo_evento", sa.String(length=40), nullable=True))
    if not _has_column("historial_reportes", "detalles"):
        op.add_column("historial_reportes", sa.Column("detalles", sa.JSON(), nullable=True))
    op.execute("UPDATE historial_reportes SET tipo_evento = 'transicion_estado' WHERE tipo_evento IS NULL")
    with op.batch_alter_table("historial_reportes") as batch:
        batch.alter_column("tipo_evento", existing_type=sa.String(length=40), nullable=False, server_default="transicion_estado")
        batch.alter_column("usuario_id", existing_type=sa.Integer(), nullable=True)
    op.execute("""
        INSERT INTO historial_reportes
            (reporte_id, usuario_id, estado_anterior, estado_nuevo, observacion, tipo_evento, detalles, created_at)
        SELECT r.id, NULL, 'reportado', r.estado,
               'Registro inicial conservado durante la actualización del historial',
               'reporte_existente', NULL, r.created_at
        FROM reportes_falla r
        WHERE NOT EXISTS (
            SELECT 1 FROM historial_reportes h
            WHERE h.reporte_id = r.id AND h.tipo_evento = 'reporte_creado'
        )
    """)


def downgrade():
    op.alter_column("historial_reportes", "usuario_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("historial_reportes", "detalles")
    op.drop_column("historial_reportes", "tipo_evento")
    op.drop_column("reportes_falla", "mantenimiento_started_at")
    op.drop_column("reportes_falla", "reporte_liberacion")
    op.drop_column("reportes_falla", "reporte_final_mantenimiento")
    op.drop_column("reportes_falla", "dias_estimados_iniciales")
