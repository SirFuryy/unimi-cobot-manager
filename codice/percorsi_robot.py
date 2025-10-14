import socket
import json
import time
import threading
from typing import Tuple, List

class RobotController:
    def __init__(self, host: str = "192.168.1.100", port: int = 5000):
        """
        Inizializza il controller del robot.
        
        Args:
            host: Indirizzo IP del robot
            port: Porta TCP/IP del robot
        """
        self.host = host
        self.port = port
        self.socket = None
        self.is_scanning = False
        self.scan_data = []
        
    def connect(self):
        """Stabilisce la connessione con il robot."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"Connesso al robot su {self.host}:{self.port}")
    
    def disconnect(self):
        """Chiude la connessione con il robot."""
        if self.socket:
            self.socket.close()
            print("Disconnesso dal robot")
    
    def send_command(self, command: dict) -> dict:
        """
        Invia un comando al robot e riceve la risposta.
        
        Args:
            command: Dizionario contenente il comando
            
        Returns:
            Risposta del robot come dizionario
        """
        message = json.dumps(command)
        self.socket.sendall(message.encode('utf-8'))
        response = self.socket.recv(4096).decode('utf-8')
        return json.loads(response)
    
    def move_to_position(self, x: float, y: float, z: float):
        """
        Muove il robot a una posizione specifica.
        
        Args:
            x, y, z: Coordinate della posizione target
        """
        command = {
            "action": "move",
            "x": x,
            "y": y,
            "z": z
        }
        response = self.send_command(command)
        print(f"Movimento a ({x}, {y}, {z}): {response.get('status', 'unknown')}")
        time.sleep(0.5)  # Attesa per completare il movimento
    
    def start_scanning(self):
        """Avvia la scansione in background."""
        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._scan_worker)
        self.scan_thread.start()
        print("Scansione avviata")
    
    def stop_scanning(self):
        """Ferma la scansione."""
        self.is_scanning = False
        if hasattr(self, 'scan_thread'):
            self.scan_thread.join()
        print("Scansione terminata")
    
    def _scan_worker(self):
        """Worker thread per la scansione continua."""
        while self.is_scanning:
            # Simula la raccolta dati dalla scansione
            scan_command = {"action": "scan"}
            try:
                data = self.send_command(scan_command)
                self.scan_data.append({
                    "timestamp": time.time(),
                    "data": data
                })
            except Exception as e:
                print(f"Errore durante la scansione: {e}")
            time.sleep(0.1)  # Frequenza di scansione
    
    def calculate_scan_points(self, center_x: float, center_y: float, 
                             center_z: float, distance: float = 0.5) -> List[Tuple[float, float, float]]:
        """
        Calcola i quattro punti attorno alla piantina.
        
        Args:
            center_x, center_y, center_z: Coordinate del centro della piantina
            distance: Distanza dal centro per i punti di scansione
            
        Returns:
            Lista di tuple con le coordinate dei quattro punti
        """
        points = [
            (center_x + distance, center_y, center_z),  # Destra
            (center_x, center_y + distance, center_z),  # Avanti
            (center_x - distance, center_y, center_z),  # Sinistra
            (center_x, center_y - distance, center_z)   # Indietro
        ]
        return points
    
    def scan_plant(self, center_x: float, center_y: float, center_z: float, 
                   distance: float = 0.5):
        """
        Esegue la scansione completa della piantina muovendosi nei quattro punti.
        
        Args:
            center_x, center_y, center_z: Coordinate del centro della piantina
            distance: Distanza dal centro per i punti di scansione
        """
        # Calcola i punti di scansione
        scan_points = self.calculate_scan_points(center_x, center_y, center_z, distance)
        
        # Avvia la scansione in background
        self.start_scanning()
        
        try:
            # Muovi il robot attraverso i quattro punti
            for i, (x, y, z) in enumerate(scan_points, 1):
                print(f"Movimento al punto {i}/4")
                self.move_to_position(x, y, z)
                time.sleep(1)  # Pausa per acquisire dati da ogni posizione
        finally:
            # Ferma la scansione
            self.stop_scanning()
            print(f"Scansione completata. Dati raccolti: {len(self.scan_data)} campioni")
    
    def save_scan_data(self, filename: str = "scan_data.json"):
        """
        Salva i dati della scansione su file.
        
        Args:
            filename: Nome del file di output
        """
        with open(filename, 'w') as f:
            json.dump(self.scan_data, f, indent=2)
        print(f"Dati salvati in {filename}")


# Esempio di utilizzo
if __name__ == "__main__":
    # Inizializza il controller
    robot = RobotController(host="192.168.1.100", port=5000)
    
    try:
        # Connetti al robot
        robot.connect()
        
        # Coordinate del centro della piantina
        plant_center = (1.0, 2.0, 0.5)  # x, y, z
        
        # Esegui la scansione
        robot.scan_plant(*plant_center, distance=0.3)
        
        # Salva i dati
        robot.save_scan_data("plant_scan.json")
        
    finally:
        # Disconnetti
        robot.disconnect()