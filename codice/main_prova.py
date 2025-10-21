# prova_compl.py

import threading
import time
import tkinter as tk
from transforms3d.euler import euler2quat
import numpy as np

#import camera_handler_mock as camera_handler
import camera_handler
import percorsi_robot
import robot_controller
import feed_thread
from codice.multi_terminal_gui import MultiTerminalGUI
from pose_class import Pose

global dashboard, move, feed, feedFour

def avvia_programma(gui: MultiTerminalGUI):
    global dashboard, move, feed, feedFour
    
    # Initialize robot connection
    dashboard, move, feed, feedFour = robot_controller.ConnessioneStandard(gui)

    # Start feedback threads
    thread_feed = threading.Thread(target=feed_thread.GetFeed200ms, args=(feedFour,), name="FeedbackThread")
    thread_feed.daemon = True
    thread_feed.start()

    thread_error = threading.Thread(target=feed_thread.ClearRobotError, args=(dashboard, gui), name="ErrorThread")
    thread_error.daemon = True
    thread_error.start()

    # Prepare initial pose to send to camera
    CORD_RIPOSO = [142.000000, 19.500000, 314.800000, 180.000000, 0.000000, -180.000000]
    pose = Pose()
    pose.position.x = CORD_RIPOSO[0]/1000
    pose.position.y = CORD_RIPOSO[1]/1000
    pose.position.z = CORD_RIPOSO[2]/1000
    angles_radiant = np.radians([CORD_RIPOSO[3], CORD_RIPOSO[4], CORD_RIPOSO[5]])
    quat = euler2quat(angles_radiant[0], angles_radiant[1], angles_radiant[2], axes='sxyz')
    pose.orientation.x = quat[1]
    pose.orientation.y = quat[2]
    pose.orientation.z = quat[3]
    pose.orientation.w = quat[0]
    print("Coordinate salvate")
    gui.write_to_terminal(0, f"Coordinate salvate: {CORD_RIPOSO}")

    # Enable robot and set speed
    print("Inizio abilitazione...")
    gui.write_to_terminal(0, "Inizio abilitazione...")
    robot_controller.enable(dashboard)
    print("Abilitazione completata :)")
    gui.write_to_terminal(0, "Abilitazione completata :)")
    try:
        dashboard.SpeedFactor(40)
    except Exception:
        pass

    # Move robot to initial position (example)
    initial_joints = [-90.0000, -75.0000, 138.0000, 27.0000, -90.0000, 180.0000]
    robot_controller.RunPoint(dashboard, move, gui, initial_joints)
    
    #camera_handler.start_cam(pose, gui)   maybe poco utile
    
    gui.set_status("READY", "yellow")

def find_plant(gui: MultiTerminalGUI):
    global dashboard, move, feed, feedFour
    
    
    # vecchia high vision joint = [-90.0000, -46.0000, 86.0000, 28.0000, -90.0000, 180.0000]
    # nuovi [-105.0000, -46.0000, 86.0000, 29.0000, -90.0000, 168.0000]
    
    # vecchia high vision cartesian = [-143.0000, 67.2000, 662.3500, 158.0000, 0.0000, -179.3000]
    # nuovi [-120.0000, 102.0000, 659.0000, 160.0000, 3.0000, 175.0000]

    high_vision_joints = [-105.0000, -46.0000, 86.0000, 29.0000, -90.0000, 168.0000]
    HIGH_VISION_POSE = [-120.0000, 102.0000, 659.0000, 160.0000, 3.0000, 175.0000]
    robot_controller.RunPoint(dashboard, move, gui, high_vision_joints)
    
    pose = Pose()
    pose.position.x = HIGH_VISION_POSE[0]/1000
    pose.position.y = HIGH_VISION_POSE[1]/1000
    pose.position.z = HIGH_VISION_POSE[2]/1000
    angles_radiant = np.radians([HIGH_VISION_POSE[3], HIGH_VISION_POSE[4], HIGH_VISION_POSE[5]])
    quat = euler2quat(angles_radiant[0], angles_radiant[1], angles_radiant[2], axes='sxyz')
    pose.orientation.x = quat[1]
    pose.orientation.y = quat[2]
    pose.orientation.z = quat[3]
    pose.orientation.w = quat[0]
    
    camera_handler.get_image_cam(pose, gui, True)
    
    plants_number = 1
    
    list_of_plants = camera_handler.scan_and_find_plants(pose, plants_number, gui, bbox_type="y")

    gui.write_to_terminal(0, f"Main - Piante trovate: {list_of_plants}")

    return list_of_plants
    
