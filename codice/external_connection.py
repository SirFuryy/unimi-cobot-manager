import socket
import json
import time
import threading

from multi_terminal_gui import MultiTerminalGUI
from pose_class import Pose

def send_pose_to_socket(ip: str, port: int, gui: MultiTerminalGUI, pose: Pose):
    """
    Send a Pose to the server at the given IP and port via TCP socket.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((ip, port))
            gui.write_to_terminal(0, f"Connected to server at {ip}:{port}")

            pose_msg = {
                "position": {
                    "x": pose.position.x,
                    "y": pose.position.y,
                    "z": pose.position.z
                },
                "orientation": {
                    "x": pose.orientation.x,
                    "y": pose.orientation.y,
                    "z": pose.orientation.z,
                    "w": pose.orientation.w
                }
            }

            client_socket.sendall(json.dumps(pose_msg).encode('utf-8'))
            gui.write_to_terminal(0, "Pose message sent:", json.dumps(pose_msg, indent=2))
    except Exception as e:
        gui.write_to_terminal(4, "Error sending pose:", e)

def aspetta_risposta(ip: str, port: int, gui: MultiTerminalGUI):
    """
    Wait for a JSON response on the given IP and port.
    Listens for a connection, then receives data until no more arrives.
    Returns the decoded JSON object or None if no data.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serversocket:
        try:
            serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serversocket.bind((ip, port))
            serversocket.listen(1)
            gui.write_to_terminal(0, f"Waiting for connection on {ip}:{port}...")

            connection, address = serversocket.accept()
            gui.write_to_terminal(0, f"Connection established with {address}")

            connection.settimeout(0.1)  # non-blocking read with short timeout

            last_data = None
            last_time = time.time()

            while True:
                try:
                    chunk = connection.recv(1024)
                    if chunk:
                        last_data = chunk
                        last_time = time.time()
                    else:
                        # connection closed by client
                        break
                except socket.timeout:
                    # no data at the moment
                    if time.time() - last_time > 0.2:  # no new data for 200 ms
                        break
                    continue

            if last_data:
                return json.loads(last_data.decode('utf-8'))
            else:
                return None

        except Exception as e:
            gui.write_to_terminal(4, "Error receiving response:", e)
            return None
        
def _response_loop(ip: str, port: int, callback):
    """
    Internal loop running in a thread to listen for responses continuously.
    Calls the callback with the JSON response when received.
    """
    while True:
        response = aspetta_risposta(ip, port)
        if response is not None:
            callback(response)

def start_listening_thread(ip: str, port: int, callback):
    """
    Start a background thread that listens for JSON responses on the given IP and port.
    When a response is received, the callback(response) is invoked.
    """
    thread = threading.Thread(target=_response_loop, args=(ip, port, callback))
    thread.daemon = True
    thread.start()
    return thread