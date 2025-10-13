# camera_handler_mock.py
"""
Versione di camera_handler che usa un mock di pyzed per evitare errori DLL.
Sostituisce temporaneamente il camera_handler originale.
"""

# Prova prima pyzed normale, poi fall back al mock
try:
    from crop_sensing import zed_manager, find_plant, create_plc
    ZED_AVAILABLE = True
    print("[INFO] ZED SDK disponibile - usando librerie originali")
except ImportError as e:
    print(f"[WARNING] Errore importazione ZED SDK: {e}")
    print("[INFO] Usando mock di pyzed per continuare lo sviluppo")
    ZED_AVAILABLE = False
    # Import il nostro mock
    import pyzed_mock as sl

from multi_terminal_gui import MultiTerminalGUI
from pose_class import Pose
import numpy as np

zed = None  # Global variable to hold the ZED camera instance

def start_cam(pose: Pose, gui: MultiTerminalGUI):
    global zed
    if ZED_AVAILABLE:
        # Usa il ZED reale
        if zed is None:
            try:
                zed = zed_manager.zed_init(pose)
                gui.write_to_terminal(0, "ZED camera initialized successfully.")
            except Exception as e:
                gui.write_to_terminal(4, f"Failed to initialize ZED camera: {e}")
        else:
            gui.write_to_terminal(0, "ZED camera is already initialized.")
    else:
        # Usa il mock
        if zed is None:
            try:
                init_params = sl.InitParameters()
                init_params.camera_resolution = sl.RESOLUTION.HD720
                init_params.camera_fps = 30
                init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
                init_params.coordinate_units = sl.UNIT.MILLIMETER
                
                zed = sl.Camera()
                err = zed.open(init_params)
                
                if err == sl.ERROR_CODE.SUCCESS:
                    gui.write_to_terminal(0, "[MOCK] ZED camera initialized successfully (simulation mode).")
                else:
                    gui.write_to_terminal(4, f"[MOCK] Failed to initialize ZED camera: {err}")
            except Exception as e:
                gui.write_to_terminal(4, f"[MOCK] Exception during camera init: {e}")
        else:
            gui.write_to_terminal(0, "[MOCK] ZED camera is already initialized.")

def use_cam(pose: Pose, plants_number: int, gui: MultiTerminalGUI): 
    global zed
    if ZED_AVAILABLE:
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
    else:
        # Mock version
        gui.write_to_terminal(0, f"[MOCK] Simulando rilevamento di {plants_number} piante")
        
        # Initialize mock camera
        if zed is None:
            start_cam(pose, gui)
        
        # Simula bounding box delle piante
        bbox = []
        for i in range(plants_number):
            # Genera coordinate mock per ogni pianta
            mock_bbox = {
                "min": {"x": -100 - i*50, "y": 200 + i*30, "z": 100},
                "max": {"x": -50 - i*50, "y": 250 + i*30, "z": 150}
            }
            bbox.append(mock_bbox)
        
        gui.write_to_terminal(2, f"[MOCK] Generati {len(bbox)} bounding box simulati")
        return bbox

def get_image_cam(gui: MultiTerminalGUI, save: bool = False):
    global zed
    if zed is None:
        gui.write_to_terminal(0, "ZED camera is not initialized. Please start the camera first.")
        return None, None, None, None
    
    if ZED_AVAILABLE:
        try:
            image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(zed, save=save)
            gui.write_to_terminal(2, f"Image captured and saved from ZED camera.")
            return image, depth_map, normal_map, point_cloud
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to get image from ZED camera: {e}")
            return None, None, None, None
    else:
        try:
            # Mock version
            runtime_params = sl.RuntimeParameters()
            
            # Grab frame
            err = zed.grab(runtime_params)
            if err != sl.ERROR_CODE.SUCCESS:
                gui.write_to_terminal(4, f"[MOCK] Failed to grab frame: {err}")
                return None, None, None, None
            
            # Create matrices
            image_mat = sl.Mat()
            depth_mat = sl.Mat()
            normal_mat = sl.Mat()
            point_cloud_mat = sl.Mat()
            
            # Allocate
            image_mat.alloc(640, 480, sl.MAT_TYPE.U8_C4)
            depth_mat.alloc(640, 480, sl.MAT_TYPE.F32_C1)
            normal_mat.alloc(640, 480, sl.MAT_TYPE.F32_C4)
            point_cloud_mat.alloc(640, 480, sl.MAT_TYPE.F32_C4)
            
            # Retrieve data
            zed.retrieve_image(image_mat, sl.VIEW.LEFT)
            zed.retrieve_measure(depth_mat, sl.MEASURE.DEPTH)
            zed.retrieve_measure(normal_mat, sl.MEASURE.NORMALS)
            zed.retrieve_measure(point_cloud_mat, sl.MEASURE.XYZ)
            
            # Get numpy arrays
            image = image_mat.get_data()
            depth_map = depth_mat.get_data()
            normal_map = normal_mat.get_data()
            point_cloud = point_cloud_mat.get_data()
            
            gui.write_to_terminal(2, f"[MOCK] Image captured from simulated ZED camera.")
            return image, depth_map, normal_map, point_cloud
        except Exception as e:
            gui.write_to_terminal(4, f"[MOCK] Failed to get image from ZED camera: {e}")
            return None, None, None, None

def record_cam(gui: MultiTerminalGUI, plant_name: str = "piantina1", frames: int = 300):
    global zed
    if zed is None:
        gui.write_to_terminal(0, "ZED camera is not initialized. Please start the camera first.")
        return

    if ZED_AVAILABLE:
        try:
            zed_manager.record_zed_video(zed, plant_name, frames)
            gui.write_to_terminal(2, f"Recording completed: {plant_name} with {frames} frames.")
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to record video: {e}")
    else:
        try:
            gui.write_to_terminal(2, f"[MOCK] Simulando registrazione di {frames} frame per {plant_name}")
            # Simula una breve pausa per la registrazione
            import time
            time.sleep(1)
            gui.write_to_terminal(2, f"[MOCK] Recording completed: {plant_name} with {frames} frames (simulated).")
        except Exception as e:
            gui.write_to_terminal(4, f"[MOCK] Failed to record video: {e}")

def close_cam(gui: MultiTerminalGUI):
    global zed
    if zed is not None:
        if ZED_AVAILABLE:
            zed.close()
            gui.write_to_terminal(0, "ZED camera closed successfully.")
        else:
            zed.close()
            gui.write_to_terminal(0, "[MOCK] ZED camera closed successfully.")
        zed = None
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
    """Versione legacy - mantienila per compatibilità"""
    if ZED_AVAILABLE:
        # Initialize the ZED camera
        zed_temp = zed_manager.zed_init(pose)
        
        # Capture the environment with the ZED camera
        image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(zed_temp, save=True)

        # Filter the plants from the background
        mask = find_plant.filter_plants(image, save_mask=True)
        
        # Divide the plants into clusters
        masks, bounding_boxes = find_plant.segment_plants(mask, plants_number)
        find_plant.save_clustered_image(image, bounding_boxes)

        # Extract the 3D points from the clusters
        for m in masks:
            bbox_points = find_plant.get_3d_bbox(m, point_cloud)

        # Create point cloud (this will create a .ply file by taking a video of the environment)
        zed_temp.close()
        create_plc.record_and_save(plant_name='piantina1', frames=300)
    else:
        print("[MOCK] usa_cam chiamata - simulazione completata")
        return "mock_completed"