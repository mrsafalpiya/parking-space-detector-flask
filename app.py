import cv2
from flask import Flask, request, send_file, Response
from flask_cors import CORS
from flask_sock import Sock
from roi_detection import get_roi_coordinates
from image import raw_bytes_to_cv2_image, draw_boxes
from environment_config import fov_angle, distance, object_width
from free_occupied_slots_detection import get_objects_from_image, get_text_from_image
import threading
import json
import os
import time

app = Flask(__name__)
CORS(app)
sock = Sock(app)

ws_client = None

# in-memory datastore of parking slots ROI coordinates
roi_coordinates = []

# signal that the latest image is uploaded
is_uploaded = False

# labels for the objects detected by AWS Rekognition
vehicle_labels = ['Machine', 'Wheel', 'Car', 'Car Wheel', 'Truck', 'Bulldozer', 'Toy']

# last slots information
# used to get the difference between the last and current slots information to know the vehicle which has entered or exited recently
last_slots_info = None


@app.route('/roi-detection', methods=['POST'])
def roi_detection():
    global roi_coordinates

    image_raw_bytes = request.get_data()
    image = raw_bytes_to_cv2_image(image_raw_bytes)

    # First get the ROI coordinates
    roi_coordinates = get_roi_coordinates(image, fov_angle, distance,
                                          object_width + 0.5)  # + 0.5 inch to give some breathing room between the objects

    # Save the original image
    save_location_non_roi = "static/original-output.jpg"
    cv2.imwrite(save_location_non_roi, image)

    # Save an image with the ROI drawn
    save_location = "static/roi-detection-output.jpg"
    image_with_roi = draw_boxes(image, roi_coordinates)
    cv2.imwrite(save_location, image_with_roi)

    # Crop and save individual ROI images
    for i, roi in enumerate(roi_coordinates):
        (x1, y1), (x2, y2) = roi
        roi_image = image[y1:y2, x1:x2]
        cv2.imwrite(f'static/roi-{i}.jpg', roi_image)

    return "Image saved"


@app.route('/upload', methods=['POST'])
def upload():
    global is_uploaded

    image_raw_bytes = request.get_data()
    image = raw_bytes_to_cv2_image(image_raw_bytes)

    save_location = "static/uploaded.jpg"
    cv2.imwrite(save_location, image)

    is_uploaded = True
    print("[DEBUG] evt.set() from /upload", flush=True)

    return "Image saved"


@sock.route('/connect')
def ws_connect(ws):
    global ws_client
    ws_client = ws
    while True:
        data = ws.receive()
        if data == 'stop':
            break
    ws_client = None


@app.route('/slot-details')
def get_parking_details():
    global is_uploaded

    # Remove old file
    try:
        os.remove('static/uploaded.jpg')
    except:
        pass

    is_uploaded = False
    # Command the ESP32-CAM to upload the image
    ws_client.send('upload')
    # Wait till the image is uploaded by ESP32-CAM
    while not is_uploaded:
        time.sleep(0.5)
    print("[DEBUG] evt.wait() complete from /slot-details", flush=True)

    slot_details = get_slot_details()

    return Response(json.dumps({'parking_slots': slot_details}), mimetype='application/json')


@app.route('/is-parking-slot-available')
def is_parking_slot_available():
    global is_uploaded

    # Remove old file
    try:
        os.remove('static/uploaded.jpg')
    except:
        pass

    is_uploaded = False
    # Command the ESP32-CAM to upload the image
    ws_client.send('upload')
    # Wait till the image is uploaded by ESP32-CAM
    while not is_uploaded:
        time.sleep(0.5)
    print("[DEBUG] evt.wait() complete from /is-parking-slot-available", flush=True)

    # Get slot details and the number of vehicles
    slot_details = get_slot_details()
    number_of_vehicles = 0
    for slot in slot_details:
        if slot['is_occupied']:
            number_of_vehicles += 1

    available_count = len(roi_coordinates) - number_of_vehicles
    print(f"[DEBUG] Available parking slots: {available_count}", flush=True)
    print(f"[DEBUG] Slot details: {slot_details}", flush=True)

    return str(available_count)


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def get_slot_details():
    global last_slots_info

    # Remove old images
    for i in range(len(roi_coordinates)):
        try:
            os.remove(f'static/roi-{i}.jpg')
        except:
            pass

    # Get the image from the ESP32-CAM, split it into ROIs and get the objects in each ROI
    image = cv2.imread('static/uploaded.jpg')
    slot_details = []

    # First get the objects and texts in each ROI
    objects_and_texts = [None] * len(roi_coordinates) * 2
    threads = []
    for i, roi in enumerate(roi_coordinates):
        (x1, y1), (x2, y2) = roi
        roi_image = image[y1:y2, x1:x2]
        threads.append(threading.Thread(target=get_objects_from_image, args=(roi_image, i * 2, objects_and_texts)))
        threads[i * 2].start()
        threads.append(threading.Thread(target=get_text_from_image, args=(roi_image, i * 2 + 1, objects_and_texts)))
        threads[i * 2 + 1].start()
    for thread in threads:
        thread.join()

    for i, roi in enumerate(roi_coordinates):
        (x1, y1), (x2, y2) = roi
        roi_image = image[y1:y2, x1:x2]
        cv2.imwrite(f'static/roi-{i}.jpg', roi_image)

        is_occupied = False
        for obj in objects_and_texts[i * 2]:
            if obj['Name'] in vehicle_labels:
                is_occupied = True
                break

        plate_number = objects_and_texts[i * 2 + 1]

        slot_details.append({
            'slot': i + 1,
            'is_occupied': is_occupied,
            'plate_number': plate_number,
        })

    # Save and compare the last and current slot details in a new log like variable storing the vehicle number, time and week day
    # To know the newly entered or exited vehicle
    if last_slots_info is not None:
        for i, slot in enumerate(slot_details):
            if slot['is_occupied'] and not last_slots_info[i]['is_occupied']:
                print("Vehicle Entered:", slot['plate_number'])
            elif not slot['is_occupied'] and last_slots_info[i]['is_occupied']:
                print("Vehicle Exited:", last_slots_info[i]['plate_number'])
        pass

    last_slots_info = slot_details

    return slot_details


if __name__ == '__main__':
    app.run()
