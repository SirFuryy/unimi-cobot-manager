import pyzed.sl as sl
import cv2
import numpy as np
import time
from datetime import datetime
import os

class ContinuousObjectScanner:
    def __init__(self, output_dir="scan_output"):
        """Inizializza lo scanner con la camera ZED per registrazione continua"""
        self.zed = sl.Camera()
        self.output_dir = output_dir
        self.is_recording = False
        self.video_writer = None
        
        # Crea directory di output
        os.makedirs(output_dir, exist_ok=True)
        
        # Parametri di inizializzazione
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD2K
        init_params.camera_fps = 30
        init_params.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
        init_params.coordinate_units = sl.UNIT.METER
        init_params.depth_minimum_distance = 0.2
        
        # Apri la camera
        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Errore apertura camera: {err}")
            exit(1)
        
        # Parametri runtime
        self.runtime_params = sl.RuntimeParameters()
        # Imposta il sensing_mode solo se l'enum è disponibile nella versione di pyzed.sl usata,
        # alcune versioni non espongono SENSING_MODE e questo evitera' l'AttributeError.
        if hasattr(sl, "SENSING_MODE"):
            try:
                self.runtime_params.sensing_mode = sl.SENSING_MODE.FILL
            except Exception:
                # In caso di nomi diversi o altri errori, non forzare l'impostazione
                pass
        
        # Matrici per immagini
        self.image_left = sl.Mat()
        self.depth_map = sl.Mat()
        
        # Ottieni info camera per video writer
        cam_info = self.zed.get_camera_information()
        self.frame_width = cam_info.camera_configuration.resolution.width
        self.frame_height = cam_info.camera_configuration.resolution.height
        self.fps = init_params.camera_fps
        
        print("Camera ZED inizializzata con successo!")
        print(f"Risoluzione: {self.frame_width}x{self.frame_height} @ {self.fps} FPS")
        
    def start_recording(self, output_filename=None, codec='mp4v'):
        """
        Inizia la registrazione continua
        
        Args:
            output_filename: Nome file output (None genera timestamp)
            codec: Codec video ('mp4v', 'avc1', 'H264')
        """
        if self.is_recording:
            print("⚠️  Registrazione già in corso!")
            return
        
        # Genera nome file se non specificato
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"continuous_scan_{timestamp}.mp4"
        
        self.output_path = os.path.join(self.output_dir, output_filename)
        
        # Crea writer video
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.video_writer = cv2.VideoWriter(
            self.output_path, 
            fourcc, 
            self.fps, 
            (self.frame_width, self.frame_height)
        )
        
        if not self.video_writer.isOpened():
            print("❌ Errore nell'aprire il video writer!")
            return
        
        self.is_recording = True
        self.start_time = time.time()
        self.frame_count = 0
        
        print(f"\n🔴 REGISTRAZIONE INIZIATA")
        print(f"   File: {self.output_path}")
        print(f"   Codec: {codec}")
        print(f"   Risoluzione: {self.frame_width}x{self.frame_height}")
        print(f"   FPS: {self.fps}\n")
        
    def stop_recording(self):
        """Ferma la registrazione"""
        if not self.is_recording:
            print("⚠️  Nessuna registrazione in corso!")
            return
        
        self.is_recording = False
        
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        duration = time.time() - self.start_time
        
        print(f"\n⏹️  REGISTRAZIONE TERMINATA")
        print(f"   Frame registrati: {self.frame_count}")
        print(f"   Durata: {duration:.2f}s")
        print(f"   File salvato: {self.output_path}\n")
        
    def run_continuous_scan(self, scan_positions=None, show_instructions=True):
        """
        Esegue una scansione continua con istruzioni per l'operatore
        
        Args:
            scan_positions: Lista di posizioni da raggiungere
            show_instructions: Mostra istruzioni sullo schermo
        """
        # Posizioni predefinite
        if scan_positions is None:
            scan_positions = [
                "Posizione FRONTALE - inquadra l'oggetto di fronte",
                "Muovi verso DESTRA 45° - mantieni inquadrato",
                "Continua verso DESTRA 90° - vista laterale",
                "Muovi verso il RETRO - passa dietro l'oggetto",
                "Continua verso SINISTRA 90° - altro lato",
                "Torna verso SINISTRA 45° - quasi frontale",
                "Solleva la camera - vista dall'ALTO inclinata",
                "Abbassa la camera - vista dal BASSO",
                "ROVESCIA la camera - vista dall'alto verticale",
                "Torna alla posizione FRONTALE",
            ]
        
        print("\n" + "="*70)
        print("🎬 SCANSIONE CONTINUA OGGETTO")
        print("="*70)
        print("\nCONTROLLI:")
        print("  SPAZIO  - Avanza alla prossima posizione")
        print("  R       - Inizia/Ferma registrazione")
        print("  Q       - Esci")
        print("\nISTRUZIONI:")
        print("1. Posiziona la camera nella prima posizione")
        print("2. Premi 'R' per iniziare la registrazione")
        print("3. Muovi la camera seguendo le istruzioni sullo schermo")
        print("4. Premi SPAZIO quando raggiungi ogni posizione")
        print("5. Premi 'R' alla fine per salvare il video")
        print("="*70 + "\n")
        
        current_position = 0
        recording_requested = False
        
        while True:
            # Cattura frame
            if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Recupera immagine
                self.zed.retrieve_image(self.image_left, sl.VIEW.LEFT)
                frame = self.image_left.get_data()
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Crea overlay con istruzioni
                overlay = frame_rgb.copy()
                
                # Sfondo semi-trasparente per il testo
                cv2.rectangle(overlay, (0, 0), (self.frame_width, 200), 
                            (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame_rgb, 0.4, 0, frame_rgb)
                
                # Status registrazione
                if self.is_recording:
                    elapsed = time.time() - self.start_time
                    status_color = (0, 0, 255)  # Rosso
                    status_text = f"🔴 REC {elapsed:.1f}s | Frame: {self.frame_count}"
                    # Cerchio rosso lampeggiante
                    if int(elapsed * 2) % 2 == 0:
                        cv2.circle(frame_rgb, (30, 30), 15, (0, 0, 255), -1)
                else:
                    status_color = (128, 128, 128)  # Grigio
                    status_text = "⏸️  Premi 'R' per iniziare la registrazione"
                
                cv2.putText(frame_rgb, status_text, (60, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
                
                # Posizione corrente
                if current_position < len(scan_positions):
                    position_text = f"Posizione {current_position + 1}/{len(scan_positions)}"
                    instruction_text = scan_positions[current_position]
                    
                    cv2.putText(frame_rgb, position_text, (20, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    cv2.putText(frame_rgb, instruction_text, (20, 130), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame_rgb, "Premi SPAZIO quando pronto", (20, 170), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                else:
                    cv2.putText(frame_rgb, "✅ SCANSIONE COMPLETATA!", (20, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    cv2.putText(frame_rgb, "Premi 'R' per salvare il video", (20, 140), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                
                # Scrivi frame se in registrazione
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame_rgb)
                    self.frame_count += 1
                
                # Mostra frame
                cv2.imshow("ZED Continuous Scanner", frame_rgb)
                
                # Gestione input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n⚠️  Uscita richiesta dall'utente")
                    break
                    
                elif key == ord('r'):
                    if not self.is_recording:
                        self.start_recording()
                    else:
                        self.stop_recording()
                        if current_position >= len(scan_positions):
                            print("✅ Scansione completata e salvata!")
                            break
                    
                elif key == ord(' '):
                    if current_position < len(scan_positions):
                        print(f"✓ Posizione {current_position + 1} raggiunta: {scan_positions[current_position]}")
                        current_position += 1
                        if current_position >= len(scan_positions):
                            print("\n🎉 Tutte le posizioni completate!")
                            print("   Premi 'R' per fermare e salvare la registrazione\n")
            
            else:
                print("⚠️  Errore nel catturare il frame")
                time.sleep(0.01)
        
        # Assicurati che la registrazione sia fermata
        if self.is_recording:
            self.stop_recording()
    
    def run_freeform_scan(self):
        """
        Modalità libera: registra continuamente mentre l'operatore muove la camera
        """
        print("\n" + "="*70)
        print("🎬 SCANSIONE LIBERA")
        print("="*70)
        print("\nCONTROLLI:")
        print("  R - Inizia/Ferma registrazione")
        print("  Q - Esci")
        print("\nMuovi la camera liberamente intorno all'oggetto durante la registrazione")
        print("="*70 + "\n")
        
        while True:
            # Cattura frame
            if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Recupera immagine
                self.zed.retrieve_image(self.image_left, sl.VIEW.LEFT)
                frame = self.image_left.get_data()
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Overlay status
                if self.is_recording:
                    elapsed = time.time() - self.start_time
                    # Cerchio rosso lampeggiante
                    if int(elapsed * 2) % 2 == 0:
                        cv2.circle(frame_rgb, (30, 30), 15, (0, 0, 255), -1)
                    
                    cv2.putText(frame_rgb, f"🔴 REC {elapsed:.1f}s", (60, 40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(frame_rgb, f"Frame: {self.frame_count}", (60, 80), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                    # Scrivi frame
                    if self.video_writer:
                        self.video_writer.write(frame_rgb)
                        self.frame_count += 1
                else:
                    cv2.putText(frame_rgb, "Premi 'R' per iniziare", (30, 40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (128, 128, 128), 2)
                
                # Mostra frame
                cv2.imshow("ZED Free Scanner", frame_rgb)
                
                # Gestione input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n⚠️  Uscita richiesta")
                    break
                    
                elif key == ord('r'):
                    if not self.is_recording:
                        self.start_recording()
                    else:
                        self.stop_recording()
                        print("✅ Video salvato!")
                        break
        
        # Assicurati che la registrazione sia fermata
        if self.is_recording:
            self.stop_recording()
    
    def cleanup(self):
        """Chiude la camera e libera le risorse"""
        if self.is_recording:
            self.stop_recording()
        
        cv2.destroyAllWindows()
        self.zed.close()
        print("🔒 Risorse rilasciate")


def main():
    """Esempio di utilizzo dello scanner continuo"""
    
    # Crea lo scanner
    scanner = ContinuousObjectScanner(output_dir="scansioni")
    
    try:
        # Scegli modalità
        print("\n" + "="*70)
        print("SCEGLI MODALITÀ DI SCANSIONE")
        print("="*70)
        print("1. Scansione guidata (con posizioni predefinite)")
        print("2. Scansione libera (movimento continuo)")
        print("="*70)
        
        choice = input("\nScelta (1/2): ").strip()
        
        if choice == "2":
            # Modalità libera
            scanner.run_freeform_scan()
        else:
            # Modalità guidata (default)
            posizioni_custom = [
                "FRONTALE - inquadra l'oggetto di fronte",
                "DESTRA 45° - ruota mentre inquadri",
                "DESTRA 90° - vista laterale completa",
                "RETRO - continua dietro l'oggetto",
                "SINISTRA 90° - altro lato",
                "SINISTRA 45° - ritorno verso fronte",
                "ALTO - solleva la camera (45°)",
                "BASSO - abbassa la camera (45°)",
                "ALTO VERTICALE - rovescia completamente",
                "FRONTALE - torna alla posizione iniziale",
            ]
            
            scanner.run_continuous_scan(scan_positions=posizioni_custom)
        
    except KeyboardInterrupt:
        print("\n⚠️  Interruzione da tastiera")
    
    finally:
        scanner.cleanup()


if __name__ == "__main__":
    main()
    