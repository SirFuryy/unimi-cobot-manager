# pyzed_mock.py
"""
Mock module per pyzed.sl quando le DLL native non sono disponibili.
Permette di continuare lo sviluppo senza hardware ZED collegato.
"""
import numpy as np
from enum import Enum

class ERROR_CODE(Enum):
    SUCCESS = 0
    FAILURE = 1
    NO_GPU_COMPATIBLE = 2
    NOT_ENOUGH_GPU_MEMORY = 3
    CAMERA_NOT_DETECTED = 4
    SENSORS_NOT_INITIALIZED = 5
    INVALID_RESOLUTION = 6
    LOW_USB_BANDWIDTH = 7
    CALIBRATION_FILE_NOT_AVAILABLE = 8
    INVALID_CALIBRATION_FILE = 9
    INVALID_SVO_FILE = 10
    SVO_RECORDING_ERROR = 11
    SVO_UNSUPPORTED_COMPRESSION = 12
    END_OF_SVOFILE_REACHED = 13
    INVALID_COORDINATE_SYSTEM = 14
    INVALID_FIRMWARE = 15
    INVALID_FUNCTION_PARAMETERS = 16
    CUDA_ERROR = 17
    CAMERA_NOT_INITIALIZED = 18
    NVIDIA_DRIVER_OUT_OF_DATE = 19
    INVALID_FUNCTION_CALL = 20
    CORRUPTED_SDK_INSTALLATION = 21
    INCOMPATIBLE_SDK_VERSION = 22
    INVALID_AREA_FILE = 23
    INCOMPATIBLE_AREA_FILE = 24
    CAMERA_FAILED_TO_SETUP = 25
    CAMERA_DETECTION_ISSUE = 26
    CANNOT_START_CAMERA_STREAM = 27
    NO_FRAMES_TIMEOUT = 28
    INVALID_INSTANCES = 29
    LAST = 30

class RESOLUTION(Enum):
    HD2K = 0
    HD1080 = 1
    HD720 = 2
    VGA = 3
    LAST = 4

class DEPTH_MODE(Enum):
    NONE = 0
    PERFORMANCE = 1
    QUALITY = 2
    ULTRA = 3
    NEURAL = 4
    NEURAL_PLUS = 5
    LAST = 6

class UNIT(Enum):
    MILLIMETER = 0
    CENTIMETER = 1
    METER = 2
    INCH = 3
    FOOT = 4
    LAST = 5

class COORDINATE_SYSTEM(Enum):
    IMAGE = 0
    LEFT_HANDED_Y_UP = 1
    RIGHT_HANDED_Y_UP = 2
    RIGHT_HANDED_Z_UP = 3
    LEFT_HANDED_Z_UP = 4
    RIGHT_HANDED_Z_UP_X_FWD = 5
    LAST = 6

class VIEW(Enum):
    LEFT = 0
    RIGHT = 1
    LEFT_GRAY = 2
    RIGHT_GRAY = 3
    LEFT_UNRECTIFIED = 4
    RIGHT_UNRECTIFIED = 5
    LEFT_UNRECTIFIED_GRAY = 6
    RIGHT_UNRECTIFIED_GRAY = 7
    SIDE_BY_SIDE = 8
    DEPTH = 9
    CONFIDENCE = 10
    NORMALS = 11
    DEPTH_RIGHT = 12
    NORMALS_RIGHT = 13
    LAST = 14

class MEASURE(Enum):
    DISPARITY = 0
    DEPTH = 1
    CONFIDENCE = 2
    XYZ = 3
    XYZRGBA = 4
    XYZBGRA = 5
    XYZARGB = 6
    XYZABGR = 7
    NORMALS = 8
    DISPARITY_RIGHT = 9
    DEPTH_RIGHT = 10
    XYZ_RIGHT = 11
    XYZRGBA_RIGHT = 12
    XYZBGRA_RIGHT = 13
    XYZARGB_RIGHT = 14
    XYZABGR_RIGHT = 15
    NORMALS_RIGHT = 16
    DEPTH_U16_MM = 17
    DEPTH_U16_MM_RIGHT = 18
    LAST = 19

class MAT_TYPE(Enum):
    F32_C1 = 0
    F32_C2 = 1
    F32_C3 = 2
    F32_C4 = 3
    U8_C1 = 4
    U8_C2 = 5
    U8_C3 = 6
    U8_C4 = 7
    U16_C1 = 8
    S8_C4 = 9
    LAST = 10

