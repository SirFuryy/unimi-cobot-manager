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