"""Generate printable ArUco DICT_6X6_250 demonstration markers."""
from pathlib import Path
import cv2
import numpy as np

OUTPUT = Path(__file__).resolve().parents[1] / "markers"


def generate(marker_ids=(42, 43, 44), size=600, margin=60):
    OUTPUT.mkdir(exist_ok=True)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    for marker_id in marker_ids:
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, size)
        image = cv2.copyMakeBorder(marker, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=255)
        cv2.imwrite(str(OUTPUT / f"aruco_6x6_250_id_{marker_id}.png"), image)


if __name__ == "__main__":
    generate()
