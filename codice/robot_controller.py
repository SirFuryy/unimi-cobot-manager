# robot_controller.py

import re
import time

import sys
import os

import numpy as np

# Percorso assoluto alla directory contenente dobot_api.py
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_PATH)

from dobot_api import DobotApiDashboard, DobotApi, DobotApiMove, DobotApiFeedBack
from codice.multi_terminal_gui import MultiTerminalGUI

# Default IP and ports for the Dobot robot
IP_DOBOT = "192.168.5.1"
DASHBOARD_PORT = 29999
MOVE_PORT = 30003
FEED_PORT = 30005

def ConnessioneStandard(gui: MultiTerminalGUI):
    """
    Establish standard connections to the Dobot robot for dashboard, movement, and feedback.
    Returns: dashboard, move, feed, feedFour
    """
    try:
        print("Sto stabilendo la connessione con il robot...")
        dashboard = DobotApiDashboard(IP_DOBOT, DASHBOARD_PORT, gui)  # connection for info/control
        move = DobotApiMove(IP_DOBOT, MOVE_PORT, gui)               # connection for movement
        feed = DobotApi(IP_DOBOT, FEED_PORT, gui)                   # general API (unused in this context)
        feedFour = DobotApiFeedBack(IP_DOBOT, FEED_PORT, gui)       # feedback (200ms) connection
        gui.write_to_terminal(0, "Connessione al robot riuscita!")
        return dashboard, move, feed, feedFour
    except Exception as e:
        msg = f"Connessione al robot fallita: {str(e)}"
        gui.write_to_terminal(0, msg)
        raise e

def RunPoint(dashboard: DobotApiDashboard, move: DobotApiMove, gui: MultiTerminalGUI, target_joints: list):
    """
    Move the robot to the specified joint angles (target_joints list of 6 values).
    Blocks until the robot is within threshold of the target.
    """
    # Send move command
    move.JointMovJ(target_joints[0], target_joints[1], target_joints[2],
                   target_joints[3], target_joints[4], target_joints[5])
    time.sleep(0.1)  # short delay to initiate motion

    # Wait for the robot to reach the target positions (with some tolerance)
    i = 0
    while True:
        i += 1
        match = re.search(r'\{([^}]*)\}', dashboard.GetAngle())
        if match:
            values_str = match.group(1)
            current_angles = [float(v.strip()) for v in values_str.split(',')]
            # Check if all joints are within 1 degree of target
            arrived = True
            for idx in range(6):
                if abs(current_angles[idx] - target_joints[idx]) > 1.0:
                    arrived = False
                    break
            if arrived:
                gui.write_to_terminal(1, "Controller - Target raggiunto!")
                return  # target reached
        # Delay to prevent busy-wait
        time.sleep(0.5)
        if i > 20:
            gui.write_to_terminal(1, "Controller - Target non raggiunto entro 10 secondi")
 
def ottieni_joint(dashboard: DobotApiDashboard, gui: MultiTerminalGUI, coord):
    """
    Compute joint angles for the given target Cartesian coordinates (x,y,z,rx,ry,rz).
    coord can be a list/tuple of 6 values or a string "{x, y, z, rx, ry, rz}".
    Returns a list of 6 joint angles.
    """
    # Parse coordinates from string if necessary
    point_coord = _parse_target_coordinate(coord)

    # Inverse kinematics solution
    sol = dashboard.InverseSolution(point_coord[0], point_coord[1], point_coord[2],
                                    point_coord[3], point_coord[4], point_coord[5], 0, 0)
    if sol.startswith('-'):
        # Error in inverse solution, get current angles instead
        gui.write_to_terminal(1, "Controller - Errore nella soluzione inversa, utilizzo angoli attuali.")
        match = re.search(r'\{([^}]*)\}', dashboard.GetAngle())
        if match:
            values_str = match.group(1)
            return [float(v.strip()) for v in values_str.split(',')]
        else:
            gui.write_to_terminal(1, "Controller - Impossibile ottenere gli angoli correnti del robot")
            raise ValueError("Impossibile ottenere gli angoli correnti del robot")

    gui.write_to_terminal(1, f"Soluzione inversa trovata per la posizione {point_coord}. soluzione: {sol}")

    # Extract angles from solution string
    match = re.search(r'\{([^}]*)\}', sol)
    if not match:
        gui.write_to_terminal(1, "Controller - Soluzione inversa non valida")
        raise ValueError("Soluzione inversa non valida")
    values_str = match.group(1)
    joint_angles = [float(v.strip()) for v in values_str.split(',')]
    gui.write_to_terminal(1, f"Angoli calcolati: {joint_angles}")
    return joint_angles

def enable(dashboard: DobotApiDashboard):
    """
    Enable the robot (put it in enabled state).
    """
    dashboard.EnableRobot()

def raggiungi_punto(dashboard: DobotApiDashboard, move: DobotApiMove, gui: MultiTerminalGUI, coord):
    """
    Move the robot to reach a specific Cartesian point (coord).
    Coord can be string, list, or tuple as in ottieni_joint.
    Performs checks and uses RunPoint to execute move.
    """
    
    # Parse target coordinates
    point_coord = _parse_target_coordinate(coord)

    # If the Y coordinate is out of safe range, move in intermediate step
    if not position_reachable(coord):
        gui.write_to_terminal(1, "Controller - Raggiungi punto segnala un errore: posizione non raggiungibile")
        return

    # Get current pose of robot
    match = re.search(r'\{([^}]*)\}', dashboard.GetPose())
    if match:
        values_str = match.group(1)
        current_pos = [float(v.strip()) for v in values_str.split(',')]
        # If difference is small, skip move
        if abs(point_coord[0] - current_pos[0]) < 30 and abs(point_coord[1] - current_pos[1]) < 30 and abs(point_coord[2] - current_pos[2]) < 30:
            gui.write_to_terminal(1, "Controller - Differenza minima della posizione, non eseguo movimento.")
            return

    # Compute joint angles for target
    joints = ottieni_joint(dashboard, gui, coord)
    # Move robot to target
    RunPoint(dashboard, move, gui, joints)
    
def get_current_pose(dashboard: DobotApiDashboard) -> list[float]:
    """
    Get the current Cartesian pose of the robot as a list of floats [x, y, z, rx, ry, rz].
    """
    match = re.search(r'\{([^}]*)\}', dashboard.GetPose())
    if match:
        values_str = match.group(1)
        current_pose = [float(v.strip()) for v in values_str.split(',')]
        return current_pose
    else:
        raise ValueError("Impossibile ottenere la posa corrente del robot")

def position_reachable(coord: list[float] | tuple[float] | str) -> bool:

    point_coord = _parse_target_coordinate(coord)

    point = np.power(point_coord[0],2) + np.power(point_coord[1],2) + np.power((point_coord[2]),2)
    return point <= np.power(900, 2)

def _parse_target_coordinate(coord: list[float] | tuple[float] | str) -> list[float]:
    if isinstance(coord, str):
        coord = coord.strip('{} ')
        point_coord = [float(x.strip()) for x in coord.split(',')]
    elif isinstance(coord, (list, tuple)):
        point_coord = [float(x) for x in coord]
    else:
        raise ValueError("Formato delle coordinate non corretto: deve essere str, list o tuple")
    return point_coord