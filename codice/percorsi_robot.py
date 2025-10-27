import socket
import json
import time
import threading
from typing import Tuple, List

from pose_class import Pose
import camera_handler
import robot_controller
from multi_terminal_gui import MultiTerminalGUI


def start_scanning(pose: Pose, gui: MultiTerminalGUI, plant_name: str, frames_to_record: int = 300):
    """Avvia la scansione in background."""

    camera_handler.record_cam(pose, gui, plant_name, frames_to_record)

    gui.write_to_terminal(2, f"Percorsi - Scansione avviata per {plant_name} con {frames_to_record} fotogrammi.")

def scan_plant(bbox, plant_name: str, dashboard, move, gui: MultiTerminalGUI, frames_to_record: int = 300):
    """
    Esegue la scansione completa della piantina muovendosi nei quattro punti.
    
    Args:
        bbox: bounding box rigorosamente di tipo YOLO absolute (x_centro, y_centro, z_centro, larghezza, profondità, altezza con valori assoluti), altrimenti non funziona
        center_x, center_y, center_z: Coordinate del centro della piantina
        distance: Distanza dal centro per i punti di scansione
    """
    
    if bbox is None:
        gui.write_to_terminal(1, "Percorsi - Il bounding box è None.")
        return
    
    if bbox[2] < 0:   #Il braccio sarebbe sotto il piano di lavoro
        gui.write_to_terminal(1, "Percorsi - Coordinata Z della piantina non valida, valore negativo.")
        return
    
    if not robot_controller.position_reachable([bbox[0], bbox[1], bbox[5], -180.0000, 0.0000, 90.0000]):
        gui.write_to_terminal(1, "Percorsi - Posizione della piantina non raggiungibile.")
        return
    
    if bbox[0] == 0 or bbox[1] == 0:   #Siamo su uno degli assi
        gui.write_to_terminal(1, "Percorsi - Posizione della piantina non valida, si trova su uno degli assi.")
        return

    if bbox[0] > 0 and bbox[1] > 0:   #Primo quadrante
        movement_first_quadrant(bbox, plant_name, dashboard, move, gui, frames_to_record)
        return

    if bbox[0] < 0 and bbox[1] > 0:   #Secondo quadrante
        movement_second_quadrant(bbox, plant_name, dashboard, move, gui, frames_to_record)
        return

    if bbox[0] < 0 and bbox[1] < 0:   #Terzo quadrante
        gui.write_to_terminal(1, "Percorsi - Posizione della piantina nel terzo quadrante, movimenti non ancora implementati.")
        return

    if bbox[0] > 0 and bbox[1] < 0:   #Quarto quadrante
        gui.write_to_terminal(1, "Percorsi - Posizione della piantina nel quarto quadrante, movimenti non ancora implementati.")
        return

