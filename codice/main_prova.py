# prova_compl.py

import threading
import tkinter as tk
from transforms3d.euler import euler2quat

import camera_handler_mock as camera_handler
#import camera_handler
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

    # Optional: print feedback to console
    thread_print = threading.Thread(target=feed_thread.stampaFeed, args=(gui,), name="PrintFeedbackThread")
    thread_print.daemon = True
    thread_print.start()

    # Camera response handler
    def handle_response(response):
        print("Response received:", response)
        min_pt, max_pt, coord_face, bbox_size = camera_handler.get_dobot_front_face_center_and_size(response)
        # Update GUI with new values (thread-safe call)
        gui.write_to_terminal(2, f"--------\nMin Point: {min_pt} - Max Point: {max_pt}")
        gui.write_to_terminal(2, f"Dobot Coords: {coord_face} - BBox Size: {bbox_size}")
        # Move robot to the calculated point
        robot_controller.raggiungi_punto(dashboard, move, gui, coord_face)

    # Start listening thread for camera responses
    #CAMERA_LISTEN_IP = "192.168.5.2"
    #CAMERA_LISTEN_PORT = 5005
    #camera_handler.start_listening_thread(CAMERA_LISTEN_IP, CAMERA_LISTEN_PORT, handle_response)

    # Prepare initial pose to send to camera
    CORD = [-143.7374, 69.6845, 646.8096, 93.9973, -0.0089, -179.7939]
    pose = Pose()
    pose.position.x = CORD[0]
    pose.position.y = CORD[1]
    pose.position.z = CORD[2]
    quat = euler2quat(CORD[3], CORD[4], CORD[5], axes='sxyz')
    pose.orientation.x = quat[1]
    pose.orientation.y = quat[2]
    pose.orientation.z = quat[3]
    pose.orientation.w = quat[0]
    print("Coordinate salvate")
    gui.write_to_terminal(0, f"Coordinate salvate: {CORD}")

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
    initial_joints = [-90.0, -22.0000, 43.0000, 52.0000, -90.0, 180.0]
    robot_controller.RunPoint(dashboard, move, gui, initial_joints)

    camera_handler.start_cam(pose, gui)
    camera_handler.get_image_cam(gui, True)

    # Send pose to camera server
    #SERVER_IP = "192.168.5.4"
    #SERVER_PORT = 5005
    #camera_handler.send_pose_to_socket(SERVER_IP, SERVER_PORT, gui, pose)



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
    
    # Esempio: aggiungi un pulsante nella colonna controlli
    start_button = tk.Button(
        gui.control_frame,
        text="Avvia Programma",
        command= lambda: avvia_programma(gui),
        width=20
    )
    gui.add_control(start_button)

    stop_button = tk.Button(
        gui.control_frame,
        text="Chiudi Programma",
        command=gui.root.quit,
        width=20
    )
    gui.add_control(stop_button)

    # Start the GUI event loop
    gui.run()

    # On exit, disable the robot
    dashboard.DisableRobot()
    print("Disabilitazione completata :)")

if __name__ == "__main__":
    main()
