import numpy as np
import cv2

def raw_bytes_to_cv2_image(image_raw_bytes):
    nparr = np.fromstring(image_raw_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def draw_boxes(image, boxes):
    for box in boxes:
        cv2.rectangle(image, box[0], box[1], (0, 255, 0), 2)
    return image