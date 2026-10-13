import cv2
import numpy as np

ALLOWED_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")
_dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
_detector = cv2.aruco.ArucoDetector(_dictionary, cv2.aruco.DetectorParameters())


class ImageError(ValueError):
    pass


def detectar_marcadores(image_bytes: bytes):
    if not image_bytes or not image_bytes.startswith(ALLOWED_MAGIC):
        raise ImageError("La imagen debe ser JPEG o PNG válido.")
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ImageError("No se pudo decodificar la imagen.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = _detector.detectMarkers(gray)
    if ids is None:
        return []
    return [{"id": int(marker_id), "corners": points.reshape(4, 2).tolist()} for marker_id, points in zip(ids.flatten(), corners)]


def generar_marcador_png(marker_id: int) -> bytes:
    if not isinstance(marker_id, int) or not 0 <= marker_id <= 249:
        raise ValueError("El ID ArUco debe estar entre 0 y 249.")
    marker = cv2.aruco.generateImageMarker(_dictionary, marker_id, 600)
    printable = cv2.copyMakeBorder(marker, 60, 60, 60, 60, cv2.BORDER_CONSTANT, value=255)
    ok, encoded = cv2.imencode(".png", printable)
    if not ok:
        raise RuntimeError("No se pudo generar el archivo PNG del marcador.")
    return encoded.tobytes()
