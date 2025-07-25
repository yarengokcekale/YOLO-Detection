import cv2
from ultralytics import YOLO
import pygame
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from PIL import Image, ImageTk
import numpy as np
import socket
import threading
import json
import time
import pandas as pd
from tkinter import filedialog, messagebox

# Model ve ses dosyası yolları
model_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\runs\detect\train\weights\best.pt"
sound_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\alert.wav"

# Modeli yükle
model = YOLO(model_path)

# Pygame ses sistemi başlat
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load(sound_path)

# TCP Server ayarları
SERVER_HOST = '127.0.0.1'  # localhost
SERVER_PORT = 8888
connected_clients = []

# Global değişkenler
current_drone_data = {
    "drone_count": 0,
    "threat_level": "YOK",
    "detections": [],
    "timestamp": "",
    "fire_authorized": False
}

# Raporlar için geçmiş veriler
detection_history = []
max_history = 1000  # Son 1000 tespiti sakla

def play_alert():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play()

def start_server():
    """TCP sunucusunu başlat"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    
    print(f"Sunucu {SERVER_HOST}:{SERVER_PORT} adresinde başlatıldı...")
    
    def handle_client(client_socket, client_address):
        """İstemci bağlantılarını yönet"""
        print(f"Yeni bağlantı: {client_address}")
        connected_clients.append(client_socket)
        
        try:
            while True:
                # İstemciden veri bekle (ateş emri vs.)
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if data:
                        message = json.loads(data)
                        if message.get("command") == "FIRE":
                            print(f"ATEŞ EMRİ alındı - İstemci: {client_address}")
                            # Burada gerçek ateş etme işlemi yapılabilir
                            
                except socket.timeout:
                    continue
                except:
                    break
                    
        except Exception as e:
            print(f"İstemci hatası {client_address}: {e}")
        finally:
            if client_socket in connected_clients:
                connected_clients.remove(client_socket)
            client_socket.close()
            print(f"Bağlantı kesildi: {client_address}")
    
    def accept_connections():
        """Yeni bağlantıları kabul et"""
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                client_socket.settimeout(1.0)  # Timeout ayarla
                client_thread = threading.Thread(
                    target=handle_client, 
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                print(f"Sunucu hatası: {e}")
                break
    
    # Bağlantı kabul etme thread'ini başlat
    accept_thread = threading.Thread(target=accept_connections)
    accept_thread.daemon = True
    accept_thread.start()

def broadcast_drone_data():
    """Drone verilerini tüm istemcilere gönder"""
    if not connected_clients:
        return
        
    message = json.dumps(current_drone_data) + "\n"
    
    for client in connected_clients[:]:  # Kopya liste kullan
        try:
            client.send(message.encode('utf-8'))
        except Exception as e:
            print(f"İstemciye veri gönderme hatası: {e}")
            if client in connected_clients:
                connected_clients.remove(client)

# Tkinter SCADA arayüzü oluştur
window = tk.Tk()
window.title("Drone Tespit Server - Raporlar")
window.geometry("1400x900")

# Ana çerçeve
main_frame = tk.Frame(window)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Üst kısım - Sistem Durumu
status_frame = tk.LabelFrame(main_frame, text="Sistem Durumu", font=("Arial", 14, "bold"), height=120)
status_frame.pack(fill=tk.X, pady=(0, 10))
status_frame.pack_propagate(False)

# Durum bilgileri için grid layout
status_grid = tk.Frame(status_frame)
status_grid.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Sol kolon - Server bilgileri
left_status = tk.Frame(status_grid)
left_status.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

server_label = tk.Label(left_status, text=f"Server: {SERVER_HOST}:{SERVER_PORT}", 
                       font=("Arial", 11, "bold"), fg="blue")
server_label.pack(anchor="w")

client_count_label = tk.Label(left_status, text="Bağlı İstemci: 0", font=("Arial", 11))
client_count_label.pack(anchor="w")

system_time_label = tk.Label(left_status, text="", font=("Arial", 11))
system_time_label.pack(anchor="w")

# Orta kolon - Tespit durumu
middle_status = tk.Frame(status_grid)
middle_status.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)

threat_level_label = tk.Label(middle_status, text="Tehlike Seviyesi: YOK", 
                             font=("Arial", 12, "bold"), fg="green")
threat_level_label.pack(anchor="w")

active_drones_label = tk.Label(middle_status, text="Aktif Drone: 0", font=("Arial", 11))
active_drones_label.pack(anchor="w")

last_detection_label = tk.Label(middle_status, text="Son Tespit: -", font=("Arial", 11))
last_detection_label.pack(anchor="w")

# Sağ kolon - Sistem kontrolleri
right_status = tk.Frame(status_grid)
right_status.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

camera_status_label = tk.Label(right_status, text="Kamera: Aktif", 
                              font=("Arial", 11), fg="green")
camera_status_label.pack(anchor="w")

ai_model_label = tk.Label(right_status, text="AI Model: Yüklü", 
                         font=("Arial", 11), fg="green")
ai_model_label.pack(anchor="w")

alert_system_label = tk.Label(right_status, text="Alarm Sistemi: Hazır", 
                             font=("Arial", 11), fg="green")
alert_system_label.pack(anchor="w")

# Ana içerik alanı - Notebook için
content_frame = tk.Frame(main_frame)
content_frame.pack(fill=tk.BOTH, expand=True)

# Notebook (sekmeli arayüz)
notebook = ttk.Notebook(content_frame)
notebook.pack(fill=tk.BOTH, expand=True)

# Sekme 1: Anlık Tespitler
current_frame = tk.Frame(notebook)
notebook.add(current_frame, text="Anlık Tespitler")

# Anlık tespitler için treeview
current_tree_frame = tk.Frame(current_frame)
current_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

current_tree_scroll = tk.Scrollbar(current_tree_frame)
current_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

current_tree = ttk.Treeview(current_tree_frame, 
                           columns=("ID", "Güven", "Tehlike", "X_Koord", "Y_Koord", "Zaman"),
                           show="headings",
                           yscrollcommand=current_tree_scroll.set)

current_tree_scroll.config(command=current_tree.yview)

# Sütun başlıkları ve genişlikleri
columns_config = [
    ("ID", 80),
    ("Güven", 100),
    ("Tehlike", 120),
    ("X_Koord", 100),
    ("Y_Koord", 100),
    ("Zaman", 180)
]

for col, width in columns_config:
    current_tree.heading(col, text=col)
    current_tree.column(col, width=width, anchor="center")

current_tree.pack(fill=tk.BOTH, expand=True)

# Sekme 2: Tespit Geçmişi
history_frame = tk.Frame(notebook)
notebook.add(history_frame, text="Tespit Geçmişi")

# Geçmiş için kontroller
history_controls = tk.Frame(history_frame)
history_controls.pack(fill=tk.X, padx=10, pady=5)

clear_history_btn = tk.Button(history_controls, text="Geçmişi Temizle", 
                             command=lambda: clear_detection_history())
clear_history_btn.pack(side=tk.LEFT)

export_excel_btn = tk.Button(history_controls, text="Excel'e Aktar", 
                            command=lambda: export_to_excel())
export_excel_btn.pack(side=tk.LEFT, padx=(10, 0))

export_txt_btn = tk.Button(history_controls, text="TXT'ye Aktar", 
                          command=lambda: export_to_txt())
export_txt_btn.pack(side=tk.LEFT, padx=(10, 0))

# Geçmiş için treeview
history_tree_frame = tk.Frame(history_frame)
history_tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

history_tree_scroll = tk.Scrollbar(history_tree_frame)
history_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

history_tree = ttk.Treeview(history_tree_frame,
                           columns=("ID", "Güven", "Tehlike", "X_Koord", "Y_Koord", "Zaman"),
                           show="headings",
                           yscrollcommand=history_tree_scroll.set)

history_tree_scroll.config(command=history_tree.yview)

for col, width in columns_config:
    history_tree.heading(col, text=col)
    history_tree.column(col, width=width, anchor="center")

history_tree.pack(fill=tk.BOTH, expand=True)

# Sekme 3: İstatistikler
stats_frame = tk.Frame(notebook)
notebook.add(stats_frame, text="İstatistikler")

# İstatistik göstergeleri
stats_grid = tk.Frame(stats_frame)
stats_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

# İstatistik kartları
stat_cards = []
stat_texts = ["Toplam Tespit", "Yüksek Tehlike", "Orta Seviye", "Düşük Tehlike", 
              "Ortalama Güven", "Aktif Süre"]

for i in range(6):
    card_frame = tk.LabelFrame(stats_grid, text=stat_texts[i], font=("Arial", 12, "bold"))
    card_frame.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew", ipadx=20, ipady=20)
    
    value_label = tk.Label(card_frame, text="0", font=("Arial", 24, "bold"), fg="blue")
    value_label.pack()
    
    stat_cards.append(value_label)

# Grid ağırlıklarını ayarla
for i in range(2):
    stats_grid.grid_rowconfigure(i, weight=1)
for i in range(3):
    stats_grid.grid_columnconfigure(i, weight=1)

def clear_detection_history():
    """Tespit geçmişini temizle"""
    global detection_history
    detection_history.clear()
    update_history_tree()
    messagebox.showinfo("Başarılı", "Tespit geçmişi temizlendi!")

def export_to_excel():
    """Raporu Excel dosyasına aktar"""
    try:
        if not detection_history:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri bulunmuyor!")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel dosyası", "*.xlsx"), ("Tüm dosyalar", "*.*")],
            initialname=f"drone_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
        
        if filename:
            # Pandas DataFrame oluştur
            df = pd.DataFrame(detection_history)
            
            # Sütun sıralaması düzenle
            column_order = ['timestamp', 'id', 'confidence', 'threat_level', 'x_coord', 'y_coord', 'zone']
            df = df[column_order]
            
            # Sütun adlarını Türkçe yap
            df.columns = ['Tespit Zamanı', 'Drone ID', 'Güven Oranı (%)', 'Tehlike Seviyesi', 'X Koordinatı', 'Y Koordinatı', 'Bölge']
            
            # Excel'e kaydet
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Drone Tespitleri', index=False)
                
                # Çalışma sayfasını al ve biçimlendir
                worksheet = writer.sheets['Drone Tespitleri']
                
                # Sütun genişliklerini ayarla
                column_widths = [20, 12, 15, 18, 15, 15, 15]
                for i, width in enumerate(column_widths, 1):
                    worksheet.column_dimensions[chr(64+i)].width = width
                
                # Başlık satırını kalınlaştır
                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True)
            
            messagebox.showinfo("Başarılı", f"Rapor başarıyla Excel dosyasına kaydedildi:\n{filename}")
    except Exception as e:
        messagebox.showerror("Hata", f"Excel dosyası kaydedilirken hata oluştu:\n{str(e)}")

def export_to_txt():
    """Raporu TXT dosyasına aktar"""
    try:
        if not detection_history:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri bulunmuyor!")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Metin dosyası", "*.txt"), ("Tüm dosyalar", "*.*")],
            initialname=f"drone_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("DRONE TESPİT RAPORU\n")
                f.write("="*60 + "\n")
                f.write(f"Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Toplam Tespit: {len(detection_history)}\n\n")
                
                f.write(f"{'Tespit Zamanı':<20} {'ID':<8} {'Güven':<8} {'Tehlike':<15} {'X Koord':<10} {'Y Koord':<10} {'Bölge':<15}\n")
                f.write("-" * 95 + "\n")
                
                for detection in detection_history:
                    f.write(f"{detection['timestamp']:<20} ")
                    f.write(f"{detection['id']:<8} ")
                    f.write(f"{detection['confidence']:<8.1f} ")
                    f.write(f"{detection['threat_level']:<15} ")
                    f.write(f"{detection['x_coord']:<10.2f} ")
                    f.write(f"{detection['y_coord']:<10.2f} ")
                    f.write(f"{detection['zone']:<15}\n")
            
            messagebox.showinfo("Başarılı", f"Rapor başarıyla TXT dosyasına kaydedildi:\n{filename}")
    except Exception as e:
        messagebox.showerror("Hata", f"TXT dosyası kaydedilirken hata oluştu:\n{str(e)}")

def update_current_tree():
    """Anlık tespitler tablosunu güncelle"""
    # Mevcut verileri temizle
    for item in current_tree.get_children():
        current_tree.delete(item)
    
    # Yeni verileri ekle
    for detection in current_drone_data.get("detections", []):
        pos = detection["position"]
        
        # X ve Y koordinatlarını 0-1 aralığından -1 ile 1 aralığına çevir (client ile uyumlu)
        display_x = (pos.get("map_x", 0.5) * 2) - 1
        display_y = (pos.get("map_y", 0.5) * 2) - 1
        
        current_tree.insert("", "end", values=(
            f"D{detection['id']:03d}",
            f"%{detection['confidence']:.1f}",
            pos["distance"],  # Tehlike seviyesi (Çok Yakın, Yakın, vs.)
            f"{display_x:.2f}",
            f"{display_y:.2f}",
            current_drone_data.get("timestamp", "")
        ))

def update_history_tree():
    """Geçmiş tespitler tablosunu güncelle"""
    # Mevcut verileri temizle
    for item in history_tree.get_children():
        history_tree.delete(item)
    
    # Son tespitleri ekle (en yeniden eskiye)
    for detection in reversed(detection_history[-100:]):  # Son 100 kayıt
        history_tree.insert("", "end", values=(
            detection["id"],
            f"%{detection['confidence']:.1f}",
            detection["threat_level"],
            f"{detection['x_coord']:.2f}",
            f"{detection['y_coord']:.2f}",
            detection["timestamp"]
        ))

def update_statistics():
    """İstatistikleri güncelle"""
    total_detections = len(detection_history)
    high_threat = len([d for d in detection_history if "YÜKSEK TEHLİKE" in d["threat_level"]])
    medium_threat = len([d for d in detection_history if "ORTA SEVİYE" in d["threat_level"]])
    low_threat = len([d for d in detection_history if "DÜŞÜK TEHLİKE" in d["threat_level"] or d["threat_level"] == "Çok Yakın" or d["threat_level"] == "Yakın"])
    
    avg_confidence = 0
    if detection_history:
        avg_confidence = sum(d["confidence"] for d in detection_history) / len(detection_history)
    
    # Aktif süre hesaplama (program başlangıcından itibaren)
    if not hasattr(update_statistics, 'start_time'):
        update_statistics.start_time = datetime.now()
    
    active_time = datetime.now() - update_statistics.start_time
    active_hours = int(active_time.total_seconds() // 3600)
    active_minutes = int((active_time.total_seconds() % 3600) // 60)
    
    # İstatistik kartlarını güncelle
    stat_values = [
        str(total_detections),
        str(high_threat),
        str(medium_threat),
        str(low_threat),
        f"%{avg_confidence:.1f}",
        f"{active_hours:02d}:{active_minutes:02d}"
    ]
    
    for i, value in enumerate(stat_values):
        stat_cards[i].config(text=value)

# Kamera başlat (arka planda)
cap = cv2.VideoCapture(0)

def get_zone_name(center_x, center_y, frame_width, frame_height):
    """Koordinatlara göre bölge adını belirle"""
    # Ekranı 9 bölgeye ayır (3x3 grid)
    h_zone = "Batı" if center_x < frame_width/3 else ("Merkez" if center_x < 2*frame_width/3 else "Doğu")
    v_zone = "Kuzey" if center_y < frame_height/3 else ("Merkez" if center_y < 2*frame_height/3 else "Güney")
    
    if v_zone == "Merkez" and h_zone == "Merkez":
        return "Merkez"
    elif v_zone == "Merkez":
        return h_zone
    elif h_zone == "Merkez":
        return v_zone
    else:
        return f"{v_zone} {h_zone}"

def background_detection():
    """Arka planda drone tespiti yap"""
    global current_drone_data, detection_history
    
    ret, frame = cap.read()
    if not ret:
        return

    results = model(frame)
    
    threat_level = "YOK"
    alert_triggered = False
    detections = []
    
    frame_height, frame_width = frame.shape[:2]

    for i, result in enumerate(results):
        for j, box in enumerate(result.boxes):
            cls_id = int(box.cls[0].item())
            cls_name = model.names[cls_id]

            if cls_name.lower() != "drone":
                continue

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            width = x2 - x1
            height = y2 - y1
            area = width * height
            confidence = box.conf[0].item() * 100

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            
            # GPS koordinatlarını simüle et
            base_lat = 39.7767  # Eskişehir enlem
            base_lon = 30.5206  # Eskişehir boylam

            lat_offset = ((center_y - frame_height/2) / (frame_height/2)) * 0.01
            lon_offset = ((center_x - frame_width/2) / (frame_width/2)) * 0.01

            drone_lat = base_lat + lat_offset
            drone_lon = base_lon + lon_offset

            #lat_offset = ((center_y - frame_height/2) / (frame_height/2)) * 0.01
            #lon_offset = ((center_x - frame_width/2) / (frame_width/2)) * 0.01
            
            #drone_lat = base_lat - lat_offset
            #drone_lon = base_lon + lon_offset
            
            # Bölge adını belirle
            zone_name = get_zone_name(center_x, center_y, frame_width, frame_height)
            
            # Mesafe ve tehlike seviyesi
            if area > 40000:
                distance = "Çok Yakın"
                distance_color = "red"
                distance_meters = f"{int(50 + (60000-area)/1000)}m"
                current_threat = "YÜKSEK TEHLİKE"
            elif area > 20000:
                distance = "Yakın"
                distance_color = "orange"
                distance_meters = f"{int(100 + (40000-area)/500)}m"
                current_threat = "ORTA SEVİYE"
            elif area > 5000:
                distance = "Orta"
                distance_color = "yellow"
                distance_meters = f"{int(200 + (20000-area)/100)}m"
                current_threat = "DÜŞÜK TEHLİKE"
            else:
                distance = "Uzak"
                distance_color = "green"
                distance_meters = f"{int(400 + (10000-max(area,1000))/50)}m"
                current_threat = "DÜŞÜK TEHLİKE"
            
            # Yükseklik tahmini
            if area > 40000:
                altitude = f"{int(20 + (area-40000)/2000)}m"
            elif area > 20000:
                altitude = f"{int(40 + (area-20000)/1000)}m"
            else:
                altitude = f"{int(80 + (20000-max(area,5000))/500)}m"
             # Tehlike seviyesi belirleme
            if area > 40000:
                threat_level = "YUKSEK TEHLİKE"
                alert_triggered = True
               
            elif area > 20000:
                if threat_level != "YUKSEK TEHLİKE":
                    threat_level = "ORTA SEVİYE"
               
            else:
                if threat_level not in ["YUKSEK TEHLİKE", "ORTA SEVİYE"]:
                    threat_level = "DUSUK"
                   
            
            # Tehlike seviyesi güncelle
            #if current_threat == "YÜKSEK TEHLİKE":
            #    threat_level = "YÜKSEK TEHLİKE"
            #    alert_triggered = True
            #elif current_threat == "ORTA SEVİYE" and threat_level != "YÜKSEK TEHLİKE":
             #   threat_level = "ORTA SEVİYE"
            #elif threat_level == "YOK":
            #    threat_level = "DÜŞÜK TEHLİKE"

            # Drone verilerini kaydet
            drone_info = {
                "id": j + 1,
                "confidence": round(confidence, 1),
                "area": int(area),
                "position": {
                    "zone": zone_name,
                    "distance": distance,
                    "distance_color": distance_color,
                    "distance_meters": distance_meters,
                    "altitude": altitude,
                    "gps": {
                        "latitude": round(drone_lat, 6),
                        "longitude": round(drone_lon, 6),
                        "altitude_m": int(altitude.replace('m', ''))
                    },
                    "center_x": center_x,
                    "center_y": center_y,

                    "map_x": center_x / frame_width,  # 0-1 aralığında normalize
                    "map_y": center_y / frame_height  # 0-1 aralığında normalize
                }
            }
            detections.append(drone_info)
            
            # Geçmişe ekle - Client formatına uygun
            display_x = (center_x / frame_width * 2) - 1  # 0-1'den -1,1'e çevir
            display_y = (center_y / frame_height * 2) - 1  # 0-1'den -1,1'e çevir
            
            history_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "id": f"D{j+1:03d}",
                "confidence": round(confidence, 1),
                "threat_level": distance,  # Client'ta tehlike seviyesi olarak mesafe kullanılıyor
                "x_coord": display_x,
                "y_coord": display_y,
                "zone": zone_name
            }
            
            detection_history.append(history_entry)
            if len(detection_history) > max_history:
                detection_history.pop(0)

    # Global verileri güncelle
    current_drone_data = {
        "drone_count": len(detections),
        "threat_level": threat_level,
        "detections": detections,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "fire_authorized": threat_level == "YÜKSEK TEHLİKE"
    }

    if alert_triggered:
        play_alert()

    # Verileri istemcilere gönder
    broadcast_drone_data()

def update_gui():
    """GUI'yi güncelle"""
    # Sistem durumu güncelle
    client_count_label.config(text=f"Bağlı İstemci: {len(connected_clients)}")
    system_time_label.config(text=f"Sistem Saati: {datetime.now().strftime('%H:%M:%S')}")
    
    # Tehlike seviyesi güncelle
    threat_level = current_drone_data.get("threat_level", "YOK")
    threat_level_label.config(text=f"Tehlike Seviyesi: {threat_level}")
    
    if threat_level == "YÜKSEK TEHLİKE":
        threat_level_label.config(fg="red")
    elif threat_level == "ORTA SEVİYE":
        threat_level_label.config(fg="orange")
    elif threat_level == "DÜŞÜK TEHLİKE":
        threat_level_label.config(fg="yellow")
    else:
        threat_level_label.config(fg="green")
    
    active_drones_label.config(text=f"Aktif Drone: {current_drone_data.get('drone_count', 0)}")
    
    if current_drone_data.get("timestamp"):
        last_detection_label.config(text=f"Son Tespit: {current_drone_data['timestamp']}")
    
    # Tabloları güncelle
    update_current_tree()
    update_history_tree()
    update_statistics()
    
    # Arka plan tespiti yap
    background_detection()
    
    # 100ms sonra tekrar çağır
    window.after(100, update_gui)

# Sunucuyu başlat
start_server()

# GUI güncellemesini başlat
update_gui()

# Pencere kapatılırken temizlik
def on_closing():
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()
    for client in connected_clients:
        client.close()
    window.quit()

window.protocol("WM_DELETE_WINDOW", on_closing)
window.mainloop()
