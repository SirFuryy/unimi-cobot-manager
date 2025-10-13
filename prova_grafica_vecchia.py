import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import time
from datetime import datetime
from pathlib import Path
import atexit


class MultiTerminalGUI:
    """
    Classe per gestire un'interfaccia multi-terminale con 6 finestre di output
    che ricevono dati da thread separati e salvano automaticamente su file.
    """
    
    def __init__(self, master=None, terminal_titles=None, log_directory="log_files"):
        """
        Inizializza l'interfaccia multi-terminale.
        
        Args:
            master: Finestra root di tkinter (None per crearne una nuova)
            terminal_titles: Lista di 6 titoli per i terminali
            log_directory: Directory dove salvare i file di log
        """
        # Crea o usa la finestra principale
        if master is None:
            self.root = tk.Tk()
            self.root.title("Multi-Terminal Interface")
            self.root.geometry("1400x800")
        else:
            self.root = master
        
        # Configurazione titoli terminali
        if terminal_titles is None:
            self.terminal_titles = [
                "Terminal 1", "Terminal 2", "Terminal 3",
                "Terminal 4", "Terminal 5", "Terminal 6"
            ]
        else:
            self.terminal_titles = terminal_titles[:6]

        # Dizionari per gestire terminali e code
        self.terminals = {}
        self.queues = {}
        self.file_locks = {}
        print("ok fin qui")
        
        # Setup directory e file di log
        self.log_dir = Path(log_directory)
        self.log_dir.mkdir(exist_ok=True)
        self.log_files = {}
        self._setup_log_files()
        
        # Flag per gestire lo shutdown
        self.running = True
        
        # Setup interfaccia
        self._setup_gui()
        
        # Avvia thread di aggiornamento GUI
        self.update_thread = threading.Thread(target=self._update_terminals, daemon=True)
        self.update_thread.start()
        
        # Registra cleanup all'uscita
        atexit.register(self.cleanup)
    
    def _setup_log_files(self):
        """Inizializza i file di log, sovrascrivendo quelli esistenti."""
        for i, title in enumerate(self.terminal_titles):
            filename = f"terminal_{i+1}_{title.replace(' ', '_')}.log"
            filepath = self.log_dir / filename
            # Sovrascrive il file se esiste
            self.log_files[i] = open(filepath, 'w', encoding='utf-8')
            self.file_locks[i] = threading.Lock()
            # Scrivi header
            self.log_files[i].write(f"=== {title} - Started: {datetime.now()} ===\n\n")
            self.log_files[i].flush()
    
    def _setup_gui(self):
        """Costruisce l'interfaccia grafica con griglia 3x2 + colonna extra."""
        # Frame principale con weight per ridimensionamento
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura grid weights per ridimensionamento
        for i in range(3):  # 3 colonne per terminali
            main_frame.grid_columnconfigure(i, weight=1)
        main_frame.grid_columnconfigure(3, weight=0, minsize=200)  # Colonna extra fissa
        
        for i in range(2):  # 2 righe
            main_frame.grid_rowconfigure(i, weight=1)
        
        # Crea i 6 terminali
        positions = [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2)]
        
        for idx, (row, col) in enumerate(positions):
            # Frame per ogni terminale con bordo
            terminal_frame = tk.LabelFrame(
                main_frame, 
                text=self.terminal_titles[idx],
                font=("Arial", 10, "bold"),
                padx=5, 
                pady=5
            )
            terminal_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Area di testo con scroll
            text_widget = scrolledtext.ScrolledText(
                terminal_frame,
                wrap=tk.WORD,
                width=40,
                height=15,
                font=("Consolas", 9),
                bg="white",
                fg="black",
                insertbackground="black"
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # Disabilita editing diretto
            text_widget.config(state=tk.DISABLED)
            
            # Salva riferimenti
            self.terminals[idx] = text_widget
            self.queues[idx] = queue.Queue()
        
        # Frame per controlli futuri (colonna extra)
        self.control_frame = tk.LabelFrame(
            main_frame,
            text="Controls",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10
        )
        self.control_frame.grid(row=0, column=3, rowspan=2, padx=5, pady=5, sticky="nsew")
        
        # Status label
        self.status_label = tk.Label(
            self.control_frame,
            text="Status: Idle",
            font=("Arial", 9, "bold"),
            fg="grey"
        )
        self.status_label.pack(pady=20)

        def _set_status_text(text, color=None):
            """Aggiorna in modo sicuro la status_label dal thread principale."""
            def _apply():
                try:
                    self.status_label.config(text=text, fg=color if color else self.status_label.cget("fg"))
                except Exception:
                    pass
            self.root.after(0, _apply)

        # Espone un metodo instance-level per essere chiamato da altri thread o codice esterno
        self.set_status = _set_status_text

        self.stop_button = tk.Button(
            self.control_frame,
            text="Chiudi Programma",
            command=self.root.quit,
            width=20
        )
        self.stop_button.pack(side=tk.BOTTOM, pady=10)
    
    def write_to_terminal(self, terminal_id, text):
        """
        Metodo thread-safe per scrivere testo in un terminale specifico.
        
        Args:
            terminal_id: ID del terminale (0-5)
            text: Testo da scrivere
        """
        if terminal_id in self.queues:
            self.queues[terminal_id].put(text)
    
    def _update_terminals(self):
        """Thread che aggiorna continuamente i terminali dalla coda."""
        while self.running:
            for terminal_id in range(6):
                try:
                    # Controlla se ci sono messaggi nella coda
                    if not self.queues[terminal_id].empty():
                        # Raccogli tutti i messaggi disponibili (batch processing)
                        messages = []
                        while not self.queues[terminal_id].empty() and len(messages) < 10:
                            try:
                                msg = self.queues[terminal_id].get_nowait()
                                messages.append(msg)
                            except queue.Empty:
                                break
                        
                        if messages:
                            combined_text = '\n'.join(messages) + '\n'
                            
                            # Aggiorna GUI
                            self.root.after(0, self._update_terminal_widget, terminal_id, combined_text)
                            
                            # Salva su file
                            self._write_to_log(terminal_id, combined_text)
                
                except Exception as e:
                    print(f"Error updating terminal {terminal_id}: {e}")
            
            # Breve pausa per non sovraccaricare CPU
            time.sleep(0.01)
    
    def _update_terminal_widget(self, terminal_id, text):
        """Aggiorna il widget del terminale nel thread principale."""
        try:
            widget = self.terminals[terminal_id]
            widget.config(state=tk.NORMAL)
            widget.insert(tk.END, text)
            # Auto-scroll
            widget.see(tk.END)
            widget.config(state=tk.DISABLED)
            
            # Limita linee visualizzate per performance (mantieni ultime 1000)
            lines = widget.get("1.0", tk.END).split('\n')
            if len(lines) > 1000:
                widget.config(state=tk.NORMAL)
                widget.delete("1.0", f"{len(lines)-1000}.0")
                widget.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error updating widget {terminal_id}: {e}")
    
    def _write_to_log(self, terminal_id, text):
        """Scrive il testo nel file di log corrispondente."""
        with self.file_locks[terminal_id]:
            try:
                self.log_files[terminal_id].write(text)
                self.log_files[terminal_id].flush()
            except Exception as e:
                print(f"Error writing to log {terminal_id}: {e}")
    
    def add_control(self, widget):
        """
        Metodo per aggiungere controlli personalizzati alla colonna extra.
        
        Args:
            widget: Widget tkinter da aggiungere
        """
        widget.pack(in_=self.control_frame, pady=5)
    
    def cleanup(self):
        """Chiude i file di log e pulisce le risorse."""
        self.running = False
        
        # Chiudi tutti i file di log
        for file in self.log_files.values():
            try:
                file.close()
            except:
                pass
        
        # Aggiorna status
        if hasattr(self, 'status_label'):
            try:
                self.status_label.config(text="Status: Stopped", fg="red")
            except:
                pass
    
    def run(self):
        """Avvia il main loop dell'interfaccia (blocca fino alla chiusura)."""
        try:
            self.root.mainloop()
        finally:
            print("Cleaning up resources...")
            self.cleanup()


# ========== ESEMPIO DI UTILIZZO ==========

def example_worker_fast(gui, terminal_id, name):
    """Esempio di worker che genera testo velocemente."""
    counter = 0
    while True:
        counter += 1
        message = f"[{name}] Fast update #{counter} - Time: {time.strftime('%H:%M:%S')}"
        gui.write_to_terminal(terminal_id, message)
        time.sleep(0.05)  # 50ms

def example_worker_medium(gui, terminal_id, name):
    """Esempio di worker che genera testo a velocità media."""
    counter = 0
    while True:
        counter += 1
        message = f"[{name}] Medium update #{counter} - Processing data..."
        gui.write_to_terminal(terminal_id, message)
        time.sleep(0.2)  # 200ms

def example_worker_random(gui, terminal_id, name):
    """Esempio di worker che genera testo a intervalli casuali."""
    import random
    counter = 0
    while True:
        counter += 1
        message = f"[{name}] Random event #{counter} - Value: {random.randint(0, 100)}"
        gui.write_to_terminal(terminal_id, message)
        time.sleep(random.uniform(0.1, 2.0))


if __name__ == "__main__":
    # Crea l'interfaccia con titoli personalizzati
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
    
    # Avvia thread di esempio (sostituisci con i tuoi thread reali)
    threads = [
        threading.Thread(target=example_worker_fast, args=(gui, 0, "Stato_robot"), daemon=True),
        threading.Thread(target=example_worker_fast, args=(gui, 1, "Dimensioni_ottenute"), daemon=True),
        threading.Thread(target=example_worker_medium, args=(gui, 2, "Coordinate_bbbox"), daemon=True),
        threading.Thread(target=example_worker_medium, args=(gui, 3, "Invio_comandi"), daemon=True),
        threading.Thread(target=example_worker_random, args=(gui, 4, "Messaggi_errore"), daemon=True),
        threading.Thread(target=example_worker_random, args=(gui, 5, "Stato_Feedback"), daemon=True),
    ]

    # Esempio: aggiungi un pulsante nella colonna controlli
    start_button = tk.Button(
        gui.control_frame,
        text="Avvia Programma",
        command= lambda: [t.start() for t in threads],
        width=20
    )
    gui.add_control(start_button)

    ready_button = tk.Button(
        gui.control_frame,
        text="Prepara robot",
        command= lambda: gui.set_status("Status: Ready", "yellow"),
        width=20
    )
    gui.add_control(ready_button)

    # Campo di input per il valore della scansione
    scan_label = tk.Label(gui.control_frame, text="Piante da scansionare:", font=("Arial", 9))
    scan_entry = tk.Entry(gui.control_frame, width=20, font=("Arial", 9))
    gui.add_control(scan_label)
    gui.add_control(scan_entry)
    val = 0

    # Funzione che esegue la scansione in background usando il valore inserito
    def start_scan():
        gui.set_status("Status: Scanning...", "green")
        val = scan_entry.get().strip()
        if not val:
            gui.write_to_terminal(3, "[Scan] Valore vuoto: inserire un valore prima di eseguire la scansione")
            gui.set_status("Status: Ready", "yellow")
            return
        try:
            numeric_val = float(val)
            n = max(0, int(numeric_val))
            if n == 0:
                gui.write_to_terminal(3, "[Scan] Nessun pulsante da generare (valore 0)")
                gui.set_status("Status: Ready", "yellow")
                return

            def scan_task():
                # Simula lavoro di scansione (sostituire con lavoro reale)
                time.sleep(2)

                def create_buttons():
                    # Rimuove eventuali pulsanti precedenti
                    if hasattr(gui, 'scan_buttons_frame') and gui.scan_buttons_frame.winfo_exists():
                        try:
                            gui.scan_buttons_frame.destroy()
                        except Exception:
                            pass

                    gui.scan_buttons_frame = tk.LabelFrame(gui.control_frame, text="Scan Buttons", padx=5, pady=5)
                    gui.scan_buttons_frame.pack(fill=tk.X, pady=5)

                    gui.scan_handlers = {}
                    for i in range(n):
                        def make_handler(idx):
                            def handler(idx=idx):
                                # Funzione unica per ogni pulsante: personalizzabile
                                gui.write_to_terminal(3, f"[Scan] Pulsante {idx+1} premuto")
                                # Qui si possono eseguire azioni diverse per idx
                            return handler

                        btn = tk.Button(
                            gui.scan_buttons_frame,
                            text=f"Pulsante {i+1}",
                            command=make_handler(i),
                            width=20
                        )
                        btn.pack(fill=tk.X, padx=2, pady=2, anchor="w")
                        gui.scan_handlers[i] = make_handler(i)

                # Creazione dei widget deve avvenire nel thread principale
                gui.root.after(0, create_buttons)

            threading.Thread(target=scan_task, daemon=True).start()
            gui.set_status("Status: Ready", "yellow")
        except ValueError:
            gui.write_to_terminal(3, f"[Scan] Valore non valido: '{val}' (serve un numero)")
            return

    # Bottone per lanciare la scansione
    scan_button = tk.Button(
        gui.control_frame, 
        text="Esegui scansione", 
        command=start_scan, 
        width=20)
    gui.add_control(scan_button)
   
    # Avvia GUI (blocca qui)
    gui.run()