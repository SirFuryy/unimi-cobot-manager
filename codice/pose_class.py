from transforms3d.euler import euler2quat

class Pose:
    """Class representing a 3D pose with position and orientation."""
    class Position:
        def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
            self.x = x
            self.y = y
            self.z = z

    class Orientation:
        def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
            self.x = x
            self.y = y
            self.z = z
            self.w = w

    def __init__(self):
        self.position = Pose.Position()
        self.orientation = Pose.Orientation()

    @staticmethod
    def crea_pose_from_coord(coord: list[float]):
        """Create a Pose in quaternion from a list of 6 eulser coordinates [x, y, z, rx, ry, rz]."""
        if len(coord) != 6:
            raise ValueError("Coordinate list must have exactly 6 elements.")
        
        pose = Pose()
        pose.position.x = coord[0]
        pose.position.y = coord[1]
        pose.position.z = coord[2]
        
        quat = euler2quat(coord[3], coord[4], coord[5], axes='sxyz')
        pose.orientation.w = quat[0]
        pose.orientation.x = quat[1]
        pose.orientation.y = quat[2]
        pose.orientation.z = quat[3]
        return pose