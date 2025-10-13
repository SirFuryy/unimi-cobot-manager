# camera_handler.py

from crop_sensing import zed_manager, find_plant, create_plc

from multi_terminal_gui import MultiTerminalGUI
from pose_class import Pose

zed = None  # Global variable to hold the ZED camera instance

def start_cam(pose: Pose, gui: MultiTerminalGUI):
    global zed
    if zed is None:
        try:
            zed = zed_manager.zed_init(pose)
            gui.write_to_terminal(0, "ZED camera initialized.")
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to initialize ZED camera: {e}")
            raise e
    else:
        gui.write_to_terminal(0, "ZED camera is already initialized.")

def use_cam(pose: Pose, plants_number: int, gui: MultiTerminalGUI): 
    global zed
    # Initialize the ZED camera
    if zed is None:
        start_cam(pose, gui)

    # Capture the environment with the ZED camera
    image, depth_map, normal_map, point_cloud = get_image_cam(gui, save=True)

    # Filter the plants from the background
    mask = find_plant.filter_plants(image, save_mask=True)
    
    # Divide the plants into clusters
    masks, bounding_boxes = find_plant.segment_plants(mask, plants_number)

    # Save clustered image for visualization
    find_plant.save_clustered_image(image, bounding_boxes)

    # Extract the 3D points from the clusters
    bbox = []
    for m in masks:
        bbxpts = find_plant.get_3d_bbox(m, point_cloud)
        bbox.append(bbxpts)

    return bbox

def get_image_cam(gui: MultiTerminalGUI, save: bool = False):
    global zed
    if zed is None:
        gui.write_to_terminal(0, "ZED camera is not initialized. Please start the camera first.")
        return
    
    try:
        image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(zed, save=False)
        gui.write_to_terminal(2, f"Image captured and saved from ZED camera.")
        return image, depth_map, normal_map, point_cloud
    except Exception as e:
        gui.write_to_terminal(4, f"Failed to get image from ZED camera: {e}")
        return None

def record_cam(gui: MultiTerminalGUI, plant_name: str = "piantina1", frames: int = 300):
    global zed
    if zed is None:
        gui.write_to_terminal(0, "ZED camera is not initialized. Please start the camera first.")
        return

    try:
        create_plc.record_and_save(plant_name=plant_name, frames=frames)
        gui.write_to_terminal(2, f"Point cloud for {plant_name} recorded and saved.")
    except Exception as e:
        gui.write_to_terminal(4, f"Failed to record point cloud: {e}")
        raise e

def close_cam(gui: MultiTerminalGUI):
    global zed
    if zed is not None:
        zed.close()
        zed = None
        gui.write_to_terminal(0, "ZED camera closed.")
    else:
        gui.write_to_terminal(0, "ZED camera is not initialized.")

def get_dobot_front_face_center_and_size(bbox_json: dict):
    """
    Given a bounding box JSON with 'min' and 'max' points, compute:
    - min_pt, max_pt as float dicts
    - dobot_coords as (center_x, center_y, center_z, rx, ry, rz)
    - bbox_size as (size_x, size_y, size_z)
    """
    # Convert string values in JSON to floats
    min_pt = {k: float(v) for k, v in bbox_json["min"].items()}
    max_pt = {k: float(v) for k, v in bbox_json["max"].items()}

    # Coordinates for 8 vertices of the box
    x_vals = [min_pt["x"], max_pt["x"]]
    y_vals = [min_pt["y"], max_pt["y"]]
    z_vals = [min_pt["z"], max_pt["z"]]
    vertici = [(x, y, z) for x in x_vals for y in y_vals for z in z_vals]

    # Compute center of the front face of the box (example logic)
    center_x = -143.0
    center_y = ((vertici[1][1] + vertici[4][1]) / 2.0) - 700
    center_z = 700.0

    # Default orientation (rx, ry, rz)
    rx = 90.0
    ry = 0.0
    rz = -180.0

    dobot_coords = (center_x, center_y, center_z, rx, ry, rz)

    # Compute size of bounding box along each axis
    xs = [v[0] for v in vertici]
    ys = [v[1] for v in vertici]
    zs = [v[2] for v in vertici]
    size_x = max(xs) - min(xs)
    size_y = max(ys) - min(ys)
    size_z = max(zs) - min(zs)
    bbox_size = (size_x, size_y, size_z)

    return min_pt, max_pt, dobot_coords, bbox_size

def usa_cam(pose: Pose, plants_number: int): 
    # Initialize the ZED camera
    zed = zed_manager.zed_init(pose)
    
    # Capture the environment with the ZED camera
    image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(zed, save=True)

    # Filter the plants from the background
    mask = find_plant.filter_plants(image, save_mask=True)
    
    # Divide the plants into clusters
    masks, bounding_boxes = find_plant.segment_plants(mask, plants_number)
    find_plant.save_clustered_image(image, bounding_boxes)

    # Extract the 3D points from the clusters
    for m in masks:
        bbxpts = find_plant.get_3d_bbox(m, point_cloud)

    # Create point cloud (this will create a .ply file by taking a video of the environment)
    zed.close()
    create_plc.record_and_save(plant_name='piantina1', frames=300)