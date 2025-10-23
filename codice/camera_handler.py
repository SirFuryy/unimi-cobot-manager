# camera_handler.py

from crop_sensing import zed_manager, find_plant, create_plc
import numpy as np

from multi_terminal_gui import MultiTerminalGUI
from pose_class import Pose

from typing import Tuple, List

global zed, pose  # Global variable to hold the ZED camera instance and the original pose, setted to None initially
zed = None
pose = Pose()

def start_cam(system_pose: Pose, gui: MultiTerminalGUI):
    """
    Initializes the ZED camera if it is not already initialized.
    This function attempts to initialize the ZED camera using the provided
    system pose. If the camera is already initialized, it notifies the user
    through the GUI. If the initialization fails, an exception is raised
    and an error message is displayed in the GUI.
    Args:
        system_pose (Pose): The pose of the system used to initialize the ZED camera.
        gui (MultiTerminalGUI): The GUI object used to display messages to the user.
    Raises:
        Exception: If the ZED camera initialization fails.
    """
    
    global zed, pose
    if zed is None:
        print("start in start")
        try:
            zed = zed_manager.zed_init(system_pose)
            pose = system_pose
            gui.write_to_terminal(2, "ZED camera initialized.")
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to initialize ZED camera: {e}")
            raise e
    else:
        gui.write_to_terminal(2, "ZED camera is already initialized.")

def scan_and_find_plants(system_pose: Pose, plants_number: int, gui: MultiTerminalGUI, bbox_type: str = "p"):
    """
    Scans the environment using a ZED camera to locate and segment plants, returning their 3D bounding boxes.
    Args:
        system_pose (Pose): The initial pose of the system, used to initialize the camera.
        plants_number (int): The number of plants to segment and identify in the environment.
        gui (MultiTerminalGUI): The graphical user interface object for displaying information and saving outputs.
        bbox_type (str, optional): The format of the bounding boxes to return. Possible values are "c" for standard COCO format, "y" for YOLO absolute format, or "p" for Pascal VOC format. Defaults to "p".
    Returns:
        list: A list of 3D bounding boxes for the segmented plants. Each bounding box is represented as a set of 3D points in the Pascal Voc standard, such as 
            {
                "min": {"x": x_min, "y": y_min, "z": z_min},
                "max": {"x": x_max, "y": y_max, "z": z_max}
            }.
    Notes:
        - The function initializes the ZED camera if it is not already started.
        - Captures an image, depth map, normal map, and point cloud of the environment.
        - Filters the plants from the background using a mask.
        - Segments the plants into clusters and saves a visualization of the clustered image.
        - Extracts the 3D bounding boxes of the segmented plants using the point cloud data.
    """
     
    global zed, pose


    if bbox_type not in ["c", "y", "p"]:
        exception_msg = f"Invalid bbox_type '{bbox_type}'. Must be 'c', 'y', or 'p'."
        gui.write_to_terminal(4, exception_msg)
        raise ValueError(exception_msg)

    # Initialize the ZED camera
    if zed is None:
        print("scanand start cam")
        start_cam(system_pose, gui)
        pose = system_pose

    # Capture the environment with the ZED camera
    image, depth_map, normal_map, point_cloud = get_image_cam(pose, gui, save=True)

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
        if bbxpts is None:
            continue
         # Convert to desired bbox format
        if bbox_type == "c":
            bbox_temp = get_bbox_COCO(bbxpts)
            if bbox_temp is None:
                continue
            bbox.append([val * 1000 for val in bbox_temp])  # Convert to mm
        if bbox_type == "p":
            bbox_temp = get_bbox_PascalVOC(bbxpts)
            if bbox_temp is None:
                continue
            bbox.append([val * 1000 for val in bbox_temp])
        if bbox_type == "y":
            bbox_temp = get_bbox_YOLO(bbxpts)
            if bbox_temp is None:
                continue
            bbox.append([val * 1000 for val in bbox_temp])
            
    gui.write_to_terminal(2, f"Piante trovate: {bbox}")

    return bbox

