from datetime import datetime, timedelta, timezone
import base64
import cv2
import numpy as np
import re
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import Equipo, HistorialReporte, ReporteFalla, Usuario
from app.services import crear_reporte
from app.vision import detectar_marcadores


def marker_bytes(marker_id):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    image = np.full((240, 240), 255, dtype=np.uint8)
    image[30:210, 30:210] = cv2.aruco.generateImageMarker(dictionary, marker_id, 180)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def equipment(aruco=42, group="g", serial=None):
    item = Equipo(nombre=f"Equipo {aruco}", tipo="Tipo", serial=serial or f"SER-{aruco}", aruco_id=aruco, grupo_respaldo=group, criticidad="apoyo", nivel_uso="bajo", estado_operativo="operativo")
    db.session.add(item); db.session.commit()
    return item


def login(client, email="engineer@test.local", password="test-password"):
    user = Usuario(nombre="Engineer", email=email, password_hash=generate_password_hash(password), rol="ingeniero")
    db.session.add(user); db.session.commit()
    return client.post("/engineer/login", data={"email": email, "password": password}, follow_redirects=False), user


def test_identify_registered_and_unknown_marker(client):
    equipment(42)
    response = client.post("/api/identify", data={"image": ( __import__("io").BytesIO(marker_bytes(42)), "marker.png")})
    assert response.status_code == 200 and response.json["status"] == "equipment_identified"
    response = client.post("/api/identify", data={"image": (__import__("io").BytesIO(marker_bytes(99)), "marker.png")})
    assert response.status_code == 404 and response.json["status"] == "equipment_not_found"
    assert Equipo.query.count() == 1


def test_report_is_stored_with_priority_and_backup_excludes_open(client):
    primary = equipment(42, "g")
    backup = equipment(43, "g")
    db.session.add(ReporteFalla(equipo=backup, reportado_por="old", descripcion="open", impacto_operativo="sin_impacto", estado="reportado")); db.session.commit()
    response = client.post("/api/reports", json={"equipo_id": primary.id, "reportado_por": "Ana", "descripcion": "Falla", "impacto_operativo": "detiene_servicio"})
    assert response.status_code == 201
    report = db.session.get(ReporteFalla, response.json["id"])
    assert report.cantidad_respaldos_al_calcular == 0 and report.prioridad == "critica"


def test_missing_backup_group_is_pending_not_invented(client):
    primary = equipment(42, None)
    response = client.post("/api/reports", json={"equipo_id": primary.id, "reportado_por": "Ana", "descripcion": "Falla", "impacto_operativo": "degradado"})
    report = db.session.get(ReporteFalla, response.json["id"])
    assert report.validacion_respaldo_pendiente and report.prioridad is None and report.puntaje_prioridad is None


