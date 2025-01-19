import math


def get_roi_coordinates(image, fov_angle, distance, object_width):
    frame_height, frame_width, _ = image.shape

    # Convert FOV angle to radians and calculate real-world FOV width
    fov_angle_rad = math.radians(fov_angle)
    fov_width = 2 * distance * math.tan(fov_angle_rad / 2)  # Real-world FOV width in inches

    # Scale pixels to inches
    scale = frame_width / fov_width

    # Calculate the number of objects that can fit
    num_objects = int(fov_width // object_width)

    # Calculate coordinates
    coordinates = []
    box_width = int(object_width * scale)  # Box width in pixels
    for i in range(num_objects):
        start_x = i * box_width
        end_x = start_x + box_width
        if i == num_objects - 1:
            end_x = frame_width
        coordinates.append([(start_x, 0), (end_x, frame_height)])

    return coordinates