def get_image_cam(system_pose: Pose, gui: MultiTerminalGUI, save: bool = False):
    """
    Captures an image and related data from the ZED camera.
    This function retrieves an image, depth map, normal map, and point cloud 
    from the ZED camera. If the camera is not initialized, it logs an error 
    message to the GUI terminal. Optionally, the captured image can be saved.
    Args:
        gui (MultiTerminalGUI): The GUI instance used to display messages 
            and logs.
        save (bool, optional): A flag indicating whether to save the captured 
            image. Defaults to False.
    Returns:
        tuple or None: A tuple containing the image, depth map, normal map, 
        and point cloud if successful. Returns None if an error occurs or 
        if the camera is not initialized.
    """
    
    global zed
    if zed is None:
        print("getimage start cam")
        start_cam(system_pose, gui)
        pose = system_pose
    
    try:
        image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(zed, save=save)
        gui.write_to_terminal(2, f"Image captured and saved from ZED camera.")
        close_cam(gui)  #close cam after getting image
        return image, depth_map, normal_map, point_cloud
    except Exception as e:
        gui.write_to_terminal(4, f"Failed to get image from ZED camera: {e}")
        close_cam(gui) #close cam if error
        raise e

def record_cam(system_pose: Pose, gui: MultiTerminalGUI, plant_name: str = "piantina1", frames: int = 300):
    """
    Records a point cloud using the ZED camera and saves it to a file.
    This function interacts with a ZED camera to capture a point cloud for a specified plant.
    The captured data is saved to a file, and the status of the operation is displayed in the GUI.
    Args:
        gui (MultiTerminalGUI): The GUI instance used to display messages to the user.
        plant_name (str, optional): The name of the plant for which the point cloud is recorded.
                                    Defaults to "piantina1".
        frames (int, optional): The number of frames to record for the point cloud. Defaults to 300.
    Raises:
        Exception: If an error occurs during the recording or saving process, the exception is raised
                   and an error message is displayed in the GUI.
    Notes:
        - The ZED camera must be initialized before calling this function. If the camera is not
          initialized, a message is displayed in the GUI, and the function exits without performing
          any operation.
        - The function uses the `create_plc.record_and_save` method to handle the recording and saving
          of the point cloud data.
    """

    try:
        create_plc.record_and_save(plant_name=plant_name, frames=frames)
        gui.write_to_terminal(2, f"Point cloud for {plant_name} recorded and saved.")
    except Exception as e:
        gui.write_to_terminal(4, f"Failed to record point cloud: {e}")
        raise e

def close_cam(gui: MultiTerminalGUI):
    """
    Closes the ZED camera if it is currently initialized.
    This function checks if the global `zed` camera object is initialized.
    If it is, the camera is closed, the `zed` object is set to `None`, and
    a message is written to the first terminal of the provided `MultiTerminalGUI`
    instance indicating that the camera has been closed. If the `zed` object
    is not initialized, a message is written to the terminal indicating that
    the camera is not initialized.
    Args:
        gui (MultiTerminalGUI): An instance of the MultiTerminalGUI class used
                                to write messages to the terminal.
    """
    
    global zed
    if zed is not None:
        zed.close()
        zed = None
        gui.write_to_terminal(2, "ZED camera closed.")
    else:
        gui.write_to_terminal(2, "ZED camera is not initialized.")

def get_bbox_COCO(bbox: dict[str, dict[str, float]] | None):
    """
    Given a bounding box JSON with 'min' and 'max' points, compute the COCO format bbox as float values, such as:
        [x_min, y_min, z_min, width, depth, height].
    """
    if bbox is None:
        print("bbox is None in get_bbox_COCO")
        return None
    min_pt = {k: float(v) for k, v in bbox["min"].items()}
    max_pt = {k: float(v) for k, v in bbox["max"].items()}
    width = max_pt["x"] - min_pt["x"]
    depth = max_pt["y"] - min_pt["y"]
    height = max_pt["z"] - min_pt["z"]
    return [min_pt["x"], min_pt["y"], min_pt["z"], width, depth, height]