def test_auth_and_complete_maintenance_release_flow(client):
    primary = equipment(42, None)  # unknown backup group must not block maintenance
    report = crear_reporte(primary, "Ana", "Falla del equipo", "detiene_servicio")
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_revision"}).status_code == 302
    _, user = login(client)

    # Receiving the report has no diagnostic, days, backup, or functional gates.
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_revision"}).status_code == 302
    assert db.session.get(ReporteFalla, report.id).estado == "en_revision"
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_revision"}).status_code == 400
    report = db.session.get(ReporteFalla, report.id)
    assert primary.estado_operativo == "fuera_servicio"
    assert client.post(f"/engineer/reports/{report.id}/review", data={"diagnostico": "Fuente de poder intermitente", "dias_estimados": "2"}).status_code == 302
    report = db.session.get(ReporteFalla, report.id)
    score = report.puntaje_prioridad
    assert report.diagnostico == "Fuente de poder intermitente" and report.dias_estimados == 2

    # Missing compatible backup is informational and does not block the transition.
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_mantenimiento"}).status_code == 302
    assert primary.estado_operativo == "mantenimiento"
    assert report.diagnostico == "Fuente de poder intermitente" and report.dias_estimados == 2
    assert report.dias_estimados_iniciales == 2

    assert client.post(f"/engineer/reports/{report.id}/extend-days", data={"dias_adicionales": "3", "observacion": "Repuesto de importación retrasado"}).status_code == 302
    assert report.dias_estimados == 5 and report.puntaje_prioridad == score
    extension = HistorialReporte.query.filter_by(reporte_id=report.id, tipo_evento="plazo_ampliado").one()
    assert extension.detalles == {"dias_anterior": 2, "dias_adicionales": 3, "dias_nuevo": 5}

    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "reparado"}).status_code == 400
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "reparado", "reporte_final": "Se cambió la fuente y se probó el equipo"}).status_code == 302
    assert report.estado == "reparado" and primary.estado_operativo == "mantenimiento"
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_mantenimiento"}).status_code == 400
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "en_mantenimiento", "observacion": "Falla persiste en prueba de carga"}).status_code == 302
    assert report.estado == "en_mantenimiento" and primary.estado_operativo == "mantenimiento"
    assert report.reporte_final_mantenimiento == "Se cambió la fuente y se probó el equipo"

    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "reparado", "reporte_final": "Se ajustó el cableado y se repitieron pruebas"}).status_code == 302
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "cerrado"}).status_code == 400
    assert client.post(f"/engineer/reports/{report.id}/transition", data={"nuevo_estado": "cerrado", "reporte_liberacion": "Prueba funcional satisfactoria; se devuelve a servicio"}).status_code == 302
    assert report.estado == "cerrado" and primary.estado_operativo == "operativo"
    assert report.reporte_liberacion == "Prueba funcional satisfactoria; se devuelve a servicio"
    events = HistorialReporte.query.filter_by(reporte_id=report.id).order_by(HistorialReporte.id).all()
    assert [event.tipo_evento for event in events] == ["reporte_creado", "revision_iniciada", "revision_guardada", "mantenimiento_iniciado", "plazo_ampliado", "mantenimiento_finalizado", "retorno_a_mantenimiento", "mantenimiento_finalizado", "equipo_liberado"]
    assert events[6].observacion == "Falla persiste en prueba de carga"
    assert events[7].observacion == "Se ajustó el cableado y se repitieron pruebas"
    assert events[8].observacion == "Prueba funcional satisfactoria; se devuelve a servicio"
    assert all(event.usuario_id == user.id for event in events[1:])

    history_page = client.get(f"/engineer/equipment/{primary.id}/history")
    assert history_page.status_code == 200
    assert b"Prueba funcional satisfactoria" in history_page.data
    assert b"Falla persiste en prueba de carga" in history_page.data


def test_dashboard_lists_real_status_counts_and_return_reason(client):
    reported_equipment = equipment(42, "reported")
    returned_equipment = equipment(43, "returned")
    reported = crear_reporte(reported_equipment, "Ana", "Pendiente de revisión visible", "sin_impacto")
    returned = crear_reporte(returned_equipment, "Ana", "Necesita nueva intervención", "sin_impacto")
    returned.diagnostico = "Diagnóstico guardado"
    returned.dias_estimados = 1
    returned.estado = "reparado"
    db.session.commit()
    login(client)
    response = client.post(f"/engineer/reports/{returned.id}/transition", data={"nuevo_estado": "en_mantenimiento", "observacion": "Nueva falla tras reparación"})
    assert response.status_code == 302
    page = client.get("/engineer").data.decode()
    assert "Pendientes de revisión" in page and "En mantenimiento" in page
    assert "Nueva falla tras reparación" in page
    assert f'data-report-id="{reported.id}"' in page and f'data-report-id="{returned.id}"' in page
    assert 'id="reparados"' in page and "Reparados por verificar" in page


