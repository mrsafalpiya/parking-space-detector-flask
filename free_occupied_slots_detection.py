import boto3
import cv2
from dotenv import load_dotenv

load_dotenv()


def get_objects_from_image(image, i, objects_and_texts):
    reko_client = boto3.client('rekognition', region_name='ap-south-1')
    _, image_buffer = cv2.imencode('.jpg', image)
    image_bytes = image_buffer.tobytes()
    response = reko_client.detect_labels(Image={'Bytes': image_bytes}, MinConfidence=50, MaxLabels=5)
    objects_and_texts[i] = response['Labels']


def get_text_from_image(image, i, objects_and_texts):
    reko_client = boto3.client('rekognition', region_name='ap-south-1')
    _, image_buffer = cv2.imencode('.jpg', image)
    image_bytes = image_buffer.tobytes()
    response = reko_client.detect_text(Image={'Bytes': image_bytes})
    text_detections = response['TextDetections']
    try:
        text_detected = max(text_detections, key=lambda x: x['Confidence'])['DetectedText']
    except:
        text_detected = ''
    objects_and_texts[i] = text_detected.upper()