def get_bbox_YOLO(bbox: dict[str, dict[str, float]] | None):
    """
    Given a bounding box JSON with 'min' and 'max' points, compute the YOLO format bbox in absolute value as float values, such as:
        [center_x, center_y, center_z, width, depth, height].
    """
    if bbox is None:
        print("bbox is None in get_bbox_YOLO")
        return None
    min_pt = {k: float(v) for k, v in bbox["min"].items()}
    max_pt = {k: float(v) for k, v in bbox["max"].items()}
    center_x = (min_pt["x"] + max_pt["x"]) / 2.0
    center_y = (min_pt["y"] + max_pt["y"]) / 2.0
    center_z = (min_pt["z"] + max_pt["z"]) / 2.0
    width = max_pt["x"] - min_pt["x"]
    depth = max_pt["y"] - min_pt["y"]
    height = max_pt["z"] - min_pt["z"]
    return [center_x, center_y, center_z, width, depth, height]

def get_bbox_PascalVOC(bbox: dict[str, dict[str, float]] | None):
    """
    Given a bounding box JSON with 'min' and 'max' points, compute the Pascal VOC format bbox as int values, such as:
        [x_min, y_min, z_min, x_max, y_max, z_max]
    """
    if bbox is None:
        print("bbox is None in get_bbox_PascalVOC")
        return None
    min_pt = {k: int(float(v)) for k, v in bbox["min"].items()}
    max_pt = {k: int(float(v)) for k, v in bbox["max"].items()}
    return [min_pt["x"], min_pt["y"], min_pt["z"], max_pt["x"], max_pt["y"], max_pt["z"]]


def get_dobot_front_face_center_and_size(bbox: dict):
    """
    Given a bounding box JSON with 'min' and 'max' points, compute:
    - min_pt, max_pt as float dicts
    - dobot_coords as (center_x, center_y, center_z, rx, ry, rz)
    - bbox_size as (size_x, size_y, size_z)
    """

    # Convert string values in JSON to floats
    min_pt = {k: float(v) for k, v in bbox["min"].items()}
    max_pt = {k: float(v) for k, v in bbox["max"].items()}

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

# Metodo di test
def usa_cam(pose: Pose, plants_number: int): 
    """
    Metodo di test per utilizzare la telecamera ZED e processare l'ambiente circostante.
    Questo metodo inizializza la telecamera ZED, cattura immagini e mappe di profondità,
    filtra le piante dallo sfondo, segmenta le piante in cluster e salva i dati rilevanti.
    Inoltre, registra un video dell'ambiente per creare un file di point cloud (.ply).
    Args:
        pose (Pose): La posizione iniziale della telecamera ZED.
        plants_number (int): Il numero di piante da segmentare nell'immagine.
    Note:
        Questo metodo è progettato per scopi di test e dimostrazione.
    """

    global zed
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
    
    
def calculate_scan_points(self, center_x: float, center_y: float, 
                             center_z: float, distance: float = 0.5) -> List[Tuple[float, float, float]]:
        """
        Calcola i quattro punti attorno alla piantina.
        
        Args:
            center_x, center_y, center_z: Coordinate del centro della piantina
            distance: Distanza dal centro per i punti di scansione
            
        Returns:
            Lista di tuple con le coordinate dei quattro punti
        """
        points = [
            (center_x + distance, center_y, center_z),  # Destra
            (center_x, center_y + distance, center_z),  # Avanti
            (center_x - distance, center_y, center_z),  # Sinistra
            (center_x, center_y - distance, center_z)   # Indietro
        ]
        return points