# camera_handler.py

from crop_sensing import zed_manager, find_plant, create_plc
import numpy as np

from multi_terminal_gui_class import MultiTerminalGUI
from pose_class import Pose

from typing import Tuple, List, Optional, Dict


class CameraHandler:
    """
    Class to manage the ZED camera and the extraction of 3D bounding boxes of plants.
    """

    def __init__(self):
        self.zed = None  # ZED camera instance

    def start_cam(self, system_pose: Pose, gui: MultiTerminalGUI):
        """
        Initializes the ZED camera if it is not already active.

        If the camera is not initialized, it calls `zed_manager.zed_init(system_pose)` and logs
        a success message. If initialization fails, it logs an error message and re-raises
        the exception. If the camera is already initialized, it logs that information.

        Args:
            system_pose (Pose): The actual pose of the camera in the system used to configure the ZED camera.
            gui (MultiTerminalGUI): GUI interface for displaying status and error messages.

        Raises:
            Exception: If the camera initialization fails.
        
        Example:
            >>> controller.start_cam(current_pose, gui)
            ZED camera initialized.
        """
        
        if self.zed is None:
            try:
                self.zed = zed_manager.zed_init(system_pose)
                gui.write_to_terminal(2, "ZED camera initialized.")
            except Exception as e:
                gui.write_to_terminal(4, f"Failed to initialize ZED camera: {e}")
                raise e
        else:
            gui.write_to_terminal(2, "ZED camera is already initialized.")

    def scan_and_find_plants(self, system_pose: Pose, plants_number: int, gui: MultiTerminalGUI,
                             bbox_type: str = "p") -> List[List[float]]:
        """
        Scans the environment, segments plants, and returns their 3D bounding boxes.

        Args:
            system_pose (Pose): The current pose of the system for camera reference.
            plants_number (int): The number of plants to detect and segment.
            gui (MultiTerminalGUI): GUI interface for displaying status and error messages.
            bbox_type (str, optional): Format of the bounding box. 
                Must be 'c' (COCO), 'y' (YOLO), or 'p' (PascalVOC). Defaults to 'p'.

        Returns:
            List[List[float]]: A list of 3D bounding boxes (in millimeters) for the detected plants, in the format 
            {
                "min": {"x": x_min, "y": y_min, "z": z_min},
                "max": {"x": x_max, "y": y_max, "z": z_max}
            }.

        Raises:
            ValueError: If `bbox_type` is not one of 'c', 'y', or 'p'.
            Exception: If camera initialization fails.

        Example:
            >>> bbox_list = robot.scan_and_find_plants(current_pose, 2, gui, bbox_type='p')
            >>> print(bbox_list)
            [[120.0, 250.0, 100.0, 180.0, 300.0, 200.0], 
            [300.0, 400.0, 150.0, 350.0, 450.0, 200.0]]
        """
        
        if bbox_type not in ["c", "y", "p"]:
            gui.write_to_terminal(4, f"Invalid bbox_type '{bbox_type}'. Must be 'c', 'y', or 'p'.")
            raise ValueError(f"Invalid bbox_type '{bbox_type}'.")

        try:
            # Initialize the ZED camera
            if self.zed is None:
                self.start_cam(system_pose, gui)

            # Capture the environment with the ZED camera
            image, depth_map, normal_map, point_cloud = self.get_image_cam(system_pose, gui, save=True)

            # Filter the plants from the background
            mask = find_plant.filter_plants(image, save_mask=True)
            
            # Divide the plants into clusters
            masks, bounding_boxes = find_plant.segment_plants(mask, plants_number)
            
            # Save clustered image for visualization
            find_plant.save_clustered_image(image, bounding_boxes)

            # Extract the 3D points from the clusters
            bbox_list: List[List[float]] = []
            for m in masks:
                bbxpts = find_plant.get_3d_bbox(m, point_cloud)
                if bbxpts is None:
                    continue

                # Convert to desired bbox format
                if bbox_type == "c":
                    bbox_temp = self.get_bbox_COCO(bbxpts)
                    if bbox_temp is None:
                        continue
                    bbox_list.append([val * 1000 for val in bbox_temp])  # Convert to mm

                elif bbox_type == "p":
                    bbox_temp = self.get_bbox_PascalVOC(bbxpts)
                    if bbox_temp is None:
                        continue
                    bbox_list.append([val * 1000 for val in bbox_temp])

                elif bbox_type == "y":
                    bbox_temp = self.get_bbox_YOLO(bbxpts)
                    if bbox_temp is None:
                        continue
                    bbox_list.append([val * 1000 for val in bbox_temp])

            gui.write_to_terminal(2, f"Piante trovate: {bbox_list}")
            
            return bbox_list
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to scan and find plants: {e}")
            raise e

    def get_image_cam(self, system_pose: Pose, gui: MultiTerminalGUI, save: bool = False):
        """
        Captures an image, depth map, normal map, and point cloud from the ZED camera.

        If the camera is not already initialized, it will start it. After capturing, the camera is closed automatically.

        Args:
            system_pose (Pose): The current pose of the system for camera reference.
            gui (MultiTerminalGUI): GUI interface for displaying status and error messages.
            save (bool, optional): Whether to save the captured images and maps to disk. Defaults to False.

        Returns:
            Tuple: A tuple containing:
                - image: The RGB image captured from the ZED camera.
                - depth_map: The depth map corresponding to the captured image.
                - normal_map: The normal map of the scene.
                - point_cloud: The 3D point cloud generated from the camera data.

        Raises:
            Exception: If the image capture from the ZED camera fails.

        Example:
            >>> image, depth_map, normal_map, point_cloud = robot.get_image_cam(current_pose, gui, save=True)
            >>> print(image.shape, depth_map.shape)
            (720, 1280, 3) (720, 1280)
        """
        
        if self.zed is None:
            self.start_cam(system_pose, gui)

        try:
            image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(self.zed, save=save)
            gui.write_to_terminal(2, "Image captured and saved from ZED camera.")
            self.close_cam(gui)     # Close camera after capturing
            return image, depth_map, normal_map, point_cloud
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to get image from ZED camera: {e}")
            self.close_cam(gui)
            raise e

    def record_cam(self, system_pose: Pose, gui: MultiTerminalGUI, plant_name: str = "piantina1", frames: int = 300):
        """
        Records a point cloud sequence from the camera and saves it to disk.

        This function uses `create_plc.record_and_save` to capture a specified number of frames
        of a plant and save the resulting point cloud. Status messages are displayed in the GUI.

        Args:
            system_pose (Pose): The current pose of the system (used for reference, if needed).
            gui (MultiTerminalGUI): GUI interface for displaying status and error messages.
            plant_name (str, optional): Name of the plant used for saving the point cloud file. Defaults to "piantina1".
            frames (int, optional): Number of frames to capture for the point cloud. Defaults to 300.

        Raises:
            Exception: If recording or saving the point cloud fails.
            
        Example:
        >>> robot.record_cam(current_pose, gui, plant_name="tomato1", frames=500)

        """
        try:
            gui.write_to_terminal(2, f"Record point cloud for {plant_name} started.")
            create_plc.record_and_save(plant_name=plant_name, frames=frames, mesh=False)
            gui.write_to_terminal(2, f"Point cloud for {plant_name} recorded and saved.")
        except Exception as e:
            gui.write_to_terminal(4, f"Failed to record point cloud: {e}")
            raise e

    def close_cam(self, gui: MultiTerminalGUI):
        """
        Closes the ZED camera if it is currently initialized.

        This function safely shuts down the ZED camera and updates the `self.zed` attribute to None.
        Status messages are displayed in the GUI. If the camera is not initialized, a message is shown.

        Args:
            gui (MultiTerminalGUI): GUI interface for displaying status and error messages.
            
        Raises:
            Exception: If recording or saving the point cloud fails.

        Example:
            >>> robot.close_cam(gui)
        """
        if self.zed is not None:
            try:
                self.zed.close()
            except Exception as e:
                gui.write_to_terminal(4, f"Failed to close ZED camera: {e}")
            self.zed = None
            gui.write_to_terminal(2, "ZED camera closed.")
        else:
            gui.write_to_terminal(2, "ZED camera is not initialized.")

    @staticmethod
    def get_bbox_COCO(bbox: Optional[Dict[str, Dict[str, float]]]):
        """
        Given a bounding box JSON with 'min' and 'max' points, compute the COCO format bbox as float values, such as:
            [x_min, y_min, z_min, width, depth, height].
        """
        if bbox is None:
            return None
        min_pt = {k: float(v) for k, v in bbox["min"].items()}
        max_pt = {k: float(v) for k, v in bbox["max"].items()}
        width = max_pt["x"] - min_pt["x"]
        depth = max_pt["y"] - min_pt["y"]
        height = max_pt["z"] - min_pt["z"]
        return [min_pt["x"], min_pt["y"], min_pt["z"], width, depth, height]

    @staticmethod
    def get_bbox_YOLO(bbox: Optional[Dict[str, Dict[str, float]]]):
        """
        Given a bounding box JSON with 'min' and 'max' points, compute the YOLO format bbox in absolute value as float values, such as:
            [center_x, center_y, center_z, width, depth, height].
        """
        if bbox is None:
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

    @staticmethod
    def get_bbox_PascalVOC(bbox: Optional[Dict[str, Dict[str, float]]]):
        """
        Given a bounding box JSON with 'min' and 'max' points, compute the Pascal VOC format bbox as int values, such as:
            [x_min, y_min, z_min, x_max, y_max, z_max]
        """
        if bbox is None:
            return None
        min_pt = {k: int(float(v)) for k, v in bbox["min"].items()}
        max_pt = {k: int(float(v)) for k, v in bbox["max"].items()}
        return [min_pt["x"], min_pt["y"], min_pt["z"], max_pt["x"], max_pt["y"], max_pt["z"]]

    @staticmethod
    def get_dobot_front_face_center_and_size(bbox: Dict):
        """
        Computes the front face center, orientation, and size of a bounding box for Dobot usage.

        Given a bounding box dictionary with 'min' and 'max' points, this function computes:
            - `min_pt` and `max_pt` as dictionaries with float values.
            - `dobot_coords` as (center_x, center_y, center_z, rx, ry, rz), suitable for the Dobot.
            Note: The center coordinates are currently fixed offsets for example purposes.
            - `bbox_size` as (size_x, size_y, size_z) representing the dimensions of the box.

        Args:
            bbox (dict): A dictionary containing "min" and "max" keys, each mapping to a dict 
                        with "x", "y", "z" coordinates (as strings or numbers).

        Returns:
            tuple: A tuple containing:
                - min_pt (dict): Minimum point of the bounding box as floats.
                - max_pt (dict): Maximum point of the bounding box as floats.
                - dobot_coords (tuple): (x, y, z, rx, ry, rz) coordinates for Dobot.
                - bbox_size (tuple): Size of the bounding box along each axis (size_x, size_y, size_z).

        Example:
            >>> bbox = {"min": {"x": "100", "y": "200", "z": "0"}, "max": {"x": "150", "y": "250", "z": "50"}}
            >>> min_pt, max_pt, dobot_coords, bbox_size = MyClass.get_dobot_front_face_center_and_size(bbox)
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

    @staticmethod
    def calculate_scan_points(center_x: float, center_y: float,
                              center_z: float, distance: float = 0.5) -> List[Tuple[float, float, float]]:
        """
        Static method that calculates the four points around the plant.
        
        Args:
            center_x, center_y, center_z: Coordinates of the plant center
            distance: Distance from the center for the scan points

        Returns:
            List of tuples with the coordinates of the four points
        """
        points = [
            (center_x + distance, center_y, center_z),  # Right
            (center_x, center_y + distance, center_z),  # Forward
            (center_x - distance, center_y, center_z),  # Left
            (center_x, center_y - distance, center_z)   # Backward
        ]
        return points

    def usa_cam(self, system_pose: Pose, plants_number: int):
        """
        Metodo di test per utilizzare la telecamera ZED e processare l'ambiente circostante.
        Questo metodo inizializza la telecamera ZED, cattura immagini e mappe di profondità,
        filtra le piante dallo sfondo, segmenta le piante in cluster e salva i dati rilevanti.
        Inoltre, registra un video dell'ambiente per creare un file di point cloud (.ply).
        Args:
            pose (Pose): La posizione iniziale della telecamera ZED.
            plants_number (int): Il numero di piante da segmentare nell'immagine.
        """
        # init camera
        self.zed = zed_manager.zed_init(system_pose)
        image, depth_map, normal_map, point_cloud = zed_manager.get_zed_image(self.zed, save=True)

        mask = find_plant.filter_plants(image, save_mask=True)
        masks, bounding_boxes = find_plant.segment_plants(mask, plants_number)
        find_plant.save_clustered_image(image, bounding_boxes)

        for m in masks:
            _ = find_plant.get_3d_bbox(m, point_cloud)

        try:
            self.zed.close()
        except Exception:
            pass
        self.zed = None
        create_plc.record_and_save(plant_name='piantina1', frames=300)


if __name__ == "__main__":
    gui = MultiTerminalGUI()
    camera_handler = CameraHandler()
    test_pose = Pose()
    camera_handler.usa_cam(test_pose, plants_number=2)