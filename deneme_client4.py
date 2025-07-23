import socket
import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import json
import threading
from datetime import datetime
import collections # For using deque for history records

class DroneDetectionClient:
    def __init__(self):
        # Default IP and Port values, will be displayed in the UI input fields
        self.default_server_host = '127.0.0.1' # IP of your own computer
        self.default_server_port = 8888

        self.socket = None
        self.connected = False
        self.running = True
        self.logged_in = False #Login durumu

        self.current_data = {
            "drone_count": 0,
            "threat_level": "YOK",
            "detections": [],
            "timestamp": "",
            "fire_authorized": False
        }
        
        # Using deque to store detection history.
        # This keeps memory usage under control by maintaining a fixed size.
        self.detection_history = collections.deque(maxlen=1000) # Keep last 1000 records

        # Login Credentials
        self.valid_username = "yaren"
        self.valid_password = "1234"

        self.setup_login_ui()

        self.setup_ui()


        
    def setup_ui(self):
        """Sets up the user interface (Tkinter) and places its components."""
        self.window = tk.Tk()
        self.window.title("Drone Tespit Sistemi")
        self.window.geometry("1400x800")
        self.window.configure(bg="#1a1a1a") # Background color
        
        # Main container frame
        main_container = tk.Frame(self.window, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top Navigation and Title Frame ---
        header_frame = tk.Frame(main_container, bg="#1a1a1a")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(header_frame, 
                               text="🛡️ DRONE TESPİT SİSTEMİ",
                               font=("Arial", 18, "bold"),
                               bg="#1a1a1a", fg="#00ff00")
        title_label.pack(side=tk.LEFT, padx=10)

        # Navigation buttons
        nav_button_frame = tk.Frame(header_frame, bg="#1a1a1a")
        nav_button_frame.pack(side=tk.RIGHT, padx=10)

        self.home_button = tk.Button(nav_button_frame,
                                     text="🏠 Ana Ekran",
                                     font=("Arial", 10, "bold"),
                                     bg="#0066cc", fg="#ffffff",
                                     command=lambda: self.show_frame(self.main_detection_frame))
        self.home_button.pack(side=tk.LEFT, padx=5)

        self.reports_button = tk.Button(nav_button_frame,
                                        text="📋 Raporlar",
                                        font=("Arial", 10, "bold"),
                                        bg="#0066cc", fg="#ffffff",
                                        command=lambda: self.show_frame(self.reports_frame))
        self.reports_button.pack(side=tk.LEFT, padx=5)
        # --- End of Top Navigation and Title Frame ---
        
        # Main detection screen frame
        self.main_detection_frame = tk.Frame(main_container, bg="#1a1a1a")
        self.main_detection_frame.pack(fill=tk.BOTH, expand=True)

        # Reports screen frame (initially hidden)
        self.reports_frame = tk.Frame(main_container, bg="#1a1a1a")
        # self.reports_frame.pack_forget() # Keep hidden initially

        # Left panel (Connection, Map, Control) - placed inside main_detection_frame
        left_panel = tk.Frame(self.main_detection_frame, bg="#2c2c2c", relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Right panel (Drone Details, Table) - placed inside main_detection_frame
        right_panel = tk.Frame(self.main_detection_frame, bg="#2c2c2c", relief=tk.RAISED, bd=2, width=500)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False) # Prevents the right panel's size from changing based on content
        
        # --- Connection Settings Frame ---
        connection_frame = tk.LabelFrame(left_panel, 
                                         text="📡 Bağlantı Ayarları", # Frame title
                                         font=("Arial", 10, "bold"),
                                         bg="#2c2c2c", fg="#ffffff")
        connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # IP Input Field
        ip_label = tk.Label(connection_frame, text="Sunucu IP:", bg="#2c2c2c", fg="#ffffff", font=("Arial", 10))
        ip_label.pack(side=tk.LEFT, padx=(5, 2), pady=5)
        self.ip_entry = tk.Entry(connection_frame, width=15, font=("Arial", 10), bg="#3a3a3a", fg="#ffffff", insertbackground="#ffffff")
        self.ip_entry.insert(0, self.default_server_host) # Set default IP
        self.ip_entry.pack(side=tk.LEFT, padx=(0, 10), pady=5)

        # Port Input Field
        port_label = tk.Label(connection_frame, text="Port:", bg="#2c2c2c", fg="#ffffff", font=("Arial", 10))
        port_label.pack(side=tk.LEFT, padx=(5, 2), pady=5)
        self.port_entry = tk.Entry(connection_frame, width=7, font=("Arial", 10), bg="#3a3a3a", fg="#ffffff", insertbackground="#ffffff")
        self.port_entry.insert(0, str(self.default_server_port)) # Set default Port
        self.port_entry.pack(side=tk.LEFT, padx=(0, 10), pady=5)

        # Connect Button
        self.connect_button_ui = tk.Button(connection_frame,
                                           text="Bağlan",
                                           font=("Arial", 10, "bold"),
                                           bg="#008000", fg="#ffffff",
                                           command=self.initiate_connection_from_ui) # Call new connection function
        self.connect_button_ui.pack(side=tk.LEFT, padx=(0, 5), pady=5)

        # Connection Status Label
        self.connection_status = tk.Label(connection_frame,
                                         text="🔄 Bağlantı Bekleniyor...",
                                         font=("Arial", 10),
                                         bg="#2c2c2c", fg="#ffff00")
        self.connection_status.pack(side=tk.LEFT, padx=5)
        
        # Server Info Label
        self.server_info = tk.Label(connection_frame,
                                   text=f"Hedef: {self.default_server_host}:{self.default_server_port}",
                                   font=("Arial", 9),
                                   bg="#2c2c2c", fg="#cccccc")
        self.server_info.pack(side=tk.RIGHT, padx=5)
        # --- End of Connection Settings Frame ---

        # Map View Frame
        map_frame = tk.LabelFrame(left_panel,
                                 text="🗺️ Harita Görünümü",
                                 font=("Arial", 12, "bold"),
                                 bg="#2c2c2c", fg="#ffffff")
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.map_canvas = Canvas(map_frame, bg="#0d4f3c", width=600, height=400)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control Panel Frame
        control_frame = tk.LabelFrame(left_panel,
                                     text="🎯 Kontrol Paneli",
                                     font=("Arial", 12, "bold"),
                                     bg="#2c2c2c", fg="#ffffff")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_row = tk.Frame(control_frame, bg="#2c2c2c")
        status_row.pack(fill=tk.X, padx=5, pady=5)
        
        self.threat_level_label = tk.Label(status_row,
                                         text="TEHLİKE: YOK",
                                         font=("Arial", 14, "bold"),
                                         bg="#2c2c2c", fg="#00ff00")
        self.threat_level_label.pack(side=tk.LEFT)
        
        self.drone_count_label = tk.Label(status_row,
                                         text="Drone: 0",
                                         font=("Arial", 12),
                                         bg="#2c2c2c", fg="#ffffff")
        self.drone_count_label.pack(side=tk.RIGHT)
        
        button_row = tk.Frame(control_frame, bg="#2c2c2c")
        button_row.pack(fill=tk.X, padx=5, pady=5)
        
        self.fire_button = tk.Button(button_row,
                                     text="🎯 ATEŞ ET",
                                     font=("Arial", 14, "bold"),
                                     bg="#666666",
                                     fg="#ffffff",
                                     state=tk.DISABLED, # Initially disabled
                                     command=self.fire_command,
                                     height=2,
                                     relief=tk.RAISED)
        self.fire_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.reconnect_button = tk.Button(button_row,
                                         text="🔄 Yeniden Bağlan",
                                         font=("Arial", 10),
                                         bg="#0066cc",
                                         fg="#ffffff",
                                         command=self.reconnect) # Reconnect function
        self.reconnect_button.pack(side=tk.RIGHT)
        
        # Drone Details Header
        details_title = tk.Label(right_panel,
                               text="📊 DRONE DETAYLARI",
                               font=("Arial", 14, "bold"),
                               bg="#2c2c2c", fg="#ffffff")
        details_title.pack(pady=10)
        
        # Detection Table Frame
        table_frame = tk.LabelFrame(right_panel,
                                   text="📋 Tespit Tablosu",
                                   font=("Arial", 10, "bold"),
                                   bg="#2c2c2c", fg="#ffffff")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview style settings
        style = ttk.Style()
        style.theme_use('clam') # Use a modern theme
        style.configure("GPS.Treeview",
                        background="#1a1a1a",
                        foreground="#ffffff",
                        rowheight=25,
                        fieldbackground="#1a1a1a")
        style.configure("GPS.Treeview.Heading",
                        background="#0066cc",
                        foreground="#ffffff",
                        font=("Arial", 9, "bold"))
        
        # Treeview columns (X and Y axes added)
        columns = ("ID", "Tehlike Seviyesi", "Güven", "Bölge", "X Ekseni", "Y Ekseni")
        self.drone_tree = ttk.Treeview(table_frame, 
                                       columns=columns, 
                                       show="headings",
                                       style="GPS.Treeview",
                                       height=8)
        
        # Column headers and widths (widths adjusted for X and Y axes)
        widths = [40, 120, 60, 80, 70, 70] 
        for i, col in enumerate(columns):
            self.drone_tree.heading(col, text=col)
            self.drone_tree.column(col, width=widths[i], anchor=tk.CENTER)
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.drone_tree.yview)
        self.drone_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.drone_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Last Update Label
        self.timestamp_label = tk.Label(right_panel,
                                         text="Son Güncelleme: --",
                                         font=("Arial", 9),
                                         bg="#2c2c2c", fg="#cccccc")
        self.timestamp_label.pack(pady=5)
        
        # --- Reports Screen Setup ---
        self.setup_reports_ui()

        # Set window close protocol
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Delayed call to draw map base
        self.window.after(500, self.draw_map_base)

        # Show Home Screen initially
        self.show_frame(self.main_detection_frame)
    
    def setup_reports_ui(self):
        """Sets up the user interface for the reports screen."""
        self.reports_frame.config(bg="#1a1a1a") # Background color
        
        reports_title = tk.Label(self.reports_frame,
                                 text="📊 DRONE TESPİT RAPORLARI",
                                 font=("Arial", 18, "bold"),
                                 bg="#1a1a1a", fg="#00ff00")
        reports_title.pack(pady=20)

        reports_table_frame = tk.LabelFrame(self.reports_frame,
                                            text="📋 Tespit Geçmişi Tablosu",
                                            font=("Arial", 12, "bold"),
                                            bg="#2c2c2c", fg="#ffffff")
        reports_table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Columns for the reports table (X and Y axes added)
        report_columns = ("Tespit Saati", "ID", "Güven", "Bölge", "Tehlike Seviyesi", "X Ekseni", "Y Ekseni")
        self.reports_tree = ttk.Treeview(reports_table_frame,
                                         columns=report_columns,
                                         show="headings",
                                         style="GPS.Treeview") # Same style can be used

        report_widths = [180, 60, 80, 120, 120, 70, 70] # Widths adjusted
        for i, col in enumerate(report_columns):
            self.reports_tree.heading(col, text=col)
            self.reports_tree.column(col, width=report_widths[i], anchor=tk.CENTER)

        report_tree_scroll_y = ttk.Scrollbar(reports_table_frame, orient=tk.VERTICAL, command=self.reports_tree.yview)
        report_tree_scroll_x = ttk.Scrollbar(reports_table_frame, orient=tk.HORIZONTAL, command=self.reports_tree.xview)
        self.reports_tree.configure(yscrollcommand=report_tree_scroll_y.set, xscrollcommand=report_tree_scroll_x.set)

        self.reports_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        report_tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        report_tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

    def show_frame(self, frame):
        """Shows the specified frame and hides others."""
        self.main_detection_frame.pack_forget()
        self.reports_frame.pack_forget()
        
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Update table when switching to reports screen
        if frame == self.reports_frame:
            self.update_reports_table()

    def draw_map_base(self):
        """Draws the base grid and direction indicators of the map canvas."""
        self.map_canvas.delete("all") # Clear existing drawings
        width = self.map_canvas.winfo_width()
        height = self.map_canvas.winfo_height()
        
        # Retry if canvas dimensions are not yet determined
        if width <= 1 or height <= 1:
            self.window.after(500, self.draw_map_base)
            return
        
        # Calculate center for new coordinate system
        center_x, center_y = width // 2, height // 2
        
        # Draw grid lines for the new coordinate system (-1.0 to 1.0)
        # X-axis lines (vertical)
        for i in range(-10, 11): # From -1.0 to 1.0 in 0.1 increments
            x_coord = center_x + (i * 0.1) * (width / 2)
            self.map_canvas.create_line(x_coord, 0, x_coord, height, fill="#0a3d2e", width=1)
            # Add X-axis labels
            if i % 2 == 0: # Label every 0.2 units
                label_x = x_coord
                label_y = center_y + 10 # Offset for visibility
                self.map_canvas.create_text(label_x, label_y, text=f"{i * 0.1:.1f}", fill="#ffffff", font=("Arial", 7))

        # Y-axis lines (horizontal)
        for i in range(-10, 11): # From -1.0 to 1.0 in 0.1 increments
            # Y-axis is inverted in Tkinter (0 at top, increasing downwards)
            # So, for -1.0 (bottom of our desired system), it's center_y + (1.0 * height/2)
            # For 1.0 (top of our desired system), it's center_y - (1.0 * height/2)
            y_coord = center_y - (i * 0.1) * (height / 2)
            self.map_canvas.create_line(0, y_coord, width, y_coord, fill="#0a3d2e", width=1)
            # Add Y-axis labels
            if i % 2 == 0: # Label every 0.2 units
                label_x = center_x - 15 # Offset for visibility
                label_y = y_coord
                self.map_canvas.create_text(label_x, label_y, text=f"{i * 0.1:.1f}", fill="#ffffff", font=("Arial", 7))

        # Center lines (X and Y axes)
        self.map_canvas.create_line(center_x, 0, center_x, height, fill="#1a5c42", width=2)
        self.map_canvas.create_line(0, center_y, width, center_y, fill="#1a5c42", width=2)
        
        # Main Direction indicators
        self.map_canvas.create_text(center_x, 15, text="KUZEY ↑", fill="#ffffff", font=("Arial", 10, "bold"))
        self.map_canvas.create_text(center_x, height-15, text="GÜNEY ↓", fill="#ffffff", font=("Arial", 10, "bold"))
        self.map_canvas.create_text(15, center_y, text="BATI ←", fill="#ffffff", font=("Arial", 10, "bold"), angle=90)
        self.map_canvas.create_text(width-15, center_y, text="DOĞU →", fill="#ffffff", font=("Arial", 10, "bold"), angle=90)
        
        # Intermediate Direction indicators
        offset = 25 # Offset for text position from corners
        self.map_canvas.create_text(offset, offset, text="KUZEYBATI ↖", fill="#ffffff", font=("Arial", 9, "bold"), anchor="nw")
        self.map_canvas.create_text(width - offset, offset, text="KUZEYDOĞU ↗", fill="#ffffff", font=("Arial", 9, "bold"), anchor="ne")
        self.map_canvas.create_text(offset, height - offset, text="GÜNEYBATI ↙", fill="#ffffff", font=("Arial", 9, "bold"), anchor="sw")
        self.map_canvas.create_text(width - offset, height - offset, text="GÜNEYDOĞU ↘", fill="#ffffff", font=("Arial", 9, "bold"), anchor="se")

        # Center point (Origin)
        self.map_canvas.create_oval(center_x-5, center_y-5, center_x+5, center_y+5, 
                                     fill="#ffff00", outline="#000000", width=2, tags="center")
    
    def update_map(self):
        """Updates drone positions on the map canvas."""
        self.map_canvas.delete("drone") # Clear previous drone drawings
        
        width = self.map_canvas.winfo_width()
        height = self.map_canvas.winfo_height()
        center_x, center_y = width//2, height//2
        
        for detection in self.current_data.get("detections", []):
            pos = detection.get("position", {})
            # Convert normalized coordinates (0.0-1.0) to the new -1.0 to 1.0 system
            # Assuming map_x and map_y from server are 0.0-1.0
            # Convert 0.0-1.0 to -1.0 to 1.0 range: (val * 2) - 1
            normalized_x_new_system = (pos.get("map_x", 0.5) * 2) - 1
            normalized_y_new_system = (pos.get("map_y", 0.5) * 2) - 1

            # Convert -1.0 to 1.0 coordinates to canvas pixels
            # X: -1.0 is left edge, 1.0 is right edge
            # Y: -1.0 is bottom edge, 1.0 is top edge (Tkinter Y is inverted)
            map_x_pixel = center_x + (normalized_x_new_system * (width / 2))
            map_y_pixel = center_y - (normalized_y_new_system * (height / 2)) # Invert Y for Tkinter
            
            drone_id = detection.get("id", "?")
            # Draw drone as a circle
            self.map_canvas.create_oval(map_x_pixel-6, map_y_pixel-6, map_x_pixel+6, map_y_pixel+6,
                                         fill="#ff0000", outline="#ffffff", width=2, tags="drone")
            # Write Drone ID
            self.map_canvas.create_text(map_x_pixel, map_y_pixel, text=str(drone_id), 
                                         fill="#ffffff", font=("Arial", 8, "bold"), tags="drone")
            # Draw dashed line from center to drone
            self.map_canvas.create_line(center_x, center_y, map_x_pixel, map_y_pixel, 
                                         fill="#00ff00", width=1, dash=(5, 5), tags="drone")
    
    def initiate_connection_from_ui(self):
        """Gets IP and Port from UI input fields and initiates connection."""
        host = self.ip_entry.get()
        port_str = self.port_entry.get()

        if not host:
            self.show_message_box("Bağlantı Hatası", "Lütfen sunucu IP adresini girin.", "error")
            return

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Port 1-65535 arasında olmalıdır.")
        except ValueError:
            self.show_message_box("Bağlantı Hatası", "Geçerli bir port numarası girin (örn: 8888).", "error")
            return
        
        # Close existing socket (if any)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.connected = False
            self.socket = None # Reset socket

        self.connection_status.config(text="🔄 Bağlanıyor...", fg="#ffff00")
        self.server_info.config(text=f"Hedef: {host}:{port}")
        self.connect_to_server(host, port)

    def connect_to_server(self, host, port):
        """Attempts to connect to the specified server."""
        def connect_thread():
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0) # Connection timeout
                self.socket.connect((host, port))
                self.connected = True
                
                self.window.after(0, lambda: self.connection_status.config(
                    text="✅ Bağlandı", fg="#00ff00"))
                self.window.after(0, lambda: self.server_info.config(
                    text=f"Bağlı: {host}:{port}"))
                
                # Start listening for data from the server
                threading.Thread(target=self.listen_server, daemon=True).start()
            except Exception as e: # Catch connection errors
                self.connected = False
                self.window.after(0, lambda: self.connection_status.config(
                    text="❌ Bağlantı Hatası", fg="#ff0000"))
                self.window.after(0, lambda: self.server_info.config(
                    text=f"Hedef: {host}:{port} (Bağlantı Hatası)"))
                print(f"Bağlantı hatası: {e}") # Print error to console
        
        threading.Thread(target=connect_thread, daemon=True).start()
        
    def listen_server(self):
        """Listens for and processes data from the server."""
        buffer = ""
        while self.connected and self.running:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    # If server closed connection
                    break
                buffer += data
                while '\n' in buffer: # Read line by line
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            self.current_data = json.loads(line) # Parse JSON data
                            self.window.after(0, self.update_ui) # Update UI (on main thread)
                            self.window.after(0, self.add_to_history) # Add to history
                        except json.JSONDecodeError:
                            print(f"JSON Parsing Error: {line}") # Log invalid JSON
                            pass
            except socket.timeout:
                # Continue listening in case of timeout
                continue
            except ConnectionResetError:
                print("Server reset connection.")
                break
            except Exception as e:
                print(f"Data reception error: {e}")
                break
                
        # Update status when connection is lost
        self.connected = False
        self.window.after(0, lambda: self.connection_status.config(
            text="❌ Bağlantı Kesildi", fg="#ff0000"))
        self.window.after(0, lambda: self.server_info.config(
            text=f"Bağlı Değil"))
        
        # Attempt to reconnect automatically if application is still running
        if self.running:
            threading.Timer(3.0, self.reconnect).start() # Use reconnect logic
            
    def add_to_history(self):
        """Adds current detection data to history."""
        timestamp = self.current_data.get("timestamp", "--")
        threat_level = self.current_data.get("threat_level", "YOK")

        for detection in self.current_data.get("detections", []):
            pos = detection.get("position", {})
            # Create a separate record for each detection
            history_entry = {
                "timestamp": timestamp,
                "id": detection.get("id", "-"),
                "confidence": detection.get("confidence", 0),
                "zone": pos.get("zone", "-"),
                "threat_level": threat_level, # Add general threat level
                "map_x": pos.get("map_x", 0.5), # X-axis info added
                "map_y": pos.get("map_y", 0.5)  # Y-axis info added
            }
            self.detection_history.append(history_entry)

    def update_ui(self):
        """Updates the user interface based on incoming data."""
        data = self.current_data
        threat_colors = {
            "YOK": "#00ff00",
            "DUSUK": "#00ff00", 
            "ORTA SEVİYE": "#ff8800",
            "YUKSEK TEHLİKE": "#ff0000"
        }
        # Update threat level and color
        self.threat_level_label.config(
            text=f"TEHLİKE: {data.get('threat_level', 'YOK')}",
            fg=threat_colors.get(data.get('threat_level', 'YOK'), "#ffffff")
        )
        # Update drone count
        self.drone_count_label.config(text=f"Drone: {data.get('drone_count', 0)}")
        # Update timestamp
        self.timestamp_label.config(text=f"Son Güncelleme: {data.get('timestamp', '--')}")
        
        # Update "FIRE" button state
        if data.get("fire_authorized", False):
            self.fire_button.config(state=tk.NORMAL, bg="#ff0000")
        else:
            self.fire_button.config(state=tk.DISABLED, bg="#666666")
        
        self.update_table() # Update detection table on main screen
        self.update_map()   # Update map
    
    def update_table(self):
        """Updates the detection table on the main screen."""
        for item in self.drone_tree.get_children():
            self.drone_tree.delete(item) # Clear previous entries
        
        current_threat_level = self.current_data.get("threat_level", "YOK") # General threat level
        
        for detection in self.current_data.get("detections", []):
            pos = detection.get("position", {})
            # Convert 0.0-1.0 to -1.0 to 1.0 range for display
            display_x = (pos.get("map_x", 0.5) * 2) - 1
            display_y = (pos.get("map_y", 0.5) * 2) - 1 # Y-axis inverted for display (positive up)

            values = (
                f"D{detection.get('id', '-')}",
                current_threat_level, # Show general threat level for each drone
                f"{detection.get('confidence', 0):.1f}%",
                pos.get("zone", "-"),
                f"{display_x:.2f}", # X-axis info added, 2 decimal places
                f"{display_y:.2f}"  # Y-axis info added, 2 decimal places
            )
            self.drone_tree.insert("", tk.END, values=values) # Add new entries

    def update_reports_table(self):
        """Updates the historical detection table on the reports screen."""
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item) # Clear previous entries
        
        # Sort historical records from newest to oldest
        sorted_history = sorted(self.detection_history, key=lambda x: x['timestamp'], reverse=True)

        for entry in sorted_history:
            # Convert 0.0-1.0 to -1.0 to 1.0 range for display
            display_x = (entry.get("map_x", 0.5) * 2) - 1
            display_y = (entry.get("map_y", 0.5) * 2) - 1 # Y-axis inverted for display (positive up)

            values = (
                entry.get("timestamp", "--"),
                f"D{entry.get('id', '-')}",
                f"{entry.get('confidence', 0):.1f}%",
                entry.get("zone", "-"),
                entry.get("threat_level", "YOK"),
                f"{display_x:.2f}", # X-axis info added, 2 decimal places
                f"{display_y:.2f}"  # Y-axis info added, 2 decimal places
            )
            self.reports_tree.insert("", tk.END, values=values) # Add new entries
    
    def fire_command(self):
        """Sends the 'FIRE' command to the server."""
        if not self.connected:
            self.show_message_box("Hata", "Sunucuya bağlı değilsiniz!", "error")
            return
        try:
            command = {
                "command": "FIRE",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "client_id": "gps_client_1"
            }
            self.socket.send((json.dumps(command) + "\n").encode('utf-8'))
            self.show_message_box("Komut Gönderildi", "🎯 ATEŞ ETİ komutu gönderildi!", "info")
        except Exception as e:
            self.show_message_box("Hata", f"Komut gönderilemedi: {str(e)}", "error")
    
    def reconnect(self):
        """Attempts to reconnect using the current IP/Port values from the UI."""
        if self.connected:
            try:
                self.socket.close()
            except:
                pass
            self.connected = False
            self.socket = None # Reset socket
            
        host = self.ip_entry.get()
        port_str = self.port_entry.get()

        if not host:
            self.show_message_box("Bağlantı Hatası", "Yeniden bağlanmak için lütfen sunucu IP adresini girin.", "error")
            self.connection_status.config(text="❌ Bağlantı Hatası", fg="#ff0000")
            return

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("Port 1-65535 arasında olmalıdır.")
        except ValueError:
            self.show_message_box("Bağlantı Hatası", "Yeniden bağlanmak için geçerli bir port numarası girin.", "error")
            self.connection_status.config(text="❌ Bağlantı Hatası", fg="#ff0000")
            return

        self.connection_status.config(text="🔄 Yeniden Bağlanıyor...", fg="#ffff00")
        self.server_info.config(text=f"Hedef: {host}:{port}")
        threading.Thread(target=self.connect_to_server, args=(host, port), daemon=True).start()
    
    def show_message_box(self, title, message, type="info"):
        """Custom message box function (uses Tkinter's messagebox)."""
        if type == "info":
            messagebox.showinfo(title, message)
        elif type == "error":
            messagebox.showerror(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)

    def on_closing(self):
        """Called when the window is closed, cleans up connection and threads."""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR) # Attempt to gracefully close socket
                self.socket.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
        self.window.destroy() # Close Tkinter window
    
    def run(self):
        """Starts the Tkinter main loop."""
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

if __name__ == "__main__":
    try:
        client = DroneDetectionClient()
        client.run()
    except KeyboardInterrupt:
        print("\n✋ Program stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        print("👋 Program terminated")

