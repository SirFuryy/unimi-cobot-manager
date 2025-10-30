import tkinter as tk
from tkinter import scrolledtext, ttk
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
        # Definizione palette colori moderna
        self.colors = {
            'bg_main': '#1a1a1a',           # Sfondo principale dark
            'bg_secondary': '#2d2d2d',       # Sfondo secondario
            'bg_terminal': '#0d1117',        # Sfondo terminali (GitHub dark style)
            'fg_terminal': '#58a6ff',        # Testo terminali azzurro
            'accent_1': '#238636',           # Verde successo
            'accent_2': '#1f6feb',           # Blu info
            'accent_3': '#da3633',           # Rosso errore
            'accent_4': '#d29922',           # Giallo warning
            'accent_5': '#a371f7',           # Viola
            'accent_6': '#f778ba',           # Rosa
            'border': '#30363d',             # Bordi
            'text_primary': '#f0f6fc',       # Testo primario
            'text_secondary': '#8b949e',     # Testo secondario
            'button_bg': '#21262d',          # Sfondo pulsanti
            'button_hover': '#30363d',       # Hover pulsanti
            'button_active': '#238636',      # Pulsanti attivi
        }
        
        # Crea o usa la finestra principale
        if master is None:
            self.root = tk.Tk()
            self.root.title("🚀 Multi-Terminal Robot Control Interface")
            self.root.geometry("1600x900")
            self.root.configure(bg=self.colors['bg_main'])
            
            # Stile moderno per la finestra
            try:
                self.root.iconbitmap("assets/robot.ico")  # Rimuove icona default se possibile
            except:
                pass
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
        
        # Setup directory e file di log
        self.log_dir = Path(log_directory)
        self.log_dir.mkdir(exist_ok=True)
        self.log_files = {}
        self._setup_log_files()
        
        # Flag per gestire lo shutdown
        self.running = True
        
        # Setup stili ttk
        self._setup_styles()
        
        # Setup interfaccia
        self._setup_gui()
        
        # Avvia thread di aggiornamento GUI
        self.update_thread = threading.Thread(target=self._update_terminals, daemon=True)
        self.update_thread.start()
        
        # Registra cleanup all'uscita
        atexit.register(self.cleanup)
    
    def _setup_styles(self):
        """Configura gli stili ttk per un look moderno."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Stile per i LabelFrame
        style.configure(
            "Terminal.TLabelframe",
            background=self.colors['bg_secondary'],
            bordercolor=self.colors['border'],
            lightcolor=self.colors['border'],
            darkcolor=self.colors['bg_main'],
            borderwidth=2,
            relief="flat"
        )
        style.configure(
            "Terminal.TLabelframe.Label",
            background=self.colors['bg_secondary'],
            foreground=self.colors['text_primary'],
            font=("Segoe UI", 10, "bold")
        )
    
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

    def _create_styled_button(self, parent, text, command = None, width=20, color_type='primary'):
        """Crea un pulsante stilizzato."""
        colors = {
            'primary': (self.colors['accent_2'], '#ffffff'),
            'success': (self.colors['accent_1'], '#ffffff'),
            'danger': (self.colors['accent_3'], '#ffffff'),
            'warning': (self.colors['accent_4'], '#000000'),
            'secondary': (self.colors['button_bg'], self.colors['text_primary'])
        }
        
        bg_color, fg_color = colors.get(color_type, colors['primary'])
        
        btn = tk.Button(
            parent,
            text=text,
            command=command, # type: ignore
            width=width,
            font=("Segoe UI", 9, "bold"),
            bg=bg_color,
            fg=fg_color,
            activebackground=self.colors['button_hover'],
            activeforeground=fg_color,
            bd=0,
            padx=10,
            pady=8,
            cursor="hand2",
            relief="flat"
        )
        
        # Effetti hover
        def on_enter(e):
            if color_type == 'secondary':
                btn['background'] = self.colors['button_hover']
            else:
                btn['background'] = self._lighten_color(bg_color)
        
        def on_leave(e):
            btn['background'] = bg_color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def _lighten_color(self, color):
        """Schiarisce leggermente un colore per effetti hover."""
        # Semplice approccio per schiarire
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            r = min(255, r + 20)
            g = min(255, g + 20)
            b = min(255, b + 20)
            
            return f'#{r:02x}{g:02x}{b:02x}'
        return color
    
    def _setup_gui(self):
        """Costruisce l'interfaccia grafica con griglia 3x2 + colonna extra."""
        # Header con titolo
        header_frame = tk.Frame(self.root, bg=self.colors['bg_main'], height=50)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header_frame,
            text="🤖 ROBOT CONTROL CENTER",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors['bg_main'],
            fg=self.colors['text_primary']
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        # Timestamp label
        self.time_label = tk.Label(
            header_frame,
            text="",
            font=("Segoe UI", 10),
            bg=self.colors['bg_main'],
            fg=self.colors['text_secondary']
        )
        self.time_label.pack(side=tk.RIGHT, padx=20)
        self._update_time()
        
        # Frame principale con weight per ridimensionamento
        main_frame = tk.Frame(self.root, bg=self.colors['bg_main'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configura grid weights per ridimensionamento
        for i in range(3):  # 3 colonne per terminali
            main_frame.grid_columnconfigure(i, weight=1)
        main_frame.grid_columnconfigure(3, weight=0, minsize=250)  # Colonna extra più larga
        
        for i in range(2):  # 2 righe
            main_frame.grid_rowconfigure(i, weight=1)
        
        # Crea i 6 terminali
        positions = [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2)]
        
        for idx, (row, col) in enumerate(positions):
            # Colore personalizzato per ogni terminale
            border_color, text_color = '#1f6feb', '#b9bbb6'
            
            # Frame per ogni terminale con bordo colorato
            terminal_frame = tk.Frame(
                main_frame,
                bg=self.colors['bg_secondary'],
                highlightbackground=border_color,
                highlightthickness=2,
                bd=0
            )
            terminal_frame.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            
            # Header del terminale
            header = tk.Frame(terminal_frame, bg=border_color, height=35)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            # Icone per i terminali
            icons = ["⚙️", "📊", "📷", "📡", "⚠️", "💬"]
            
            terminal_title = tk.Label(
                header,
                text=f" {icons[idx]} {self.terminal_titles[idx]}",
                font=("Segoe UI", 11, "bold"),
                bg=border_color,
                fg='#ffffff'
            )
            terminal_title.pack(side=tk.LEFT, padx=10, pady=5)
            
            # Indicatore di attività
            activity_indicator = tk.Label(
                header,
                text="●",
                font=("Segoe UI", 10),
                bg=border_color,
                fg='#90ee90'
            )
            activity_indicator.pack(side=tk.RIGHT, padx=10)
            
            # Container per il terminale
            terminal_container = tk.Frame(
                terminal_frame,
                bg=self.colors['bg_secondary']
            )
            terminal_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # Area di testo con scroll
            text_widget = scrolledtext.ScrolledText(
                terminal_container,
                wrap=tk.WORD,
                width=40,
                height=15,
                font=("Cascadia Code", 9),  # Font monospace moderno
                bg=self.colors['bg_terminal'],
                fg=text_color,
                insertbackground=text_color,
                selectbackground=border_color,
                selectforeground='#ffffff',
                bd=0,
                padx=10,
                pady=10
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            
            # Personalizza scrollbar
            text_widget.vbar.config(
                bg=self.colors['bg_secondary'],
                activebackground=border_color,
                troughcolor=self.colors['bg_terminal'],
                width=12
            )
            
            # Disabilita editing diretto
            text_widget.config(state=tk.DISABLED)
            
            # Salva riferimenti
            self.terminals[idx] = {
                'widget': text_widget,
                'indicator': activity_indicator,
                'color': text_color
            }
            self.queues[idx] = queue.Queue()
        
        # Frame per controlli (colonna extra) con stile moderno
        self.control_frame = tk.Frame(
            main_frame,
            bg=self.colors['bg_secondary']
        )
        self.control_frame.grid(row=0, column=3, rowspan=2, padx=8, pady=8, sticky="nsew")
        
        # Header controlli
        control_header = tk.Frame(self.control_frame, bg=self.colors['accent_2'], height=35)
        control_header.pack(fill=tk.X)
        control_header.pack_propagate(False)
        
        control_title = tk.Label(
            control_header,
            text=" 🎮 CONTROL PANEL",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['accent_2'],
            fg='#ffffff'
        )
        control_title.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Container controlli con padding
        control_container = tk.Frame(
            self.control_frame,
            bg=self.colors['bg_secondary']
        )
        control_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Status con stile moderno
        status_frame = tk.Frame(control_container, bg=self.colors['bg_secondary'])
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(
            status_frame,
            text="STATUS",
            font=("Segoe UI", 9),
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_secondary']
        ).pack()
        
        self.status_label = tk.Label(
            status_frame,
            text="⚪ IDLE",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_secondary']
        )
        self.status_label.pack(pady=5)

        self.scan_buttons_frame: tk.Frame | None = None  # Placeholder per i pulsanti di scansione

        def _set_status_text(text, color=None):
            """Aggiorna in modo sicuro la status_label dal thread principale."""
            status_icons = {
                'green': '🟢',
                'yellow': '🟡',
                'red': '🔴',
                'grey': '⚪'
            }
            
            def _apply():
                try:
                    icon = status_icons.get(color, '⚪')
                    self.status_label.config(
                        text=f"{icon} {text.replace('Status: ', '').upper()}",
                        fg=color if color in ['green', 'yellow', 'red'] else self.colors['text_secondary']
                    )
                except Exception:
                    pass
            self.root.after(0, _apply)
        
        self.set_status = _set_status_text
        
        # Separatore stilizzato
        separator = tk.Frame(control_container, height=2, bg=self.colors['border'])
        separator.pack(fill=tk.X, pady=20)
        
        # Pulsante chiudi con stile
        self.stop_button = self._create_styled_button(
            control_container,
            text="❌ CHIUDI PROGRAMMA",
            command=self.root.quit,
            width=20,
            color_type='danger'
        )
        self.stop_button.pack(side=tk.BOTTOM, pady=10)
        
        # Salva il container per controlli aggiuntivi
        self.control_container = control_container
    
    def _update_time(self):
        """Aggiorna il timestamp nell'header."""
        current_time = datetime.now().strftime("%d/%m/%Y - %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self._update_time)
    
    def write_to_terminal(self, terminal_id, text):
        """
        Metodo thread-safe per scrivere testo in un terminale specifico.
        
        Args:
            terminal_id: ID del terminale (0-5)
            text: Testo da scrivere
        """
        if terminal_id in self.queues:
            txt = f"+- {text} -+"
            self.queues[terminal_id].put(txt)
    
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
                            
                            # Flash indicatore attività
                            self._flash_indicator(terminal_id)
                            
                            # Salva su file
                            self._write_to_log(terminal_id, combined_text)
                
                except Exception as e:
                    print(f"Error updating terminal {terminal_id}: {e}")
            
            # Breve pausa per non sovraccaricare CPU
            time.sleep(0.01)
    
    def _flash_indicator(self, terminal_id):
        """Fa lampeggiare l'indicatore di attività."""
        def flash():
            try:
                indicator = self.terminals[terminal_id]['indicator']
                indicator.config(fg='#ffffff')
                self.root.after(100, lambda: indicator.config(fg='#90ee90'))
            except:
                pass
        self.root.after(0, flash)
    
    def _update_terminal_widget(self, terminal_id, text):
        """Aggiorna il widget del terminale nel thread principale."""
        try:
            widget = self.terminals[terminal_id]['widget']
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
        widget.pack(in_=self.control_container, pady=5)
    
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
                self.set_status("STOPPED", "red")
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
        "Stato Robot",
        "Stato Calcoli", 
        "Risposte Camera",
        "Invio Comandi",
        "Messaggi Errore",
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

    # Esempio: aggiungi pulsanti stilizzati nella colonna controlli
    start_button = gui._create_styled_button(
        gui.control_container,
        text="▶️ AVVIA PROGRAMMA",
        command=lambda: [t.start() for t in threads],
        width=20,
        color_type='success'
    )
    gui.add_control(start_button)

    ready_button = gui._create_styled_button(
        gui.control_container,
        text="🔧 PREPARA ROBOT",
        command=lambda: gui.set_status("READY", "yellow"),
        width=20,
        color_type='warning'
    )
    gui.add_control(ready_button)

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
                # Simula lavoro di scansione (sostituire con lavoro reale)
                time.sleep(0.4)

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
                                # Funzione unica per ogni pulsante: personalizzabile
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
   
    # Avvia GUI (blocca qui)
    gui.run()