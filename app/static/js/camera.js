const video = document.querySelector("#camera"),
  canvas = document.querySelector("#canvas"),
  identify = document.querySelector("#identify"),
  detection = document.querySelector("#detection"),
  equipment = document.querySelector("#equipment"),
  form = document.querySelector("#report-form"),
  csrf = document.querySelector('meta[name="csrf-token"]').content;
const setEnabled = (yes) =>
  document
    .querySelectorAll(
      "#report-form input:not([type=hidden]), #report-form textarea, #report-form select, #submit-report",
    )
    .forEach((x) => (x.disabled = !yes));
document.querySelector("#start-camera").onclick = async () => {
  try {
    video.srcObject = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    identify.disabled = false;
    detection.textContent = "Cámara lista.";
  } catch (e) {
    detection.textContent =
      "No se pudo acceder a la cámara. Compruebe permisos y HTTPS/localhost.";
  }
};
identify.onclick = async () => {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.9));
  const data = new FormData();
  data.append("image", blob, "capture.jpg");
  detection.textContent = "Identificando…";
  const response = await fetch("/api/identify", {
    method: "POST",
    headers: { "X-CSRFToken": csrf },
    body: data,
  });
  const result = await response.json();
  if (result.status === "equipment_identified") {
    document.querySelector("#equipo_id").value = result.equipment.id;
    equipment.innerHTML = `<strong>${result.equipment.nombre}</strong><br>${result.equipment.tipo} · ${result.equipment.serial}<br>Estado: ${result.equipment.estado_operativo}`;
    detection.textContent = "Equipo identificado.";
    setEnabled(true);
  } else {
    document.querySelector("#equipo_id").value = "";
    setEnabled(false);
    detection.textContent =
      result.message || "No se pudo identificar el equipo.";
  }
};
form.onsubmit = async (e) => {
  e.preventDefault();
  const payload = {
    equipo_id: document.querySelector("#equipo_id").value,
    reportado_por: document.querySelector("#reportado_por").value,
    descripcion: document.querySelector("#descripcion").value,
    impacto_operativo: document.querySelector("#impacto_operativo").value,
  };
  const button = document.querySelector("#submit-report");
  button.disabled = true;
  const response = await fetch("/api/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  document.querySelector("#confirmation").innerHTML = response.ok
    ? `<div class="alert alert-success">Reporte #${result.id} registrado. Prioridad: ${result.prioridad || "pendiente de validar respaldo"}.</div>`
    : `<div class="alert alert-danger">${result.error}</div>`;
  if (response.ok) {
    form.reset();
    setEnabled(false);
    document.querySelector("#equipo_id").value = "";
  } else button.disabled = false;
};