def movement_first_quadrant(bbox, plant_name: str, dashboard, move, gui: MultiTerminalGUI, frames_to_record: int = 300):
    """
    Esegue il movimento del braccio per la scansione della piantina nel primo quadrante.
    
    Args:
        bbox: bounding box rigorosamente di tipo YOLO absolute (x_centro, y_centro, z_centro, larghezza, profondità, altezza con valori assoluti), altrimenti non funziona
        center_x, center_y, center_z: Coordinate del centro della piantina
        distance: Distanza dal centro per i punti di scansione
    """
    
    print("Percorsi - Movimento nel primo quadrante.")
    
    center_z_max = [bbox[0], bbox[1], bbox[2]+bbox[5]/2]   #Prendo z max

    coord_top_vision_plant = [center_z_max[0], center_z_max[1], center_z_max[2]+350.0, -180.0000, 0.0000, 180.0000]
    
    # arriva al punto iniziale di scansione generale
    start_joints = [-105.0000, -46.0000, 86.0000, 29.0000, -90.0000, 168.0000]
    robot_controller.RunPoint(dashboard, move, gui, start_joints)
    
    # Avvia la scansione in background
    pose = Pose.crea_pose_from_coord(robot_controller.get_current_pose(dashboard))
    #threading.Thread(target=start_scanning, args=(pose, gui, plant_name, frames_to_record), daemon=True).start()
    
    # reach the top vision of the plant
    gui.write_to_terminal(1, "Pronto per raggiungere top.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant)
    print("alto fatto")
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione

    # move to first scanning point
    coord_right_vision_plant = [center_z_max[0], center_z_max[1]+240.0, center_z_max[2]+285.0, -141.0000, 0.0000, 180.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere fronte.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_right_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("fronte fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to second scanning point
    coord_front_vision_plant = [center_z_max[0]+214.0, center_z_max[1], center_z_max[2]+305.0, -151.0000, 0.0000, 90.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere destra.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_front_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("destra fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to third scanning point
    coord_left_vision_plant = [center_z_max[0], center_z_max[1]-246.0, center_z_max[2]+285.0, -141.0000, 0.0000, 0.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere dietro.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_left_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("dietro fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to fourth scanning point
    coord_back_vision_plant = [center_z_max[0]-243.0, center_z_max[1], center_z_max[2]+285.0, -141.0000, 0.0000, -90.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere sinistra.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_back_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("sinistra fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point
    
    # return to ambient high vision point
    robot_controller.RunPoint(dashboard, move, gui, start_joints)
    
    # TODO: calcolare i 5 punti di scansione. Il primo lo si calcola prendendo il centro della piantina, ponendo z massimo per la piantina e aggiungendo 35 cm per stare larhi. Poi farlo in diagonale di 60 gradi, prendendo z massimi e x e y rispettivamente massimi e minimi per i quattro altri punti
    
    # TODO: fare runpoint su quei punti nel mentre che la scannsione è già aprtita, bisogna capire quanto tempo ci mette la scansione e regolare i tempi
    
    # TODO: modificare le funzioni di robot controller per renderle più efficaci e togliere quella cagata di get angle se non è raggiungibile    
   
    
def movement_second_quadrant(bbox, plant_name: str, dashboard, move, gui: MultiTerminalGUI, frames_to_record: int = 300):
    """
    Esegue il movimento del braccio per la scansione della piantina nel primo quadrante.
    
    Args:
        bbox: bounding box rigorosamente di tipo YOLO absolute (x_centro, y_centro, z_centro, larghezza, profondità, altezza con valori assoluti), altrimenti non funziona
        center_x, center_y, center_z: Coordinate del centro della piantina
        distance: Distanza dal centro per i punti di scansione
    """
    print("Percorsi - Movimento nel secondo quadrante.")
    center_z_max = [bbox[0], bbox[1], bbox[2]+bbox[5]/2]   #Prendo z max

    coord_top_vision_plant = [center_z_max[0], center_z_max[1], center_z_max[2]+350.0, -180.0000, 0.0000, 90.0000]

    # arriva al punto iniziale di scansione generale
    start_joints = [103.0000, 39.0000, -86.0000, -24.0000, 88.0000, 195.0000]
    robot_controller.RunPoint(dashboard, move, gui, start_joints)
    
    # Avvia la scansione in background
    pose = Pose.crea_pose_from_coord(robot_controller.get_current_pose(dashboard))
    threading.Thread(target=start_scanning, args=(pose, gui, plant_name, frames_to_record), daemon=True).start()
    
    # reach the top vision of the plant
    gui.write_to_terminal(1, "Pronto per raggiungere top.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant)
    print("alto fatto")
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione

    # move to first scanning point
    coord_right_vision_plant = [center_z_max[0], center_z_max[1]+240.0, center_z_max[2]+285.0, -141.0000, 0.0000, 180.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere fronte.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_right_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("fronte fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to second scanning point
    coord_front_vision_plant = [center_z_max[0]+214.0, center_z_max[1], center_z_max[2]+305.0, -151.0000, 0.0000, 90.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere destra.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_front_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("destra fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to third scanning point
    coord_left_vision_plant = [center_z_max[0], center_z_max[1]-246.0, center_z_max[2]+285.0, -141.0000, 0.0000, 0.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere dietro.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_left_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("dietro fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point

    # move to fourth scanning point
    coord_back_vision_plant = [center_z_max[0]-243.0, center_z_max[1], center_z_max[2]+285.0, -141.0000, 0.0000, -90.0000]
    gui.write_to_terminal(1, "Pronto per raggiungere sinistra.")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_back_vision_plant)
    time.sleep(0.1)  # Attendi un secondo per permettere la scansione
    print("sinistra fatto")
    robot_controller.raggiungi_punto(dashboard, move, gui, coord_top_vision_plant) #return to top vision point
    
    # return to ambient high vision point
    robot_controller.RunPoint(dashboard, move, gui, start_joints)
