from flask import Flask, request
from flask_sock import Sock
import os

app = Flask(__name__)
sock = Sock(app)

ws_client = None


@app.route('/')
def get_parking_details():  # put application's code here
    try:
        ws_client.send('upload')
    except:
        return 'TODO'

    return 'TODO'


@app.route('/aoi-detection', methods=['POST'])
def aoi_detection():
    image_raw_bytes = request.get_data()
    save_location = (os.path.join(app.root_path, "static/test.jpg"))

    f = open(save_location, 'wb')  # wb for write byte data in the file instead of string
    f.write(image_raw_bytes)  # write the bytes from the request body to the file
    f.close()

    print("Image saved")

    return "Image saved"


@app.route('/upload', methods=['POST'])
def upload():
    image_raw_bytes = request.get_data()
    save_location = (os.path.join(app.root_path, "static/test.jpg"))

    f = open(save_location, 'wb')  # wb for write byte data in the file instead of string
    f.write(image_raw_bytes)  # write the bytes from the request body to the file
    f.close()

    print("Image saved")

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


if __name__ == '__main__':
    app.run()
