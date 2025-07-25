import socket #sunucuya bağlanmak için tcp/ıp haberleşmesi sağlıyor
import tkinter as tk 
from tkinter import ttk, messagebox, Canvas # arayüz (gui) oluştrumak için
import json #sunucudan gelen verileri json formatında alıp işlemek için 
import threading #ağ işlemlerini ve gui'yi eş zamanlı çalıştırmak için-program donmasın diye
from datetime import datetime #zaman damagası eklemek için 
import collections # veri yapısını kullanarak geçmiş tespitleri bellekte verimli bir şekilde tutmak için

class DroneDetectionClient:  #programın istemci(client) tarafını temsil eden ana sınıf
    def __init__(self):  # init fonk sınıf ilk çalıştırıldığında yapılan ayarlar
        # Default IP and Port values, will be displayed in the UI input fields
        self.default_server_host = '127.0.0.1' # IP of your own computer--varsayılan sunucu ıp'si localhost
        self.default_server_port = 8888 #varsayılan sunucu portu

        self.socket = None #tcp bağlantısı için soket enesnesi henüz olmuşmamış
        self.connected = False #başlangıçta sunucuya bağlı değil
        self.running = True #program çalışıyor bayrağı
        
        # Login credentials
        self.correct_username = "yaren" 
        self.correct_password = "1234"
        self.login_attempts = 0 #yanlış giriş deneme sayısını takipe eder, max 3 deneme
        self.max_attempts = 3
        self.logged_in = False #başlangıçta kullanıcı giriş yapmamış
        
        # aşağıdaki kodda current_data ile drone verileri için güncel durum verilmiş
        self.current_data = {
            "drone_count": 0, #algılanan drone sayısı
            "threat_level": "YOK", #tehdit seviyesi başangıçta--yok
            "detections": [], #tespit edilen drone listesi
            "timestamp": "", #son alınan verinin zaman damgası
            "fire_authorized": False #ateş etme yetisi
        }
        
        # Using deque to store detection history.
        # This keeps memory usage under control by maintaining a fixed size.
        # detection_history ile geçmiş veriler tutuluyor

        self.detection_history = collections.deque(maxlen=1000) # Keep last 1000 records----son 1000 tespiti saklar,eskiler otomatik silinir
        
        self.setup_login_ui() #program açıldığında önce giriş ekranı bulunur
        
    def setup_login_ui(self): #giriş ekranı arayüzü
        """Sets up the login screen user interface."""
        self.window = tk.Tk() 
        self.window.title("Drone Tespit Sistemi - Giriş")
        self.window.geometry("500x400")
        self.window.configure(bg="#1a1a1a")
        #tkinter kullanrak verilen başlıkta pencere oluşturur, ekranın ortasında konumlandırılır

        # Center the window on screen
        self.window.geometry("+{}+{}".format(
            (self.window.winfo_screenwidth() // 2) - 250,
            (self.window.winfo_screenheight() // 2) - 200
        ))
        
        # Login frame---tüm giriş bilgilerini içereen bir frame oluşturulur
        self.login_frame = tk.Frame(self.window, bg="#1a1a1a")
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(self.login_frame,
                              text="🛡️ DRONE TESPİT SİSTEMİ",
                              font=("Arial", 20, "bold"),
                              bg="#1a1a1a", fg="#00ff00")
        title_label.pack(pady=30)
        
        subtitle_label = tk.Label(self.login_frame,
                                 text="SİSTEM GİRİŞİ",
                                 font=("Arial", 14, "bold"),
                                 bg="#1a1a1a", fg="#ffffff")
        subtitle_label.pack(pady=10)
        
        # Login container
        login_container = tk.Frame(self.login_frame, bg="#2c2c2c", relief=tk.RAISED, bd=2)
        login_container.pack(pady=20, padx=50, fill=tk.X)
        
        # Username
        username_label = tk.Label(login_container,
                                 text="Kullanıcı Adı:",
                                 font=("Arial", 12, "bold"),
                                 bg="#2c2c2c", fg="#ffffff")
        username_label.pack(pady=(20, 5))
        
        self.username_entry = tk.Entry(login_container,
                                      font=("Arial", 12),
                                      bg="#3a3a3a", fg="#ffffff",
                                      insertbackground="#ffffff",
                                      justify=tk.CENTER,
                                      width=20)
        self.username_entry.pack(pady=5)
        
        # Password
        password_label = tk.Label(login_container,
                                 text="Şifre:",
                                 font=("Arial", 12, "bold"),
                                 bg="#2c2c2c", fg="#ffffff")
        password_label.pack(pady=(15, 5))
        
        self.password_entry = tk.Entry(login_container,
                                      font=("Arial", 12),
                                      bg="#3a3a3a", fg="#ffffff",
                                      insertbackground="#ffffff",
                                      justify=tk.CENTER,
                                      width=20,
                                      show="*")
        self.password_entry.pack(pady=5)
        
        # Login button
        self.login_button = tk.Button(login_container,
                                     text="🔐 GİRİŞ YAP",
                                     font=("Arial", 12, "bold"),
                                     bg="#008000", fg="#ffffff",
                                     command=self.attempt_login,
                                     width=15,
                                     height=2)
        self.login_button.pack(pady=20)
        
        # Status label---giriş denemelerin sonuçalarını kullanıcıya gösterir (hatalı,eksik vs)
        self.login_status = tk.Label(login_container,
                                    text="",
                                    font=("Arial", 10),
                                    bg="#2c2c2c", fg="#ffff00")
        self.login_status.pack(pady=5)
        
        # Attempt counter----kaç deneme hakkı kaldığını sayar
        self.attempt_label = tk.Label(login_container,
                                     text=f"Kalan deneme hakkı: {self.max_attempts - self.login_attempts}",
                                     font=("Arial", 9),
                                     bg="#2c2c2c", fg="#cccccc")
        self.attempt_label.pack(pady=(5, 20))
        
        # Bind Enter key to login
        self.username_entry.bind('<Return>', lambda event: self.attempt_login())
        self.password_entry.bind('<Return>', lambda event: self.attempt_login())
        
        # Focus on username entry
        self.username_entry.focus()
        
        # Set window close protocol
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def attempt_login(self): #giriş denemesi kontrolü
        """Attempts to log in with provided credentials."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.login_status.config(text="❌ Kullanıcı adı ve şifre gerekli!", fg="#ff0000")
            return
        
        if username == self.correct_username and password == self.correct_password:
            # Successful login
            self.logged_in = True
            self.login_status.config(text="✅ Giriş başarılı! Sistem açılıyor...", fg="#00ff00")
            self.window.after(1000, self.show_main_system)
        else:
            # Failed login
            self.login_attempts += 1
            remaining_attempts = self.max_attempts - self.login_attempts
            
            if remaining_attempts > 0:
                self.login_status.config(text=f"❌ Hatalı kullanıcı adı veya şifre!", fg="#ff0000")
                self.attempt_label.config(text=f"Kalan deneme hakkı: {remaining_attempts}")
                # Clear password field
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus()
            else:
                # Maximum attempts reached
                self.login_status.config(text="🚫 Maksimum deneme sayısına ulaşıldı!", fg="#ff0000")
                self.attempt_label.config(text="Sistem kapatılıyor...", fg="#ff0000")
                self.login_button.config(state=tk.DISABLED, bg="#666666")
                self.username_entry.config(state=tk.DISABLED)
                self.password_entry.config(state=tk.DISABLED)
                self.window.after(2000, self.on_closing)
    
    def show_main_system(self): #ana sistem ekranı açma
        """Shows the main drone detection system after successful login."""
        # Clear login frame
        self.login_frame.destroy() # bu komut ile giriş ekranı kaldırılır
        
        # Resize and recenter window for main system
        self.window.title("Drone Tespit Sistemi")
        self.window.geometry("1400x800")
        self.window.geometry("+{}+{}".format(
            (self.window.winfo_screenwidth() // 2) - 700,
            (self.window.winfo_screenheight() // 2) - 400
        ))
        
        # Setup main system UI
        self.setup_main_ui() #ana arayüzü kuran setup_mainui() fonksiyonu çağrılır
        
    def setup_main_ui(self):
        """Sets up the main system user interface (Tkinter) and places its components."""
        # Main container frame-----main container, tüm ana ekran bileşenleri için arka plan çerçevesi,tüm ekranı kaplar
        main_container = tk.Frame(self.window, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Top Navigation and Title Frame --- header frame-->üst gezinme çubuğu
        header_frame = tk.Frame(main_container, bg="#1a1a1a")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(header_frame, 
                               text="🛡️ DRONE TESPİT SİSTEMİ",
                               font=("Arial", 18, "bold"),
                               bg="#1a1a1a", fg="#00ff00")
        title_label.pack(side=tk.LEFT, padx=10)

        # User info and logout
        user_info_frame = tk.Frame(header_frame, bg="#1a1a1a") #giriş yapan kullanıcı adı gösterilir
        user_info_frame.pack(side=tk.RIGHT, padx=10)
        
        user_label = tk.Label(user_info_frame,
                             text=f"👤 Kullanıcı: {self.correct_username}",
                             font=("Arial", 10),
                             bg="#1a1a1a", fg="#ffffff")
        user_label.pack(side=tk.LEFT, padx=(0, 10))
        
        logout_button = tk.Button(user_info_frame,
                                 text="🚪 Çıkış",
                                 font=("Arial", 10, "bold"),
                                 bg="#cc0000", fg="#ffffff",
                                 command=self.logout)
        logout_button.pack(side=tk.LEFT) #kullanıcı çıkış komutu

        # Navigation buttons----navigasyon butonları
        nav_button_frame = tk.Frame(header_frame, bg="#1a1a1a")
        nav_button_frame.pack(side=tk.RIGHT, padx=(0, 150))

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

        # main_detection_frame---drone tespit ekranı   reports_frame----raporlar ekranı,başlangıçta gizli
        # --- End of Top Navigation and Title Frame ---
        
        # Main detection screen frame
        self.main_detection_frame = tk.Frame(main_container, bg="#1a1a1a")
        self.main_detection_frame.pack(fill=tk.BOTH, expand=True)

        # Reports screen frame (initially hidden)
        self.reports_frame = tk.Frame(main_container, bg="#1a1a1a")
        # self.reports_frame.pack_forget() # Keep hidden initially

        # Left panel (Connection, Map, Control) - placed inside main_detection_frame
        #sol panel bağlantı ayarları, kontrol ve harita bölümü için ayrılmış
        left_panel = tk.Frame(self.main_detection_frame, bg="#2c2c2c", relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Right panel (Drone Details, Table) - placed inside main_detection_frame
        right_panel = tk.Frame(self.main_detection_frame, bg="#2c2c2c", relief=tk.RAISED, bd=2, width=500)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_panel.pack_propagate(False) # Prevents the right panel's size from changing based on content
        
        # --- Connection Settings Frame ---bağlantı ayarları
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
        self.server_info = tk.Label(connection_frame, #self.server_info etiketi hedef sunucunun ıp'sini ev portunu gösterir
                                   text=f"Hedef: {self.default_server_host}:{self.default_server_port}",
                                   font=("Arial", 9),
                                   bg="#2c2c2c", fg="#cccccc")
        self.server_info.pack(side=tk.RIGHT, padx=5)
        # --- End of Connection Settings Frame ---

        # Map View Frame----harita görünümü
        map_frame = tk.LabelFrame(left_panel,
                                 text="🗺️ Harita Görünümü",
                                 font=("Arial", 12, "bold"),
                                 bg="#2c2c2c", fg="#ffffff")
        map_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.map_canvas = Canvas(map_frame, bg="#0d4f3c", width=600, height=400)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        #harita arka paln koyu yeşil, 600x400 piksel pencere

        # Control Panel Frame----kontrol paneli
        control_frame = tk.LabelFrame(left_panel,
                                     text="🎯 Kontrol Paneli",
                                     font=("Arial", 12, "bold"),
                                     bg="#2c2c2c", fg="#ffffff")
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_row = tk.Frame(control_frame, bg="#2c2c2c")
        status_row.pack(fill=tk.X, padx=5, pady=5)
        
        self.threat_level_label = tk.Label(status_row,  #başlangıçta tehlike yok yazısı olcak
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
                                     state=tk.DISABLED, # Initially disabled--başlangıçta devre dışı
                                     command=self.fire_command, 
                                     height=2,
                                     relief=tk.RAISED)
        self.fire_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.reconnect_button = tk.Button(button_row,
                                         text="🔄 Yeniden Bağlan",
                                         font=("Arial", 10),
                                         bg="#0066cc",
                                         fg="#ffffff",
                                         command=self.reconnect) # Reconnect function---bağlantı koparsa tekrar denemek için
        self.reconnect_button.pack(side=tk.RIGHT)
        
        # Drone Details Header----drone detayları bölümü
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
        
        # Treeview style settings----ttk.treeview kullanılarak sütunlar halinde oluşturulmuş
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
        
        # Scrollbar -----kaydırma çubuğu--tabloyu dikey kaydırmak için eklenmiş
        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.drone_tree.yview)
        self.drone_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.drone_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Last Update Label----sağ panelde en son alınan verini zaman damgasını gösterir
        self.timestamp_label = tk.Label(right_panel,
                                         text="Son Güncelleme: --",
                                         font=("Arial", 9),
                                         bg="#2c2c2c", fg="#cccccc")
        self.timestamp_label.pack(pady=5)
        
        # --- Reports Screen Setup ---rapoların tutulduğu ikinci ekran
        self.setup_reports_ui()

        # Delayed call to draw map base----Harita tabanını çizmek için gecikmeli çağrı
        self.window.after(500, self.draw_map_base)

        # Show Home Screen initially-----Başlangıçta Ana Ekranı Göster
        self.show_frame(self.main_detection_frame)
    
    def logout(self):
        """Logs out the user and returns to login screen."""
        if messagebox.askyesno("Çıkış", "Sistemden çıkmak istediğinizden emin misiniz?"):
            # Close connection if exists
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.connected = False
                self.socket = None
            
            # Reset login variables
            self.logged_in = False
            self.login_attempts = 0
            
            # Close current window and restart login
            self.window.destroy()
            self.__init__()
            self.run()
    
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

        report_widths = [180, 60, 80, 120, 120, 70, 70] # Widths adjusted----Genişlikler ayarlandı
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

    def draw_map_base(self):  #harita çizimi
        """Draws the base grid and direction indicators of the map canvas."""
        self.map_canvas.delete("all") # Clear existing drawings--eski çizimler sıfırlanır
        width = self.map_canvas.winfo_width()
        height = self.map_canvas.winfo_height()
        
        # Retry if canvas dimensions are not yet determined---pencere boyutları belirlenmemişse (width/height <= 1) yarım sn sonra tekrar denenir
        if width <= 1 or height <= 1:
            self.window.after(500, self.draw_map_base)
            return
        
        # Calculate center for new coordinate system
        center_x, center_y = width // 2, height // 2
        
        # Draw grid lines for the new coordinate system (-1.0 to 1.0)
        # X-axis lines (vertical)
        for i in range(-10, 11): # From -1.0 to 1.0 in 0.1 increments-----1,0'dan 1,0'a 0,1 artışlarla
            x_coord = center_x + (i * 0.1) * (width / 2)
            self.map_canvas.create_line(x_coord, 0, x_coord, height, fill="#0a3d2e", width=1)
            # Add X-axis labels
            if i % 2 == 0: # Label every 0.2 units----Her 0,2 birimde bir etiketleyin
                label_x = x_coord
                label_y = center_y + 10 # Offset for visibility---Görünürlük için ofset
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
        
        # x ve y ekseni -1 ve 1 arasında 0.1 aralıklarla çizilir, her 0.2 birimde eksen numarası yazılır
        # Center lines (X and Y axes)---merkez çizgileri haritanın tam ortasına eksenler çizilir, yeşil renkte, ana ara yönler ve orjin belirlenir
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
    
    def update_map(self):  #haritada drone konumları güncellenir, önceki eski drone çizimleri silinir
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
            map_x_pixel = center_x + (normalized_x_new_system * (width / 2)* -1)
            map_y_pixel = center_y - (normalized_y_new_system * (height / 2)* -1) # Invert Y for Tkinter
            
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
            #sunucudan gelen 0-1 aralığındaki değerler (-1)-1 arasına dönüştürülür
            # her drone kırmızı daire olarak çizilir, ortasına ıd numarası yazılır, merkezden drone yeşil çizgi çizilir

    def initiate_connection_from_ui(self):
        """Gets IP and Port from UI input fields and initiates connection."""
            # ıp ve port değerleri kullanıcıdan alınır (self.ip_entry ve self.port_entry), kullanıcı giriş yapamamışsa hata mesajı gönderilir
            # ip boşsa veya port geçersizse hata mesajı çıkar, daha önce soket varsa kapatılır, durum etiketi "bağlanıyor" olarak güncellenir
        if not self.logged_in:
            self.show_message_box("Erişim Hatası", "Bu işlem için giriş yapmanız gerekli!", "error")
            return
            
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
         #sunucuya bağlanmayı dener
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
                while '\n' in buffer: # Read line by line---veriler satır satır ayrılarak alınır
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            self.current_data = json.loads(line) # Parse JSON data
                            self.window.after(0, self.update_ui) # Update UI (on main thread)
                            self.window.after(0, self.add_to_history) # Add to history
                        except json.JSONDecodeError:
                            print(f"JSON Parsing Error: {line}") # Log invalid JSON--- her satır json formatında çözümlenir
                            pass
            except socket.timeout:
                # self.current_data güncellenir, update_ui() çağrılarak arayüz yenilenir, add_to_history() ile veri geçmişe eklenir
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
        #bağlantı koparsa durum "bağlantı kesildi" olarak güncellenir 3sn içinde yeniden bağlanma denenir.
            
    def add_to_history(self):  #alınan veriyi geçmiş listesine self_detection_history ekler
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
            # update_ui(self) tehdit seviyesi renge göre güncellenir. drone sayısı ve görülme zamanı yenilenir, ateş et butonu aktifleşir/pasifleşir
            # update_table() ve update_map() çağrılarak tablo ve harita güncellenir.
        """Updates the user interface based on incoming data."""
        if not self.logged_in:
            return
            
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
        if not self.logged_in:
            self.show_message_box("Erişim Hatası", "Bu işlem için giriş yapmanız gerekli!", "error")
            return
            
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
        if not self.logged_in:
            return
            
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

    def on_closing(self):  #pencere kapatıldığında bağlantıyı düzgün kapatır
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