def test_detail_only_shows_controls_for_current_stage(client):
    item = equipment(42, "group")
    report = crear_reporte(item, "Ana", "Falla", "degradado")
    login(client)
    page = client.get(f"/engineer/reports/{report.id}").data.decode()
    assert "Iniciar revisión" in page and "diagnostico" not in page

    report.estado = "en_revision"; db.session.commit()
    page = client.get(f"/engineer/reports/{report.id}").data.decode()
    assert "Guardar diagnóstico y estimación" in page
    assert "Ampliar días estimados" not in page and "Reporte final de mantenimiento" not in page

    report.diagnostico = "Prueba"; report.dias_estimados = 0; report.dias_estimados_iniciales = 0
    report.estado = "en_mantenimiento"; db.session.commit()
    page = client.get(f"/engineer/reports/{report.id}").data.decode()
    assert "Ampliar días estimados" in page and "Reporte final de mantenimiento" in page
    assert "Reporte de liberación" not in page

    report.estado = "reparado"; report.reporte_final_mantenimiento = "Reparado"; db.session.commit()
    page = client.get(f"/engineer/reports/{report.id}").data.decode()
    assert "Reporte de liberación" in page and "Volver a mantenimiento" in page
    assert "Ampliar días estimados" not in page and "Guardar diagnóstico y estimación" not in page


def test_closed_equipment_history_can_be_found_by_serial(client):
    item = equipment(42, "group")
    login(client)
    response = client.get("/engineer/history?serial=SER-42")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/engineer/equipment/{item.id}/history")


def test_register_equipment_generates_printable_matching_aruco(client):
    assert client.get("/registro").status_code == 302
    login(client)
    response = client.post("/registro", data={
        "nombre": "Bomba de infusión", "tipo": "Infusión", "serial": "BINF-9001",
        "aruco_id": "249", "grupo_respaldo": "infusion_general",
        "criticidad": "diagnostico_terapia", "nivel_uso": "alto", "estado_operativo": "operativo",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Equipo registrado exitosamente" in response.data and b"ID ArUco 0" in response.data
    equipment = Equipo.query.filter_by(serial="BINF-9001").one()
    assert equipment.aruco_id == 0 and equipment.grupo_respaldo == "infusion_general"
    image_data = re.search(rb'src="data:image/png;base64,([^\"]+)', response.data).group(1)
    image_bytes = base64.b64decode(image_data)
    markers = detectar_marcadores(image_bytes)
    assert [marker["id"] for marker in markers] == [0]
    duplicate = client.post("/registro", data={
        "nombre": "Duplicado", "tipo": "Infusión", "serial": "BINF-9001",
        "criticidad": "apoyo", "nivel_uso": "bajo", "estado_operativo": "operativo",
    })
    assert duplicate.status_code == 400 and b"ya est\xc3\xa1 asignado" in duplicate.data


def test_queue_orders_pending_then_priority_then_oldest(client):
    a = equipment(42, None); b = equipment(43, "bg"); c = equipment(44, "cg")
    pending = crear_reporte(a, "A", "a", "sin_impacto")
    high = crear_reporte(b, "B", "b", "detiene_servicio")
    low = crear_reporte(c, "C", "c", "sin_impacto")
    high.created_at = datetime.now(timezone.utc) - timedelta(days=1); db.session.commit()
    login(client)
    page = client.get("/engineer").data.decode()
    assert page.index(f"#{pending.id}") < page.index(f"#{high.id}") < page.index(f"#{low.id}")


def test_dashboard_separates_reports_by_workflow_state(client):
    reported_equipment = equipment(42, "reported")
    review_equipment = equipment(43, "review")
    maintenance_equipment = equipment(44, "maintenance")
    reported = crear_reporte(reported_equipment, "Ana", "Nueva falla", "sin_impacto")
    review = crear_reporte(review_equipment, "Ana", "En revisión", "sin_impacto")
    maintenance = crear_reporte(maintenance_equipment, "Ana", "En mantenimiento", "sin_impacto")
    review.estado = "en_revision"
    maintenance.estado = "en_mantenimiento"
    db.session.commit()
    login(client)
    page = client.get("/engineer").data.decode()
    assert 'id="reportados"' in page and 'id="revision"' in page and 'id="mantenimiento"' in page
    reported_section = page[page.index('id="reportados"'):page.index('id="revision"')]
    review_section = page[page.index('id="revision"'):page.index('id="mantenimiento"')]
    maintenance_section = page[page.index('id="mantenimiento"'):page.index('id="reparados"')]
    assert f'data-report-id="{reported.id}"' in reported_section
    assert f'data-report-id="{review.id}"' in review_section
    assert f'data-report-id="{maintenance.id}"' in maintenance_section