def scan_and_record(plant_position: list, plant_name: str, gui: MultiTerminalGUI):
    global dashboard, move, feed, feedFour
    
    # arriva al punto iniziale di scansione
    start_joints = [-105.0000, -46.0000, 86.0000, 29.0000, -90.0000, 168.0000]
    robot_controller.RunPoint(dashboard, move, gui, start_joints)
    
    plant_position = [300.0, 300.0, 50.0, 100.0, 100.0, 100.0]   #Per test, da togliere
    percorsi_robot.scan_plant(plant_position, plant_name, dashboard, move, gui, frames_to_record=300)
    
    #camera_handler.record_cam(pose, gui, plant_name, frames=300)
    
    gui.write_to_terminal(0, f"Main - Scan and record for {plant_name} completed.")

def main():
    terminal_names = [
        "Stato_robot",
        "Stato_calcoli", 
        "Risposte_camera",
        "Invio_comandi",
        "Messaggi_errore",
        "Feedback"
    ]
    
    # Inizializza GUI
    gui = MultiTerminalGUI(terminal_titles=terminal_names)
    
    t = threading.Thread(target=avvia_programma, args=(gui,), daemon=True)
    
    # Button to start the robot
    start_button = gui._create_styled_button(
        gui.control_container,
        text="▶️ AVVIA PROGRAMMA",
        #command=lambda: avvia_programma(gui),
        command=lambda: t.start(),
        width=20,
        color_type='success'
    )
    gui.add_control(start_button)
    
    # Button to find plants
    # Separatore
    separator = tk.Frame(gui.control_container, height=2, bg=gui.colors['border'])
    gui.add_control(separator)

    # Campo di input stilizzato per il valore della scansione
    input_frame = tk.Frame(gui.control_container, bg=gui.colors['bg_secondary'])
    gui.add_control(input_frame)
    
    scan_label = tk.Label(
        input_frame, 
        text="PIANTE DA SCANSIONARE",
        font=("Segoe UI", 9),
        bg=gui.colors['bg_secondary'],
        fg=gui.colors['text_secondary']
    )
    scan_label.pack(pady=(10, 5))
    
    scan_entry = tk.Entry(
        input_frame, 
        width=25,
        font=("Segoe UI", 10),
        bg=gui.colors['bg_main'],
        fg=gui.colors['text_primary'],
        insertbackground=gui.colors['text_primary'],
        bd=0,
        relief="flat"
    )
    scan_entry.pack(pady=5, ipady=8, padx=2)
    
    val = 0

    # Funzione che esegue la scansione in background usando il valore inserito
    def start_scan():
        gui.set_status("SCANNING...", "green")
        val = scan_entry.get().strip()
        if not val:
            gui.write_to_terminal(4, "[Scan] ⚠️ Valore vuoto: inserire un valore prima di eseguire la scansione")
            gui.set_status("READY", "yellow")
            return
        try:
            numeric_val = float(val)
            n = max(0, int(numeric_val))  # Limita al minimo 0 pulsanti
            n = min(n, 10)  # Limita a massimo 10 pulsanti
            if n == 0:
                gui.write_to_terminal(4, "[Scan] ℹ️ Nessun pulsante da generare (valore 0)")
                gui.set_status("READY", "yellow")
                return

            def scan_task():
                list_of_plants = find_plant(gui)    #Restituisce un dizionario con punti estremi delle varie boundyng box
                
                # codice per identificare il punto centrale della piantina
                #restituisce una lista di liste, dove ogni lista interna è l'insieme delle coordinate delle posizioni delle piantine
                
                # il codice poi dovrà eseguire la scansione e la registrazione per ogni piantina

                if not list_of_plants:
                    gui.write_to_terminal(4, "[Scan] ❌ Nessuna pianta trovata dalla camera")
                    gui.set_status("READY", "yellow")
                    return
                
                def create_buttons():
                    # Rimuove eventuali pulsanti precedenti
                    if hasattr(gui, 'scan_buttons_frame') and gui.scan_buttons_frame.winfo_exists():
                        try:
                            gui.scan_buttons_frame.destroy()
                        except Exception:
                            pass

                    # Frame per i pulsanti di scansione con stile
                    gui.scan_buttons_frame = tk.Frame(
                        gui.control_container,
                        bg=gui.colors['bg_main'],
                        highlightbackground=gui.colors['border'],
                        highlightthickness=1
                    )
                    gui.scan_buttons_frame.pack(fill=tk.X, pady=10, padx=2)
                    
                    # Titolo sezione
                    scan_title = tk.Label(
                        gui.scan_buttons_frame,
                        text="🌱 SCAN RESULTS",
                        font=("Segoe UI", 9, "bold"),
                        bg=gui.colors['bg_main'],
                        fg=gui.colors['accent_1']
                    )
                    scan_title.pack(pady=5)

                    gui.scan_handlers = {}
                    for i in range(n):
                        def make_handler(idx):
                            def handler(idx=idx):
                                # da cambiare il parametro della funzione di scansione
                                scan_and_record(list_of_plants[idx], f"plant_{idx+1}", gui)
                                gui.write_to_terminal(1, f"[Scan] ✅ Pianta {idx+1} selezionata")
                                # Qui si possono eseguire azioni diverse per idx
                            return handler

                        btn = tk.Button(
                            gui.scan_buttons_frame,
                            text=f"🌿 Pianta {i+1}",
                            command=make_handler(i),
                            width=18,
                            font=("Segoe UI", 9),
                            bg=gui.colors['accent_1'],
                            fg='#ffffff',
                            activebackground=gui._lighten_color(gui.colors['accent_1']),
                            bd=0,
                            padx=5,
                            pady=5,
                            cursor="hand2"
                        )
                        if i == n - 1:
                            btn.pack(fill=tk.X, padx=10, pady=(3, 10))
                        else:
                            btn.pack(fill=tk.X, padx=10, pady=3)
                        
                        # Effetti hover
                        def on_enter(e, btn=btn):
                            btn['background'] = gui._lighten_color(gui.colors['accent_1'])
                        def on_leave(e, btn=btn):
                            btn['background'] = gui.colors['accent_1']
                        
                        btn.bind("<Enter>", on_enter)
                        btn.bind("<Leave>", on_leave)
                        gui.scan_handlers[i] = make_handler(i)

                # Creazione dei widget deve avvenire nel thread principale
                gui.root.after(0, create_buttons)

            threading.Thread(target=scan_task, daemon=True).start()
            gui.set_status("READY", "yellow")
        except ValueError:
            gui.write_to_terminal(4, f"[Scan] ❌ Valore non valido: '{val}' (serve un numero)")
            gui.set_status("ERROR", "red")
            return

    # Bottone per lanciare la scansione con stile
    scan_button = gui._create_styled_button(
        gui.control_container,
        text="📡 ESEGUI SCANSIONE",
        command=start_scan,
        width=20,
        color_type='primary'
    )
    gui.add_control(scan_button)

    # Start the GUI event loop
    gui.run()

    # On exit, disable the robot
    dashboard.DisableRobot()
    print("Disabilitazione completata :)")

if __name__ == "__main__":
    main()