class InitParameters:
    def __init__(self):
        self.camera_resolution = RESOLUTION.HD720
        self.camera_fps = 30
        self.camera_linux_id = 0
        self.svo_real_time_mode = False
        self.depth_mode = DEPTH_MODE.PERFORMANCE
        self.coordinate_units = UNIT.MILLIMETER
        self.coordinate_system = COORDINATE_SYSTEM.IMAGE
        self.sdk_verbose = False
        self.sdk_gpu_id = -1
        self.depth_minimum_distance = -1
        self.depth_maximum_distance = -1
        self.camera_disable_self_calib = False
        self.camera_image_flip = False
        self.enable_right_side_measure = False
        self.svo_input_filename = ""
        self.input_type = INPUT_TYPE.USB

class RuntimeParameters:
    def __init__(self):
        self.sensing_mode = 0
        self.enable_depth = True
        self.enable_point_cloud = True
        self.measure3D_reference_frame = REFERENCE_FRAME.CAMERA

class Mat:
    def __init__(self):
        self.data_type = MAT_TYPE.F32_C1
        self._data = None
        
    def alloc(self, width, height, mat_type):
        self.data_type = mat_type
        if mat_type == MAT_TYPE.F32_C4:
            self._data = np.zeros((height, width, 4), dtype=np.float32)
        elif mat_type == MAT_TYPE.U8_C4:
            self._data = np.zeros((height, width, 4), dtype=np.uint8)
        elif mat_type == MAT_TYPE.F32_C1:
            self._data = np.zeros((height, width), dtype=np.float32)
        else:
            self._data = np.zeros((height, width, 3), dtype=np.uint8)
        return ERROR_CODE.SUCCESS
    
    def get_data(self):
        if self._data is not None:
            return self._data
        return np.zeros((480, 640, 3), dtype=np.uint8)  # Default mock data

class Camera:
    def __init__(self):
        self.is_opened = False
        
    def open(self, init_params=None):
        print("[MOCK] Camera.open() - Simulando apertura camera ZED")
        self.is_opened = True
        return ERROR_CODE.SUCCESS
    
    def grab(self, runtime_params=None):
        if not self.is_opened:
            return ERROR_CODE.CAMERA_NOT_INITIALIZED
        # Simula frame capture
        return ERROR_CODE.SUCCESS
    
    def retrieve_image(self, mat, view, mem=None, resolution=None):
        if not self.is_opened:
            return ERROR_CODE.CAMERA_NOT_INITIALIZED
        print(f"[MOCK] retrieve_image called with view: {view}")
        # Genera immagine mock colorata
        if view == VIEW.LEFT:
            # Immagine RGB mock
            mock_img = np.random.randint(0, 255, (480, 640, 4), dtype=np.uint8)
            mock_img[:, :, 3] = 255  # Alpha channel
            mat._data = mock_img
        return ERROR_CODE.SUCCESS
    
    def retrieve_measure(self, mat, measure, mem=None, resolution=None):
        if not self.is_opened:
            return ERROR_CODE.CAMERA_NOT_INITIALIZED
        print(f"[MOCK] retrieve_measure called with measure: {measure}")
        if measure == MEASURE.XYZ:
            # Point cloud mock (X, Y, Z, W)
            mock_pc = np.random.uniform(-1.0, 1.0, (480, 640, 4)).astype(np.float32)
            mat._data = mock_pc
        elif measure == MEASURE.DEPTH:
            # Depth map mock
            mock_depth = np.random.uniform(0.5, 5.0, (480, 640)).astype(np.float32)
            mat._data = mock_depth
        elif measure == MEASURE.NORMALS:
            # Normal map mock
            mock_normals = np.random.uniform(-1.0, 1.0, (480, 640, 4)).astype(np.float32)
            mat._data = mock_normals
        return ERROR_CODE.SUCCESS
    
    def close(self):
        print("[MOCK] Camera.close() - Chiusura camera simulata")
        self.is_opened = False
    
    def is_opened(self):
        return self.is_opened

# Aggiungi altri enum/classi se necessari
class REFERENCE_FRAME(Enum):
    WORLD = 0
    CAMERA = 1

class INPUT_TYPE(Enum):
    USB = 0
    SVO = 1
    STREAM = 2

print("[MOCK MODULE] pyzed_mock caricato - simulazione ZED SDK attiva")