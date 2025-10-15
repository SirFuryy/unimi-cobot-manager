import socket
import json
import time
import threading
from typing import Tuple, List

import camera_handler
from codice import robot_controller
from multi_terminal_gui import MultiTerminalGUI


def start_scanning(gui: MultiTerminalGUI, plant_name: str, frames_to_record: int = 300):
    """Avvia la scansione in background."""

    camera_handler.record_cam(gui, plant_name, frames_to_record)

    gui.write_to_terminal(2, f"Scansione avviata per {plant_name} con {frames_to_record} fotogrammi.")

def scan_plant(posizione_piantina, bbox, gui: MultiTerminalGUI, plant_name: str, frames_to_record: int = 300):
    """
    Esegue la scansione completa della piantina muovendosi nei quattro punti.
    
    Args:
        center_x, center_y, center_z: Coordinate del centro della piantina
        distance: Distanza dal centro per i punti di scansione
    """
    
    if posizione_piantina is None:
        gui.write_to_terminal(2, "Posizione della piantina non trovata.")
        return
    
    if posizione_piantina[2] < 0:   #Il braccio sarebbe sotto il piano di lavoro
        gui.write_to_terminal(2, "Posizione della piantina non valida.")
        return
    
    if not robot_controller.position_reachable(posizione_piantina):
        gui.write_to_terminal(2, "Posizione della piantina non raggiungibile.")
        return
    
    if posizione_piantina[0] == 0 or posizione_piantina[1] == 0:   #Siamo su uno degli assi
        gui.write_to_terminal(2, "Posizione della piantina non valida.")
        return
    
    if posizione_piantina[0] > 0 & posizione_piantina[1] > 0:   #Primo quadrante
        movement_first_quadrant(posizione_piantina, bbox, gui, plant_name)
        return
    
    if posizione_piantina[0] < 0 & posizione_piantina[1] > 0:   #Secondo quadrante
        return

    if posizione_piantina[0] < 0 & posizione_piantina[1] < 0:   #Terzo quadrante
        return

    if posizione_piantina[0] > 0 & posizione_piantina[1] < 0:   #Quarto quadrante
        return
    
    
    # Avvia la scansione in background
    threading.Thread(target=start_scanning, args=(gui, plant_name, frames_to_record), daemon=True).start()

def movement_first_quadrant(bbox, gui: MultiTerminalGUI, plant_name: str):
    """
    Esegue il movimento del braccio per la scansione della piantina nel primo quadrante.
    
    Args:
        bbox: bounding box rigorosamente di tipo COCO, altrimenti non funziona
        center_x, center_y, center_z: Coordinate del centro della piantina
        distance: Distanza dal centro per i punti di scansione
    """
    
    center_z_max = [bbox[0], bbox[1], bbox[5]]   #Prendo z max

    coord_high_vision = [center_z_max[0], center_z_max[1], center_z_max[2], ]
    # TODO: calcolare i 5 punti di scansione. Il primo lo si calcola prendendo il centro della piantina, ponendo z massimo per la piantina e aggiungendo 35 cm per stare larhi. Poi farlo in diagonale di 60 gradi, prendendo z massimi e x e y rispettivamente massimi e minimi per i quattro altri punti
    
    # TODO: verificare che i punti siano raggiungibili, altrimenti avvisare l'utente e saltare quel punto
    
    # TODO: fare runpoint su quei punti nel mentre che la scannsione è già aprtita, bisogna capire quanto tempo ci mette la scansione e regolare i tempi
    
    # TODO: modificare le funzioni di robot controller per renderle più efficaci e togliere quella cagata di get angle se non è raggiungibile
    
    # TODO: la funzione position reachable
    
    
    
    
    distance = 30  # Distanza dal centro per i punti di scansione
    
    # Calcola le coordinate dei quattro punti di scansione
    points = [
        (posizione_piantina[0] - distance, posizione_piantina[1] + distance, posizione_piantina[2]),  # Punto in alto a sinistra
        (posizione_piantina[0] + distance, posizione_piantina[1] + distance, posizione_piantina[2]),  # Punto in alto a destra
        (posizione_piantina[0] + distance, posizione_piantina[1] - distance, posizione_piantina[2]),  # Punto in basso a destra
        (posizione_piantina[0] - distance, posizione_piantina[1] - distance, posizione_piantina[2])   # Punto in basso a sinistra
    ]
    
    # Salva la posa originale del robot
    original_pose = robot_controller.get_current_pose()
    
    for idx, point in enumerate(points):
        if not robot_controller.position_reachable(point):
            gui.write_to_terminal(2, f"Punto di scansione {idx+1} non raggiungibile: {point}")
            continue
        
        gui.write_to_terminal(2, f"Spostamento al punto di scansione {idx+1}: {point}")
        
        success = robot_controller.move_to_position(point)
        if not success:
            gui.write_to_terminal(2, f"Errore nello spostamento al punto di scansione {idx+1}.")
            continue
        
        time.sleep(1)  # Attendi un secondo per stabilizzare la posizione
        
        # Avvia la scansione in background
        threading.Thread(target=start_scanning, args=(gui, plant_name), daemon=True).start()
        
        time.sleep(5)  # Attendi che la scansione sia completata (regola questo valore secondo necessità)
    
    # Torna alla posa