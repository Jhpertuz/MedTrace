import cv2
import numpy as np
import pytest
from app.vision import ImageError, detectar_marcadores


def encoded(image):
    ok, content = cv2.imencode(".png", image)
    assert ok
    return content.tobytes()


def marker(marker_id, x=20, canvas=None):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    image = cv2.aruco.generateImageMarker(dictionary, marker_id, 180)
    canvas = canvas if canvas is not None else np.full((220, 220), 255, dtype=np.uint8)
    canvas[x:x+180, x:x+180] = image
    return canvas


def test_detects_real_generated_marker():
    assert [item["id"] for item in detectar_marcadores(encoded(marker(42)))] == [42]


def test_blank_image_has_no_markers():
    assert detectar_marcadores(encoded(np.full((300, 300), 255, dtype=np.uint8))) == []


def test_two_markers_are_detected():
    canvas = np.full((260, 460), 255, dtype=np.uint8)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    canvas[40:220, 20:200] = cv2.aruco.generateImageMarker(dictionary, 42, 180)
    canvas[40:220, 260:440] = cv2.aruco.generateImageMarker(dictionary, 43, 180)
    assert len(detectar_marcadores(encoded(canvas))) == 2


def test_corrupt_image_is_controlled():
    with pytest.raises(ImageError): detectar_marcadores(b"not an image")
