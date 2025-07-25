import cv2
from ultralytics import YOLO
import pygame
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk
import numpy as np
import socket
import threading
import json
import time

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
            connected_clients.remove(client)

# Tkinter SCADA arayüzü oluştur
window = tk.Tk()
window.title("Drone Tespit SCADA Sunucusu")
window.geometry("1200x800")

# Ana çerçeve
main_frame = tk.Frame(window)
main_frame.pack(fill=tk.BOTH, expand=True)

# Sol taraf - Video
left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

video_label = tk.Label(left_frame)
video_label.pack()

# Sağ taraf - Kontrol paneli
right_frame = tk.Frame(main_frame, width=300, bg="lightgray")
right_frame.pack(side=tk.RIGHT, fill=tk.Y)
right_frame.pack_propagate(False)

# Sunucu bilgileri
server_info_frame = tk.LabelFrame(right_frame, text="Sunucu Bilgileri", font=("Arial", 12, "bold"))
server_info_frame.pack(fill=tk.X, padx=10, pady=5)

server_status_label = tk.Label(server_info_frame, text=f"Sunucu: {SERVER_HOST}:{SERVER_PORT}", font=("Arial", 10))
server_status_label.pack(pady=2)

client_count_label = tk.Label(server_info_frame, text="Bağlı İstemci: 0", font=("Arial", 10))
client_count_label.pack(pady=2)

# Tespit bilgileri
detection_frame = tk.LabelFrame(right_frame, text="Tespit Bilgileri", font=("Arial", 12, "bold"))
detection_frame.pack(fill=tk.X, padx=10, pady=5)

status_label = tk.Label(detection_frame, text="Tehlike Seviyesi: YOK", font=("Arial", 14, "bold"))
status_label.pack(pady=5)

drone_count_label = tk.Label(detection_frame, text="Tespit Edilen Drone: 0", font=("Arial", 10))
drone_count_label.pack(pady=2)

log_label = tk.Label(detection_frame, text="", font=("Arial", 9), wraplength=280)
log_label.pack(pady=2)

# Kontrol butonları
control_frame = tk.LabelFrame(right_frame, text="Kontrol", font=("Arial", 12, "bold"))
control_frame.pack(fill=tk.X, padx=10, pady=5)

fire_button = tk.Button(control_frame, text="ATEŞ ET", font=("Arial", 14, "bold"), 
                       state=tk.DISABLED, bg="gray", fg="white")
fire_button.pack(pady=10, fill=tk.X)

# Kamera başlat
cap = cv2.VideoCapture(0)

def put_text_with_background(img, text, position, font=cv2.FONT_HERSHEY_SIMPLEX,
                             font_scale=0.7, font_thickness=2,
                             text_color=(255,255,255), bg_color=(0,0,0,150)):
    """Yazıyı arka plan rengiyle birlikte çizer"""
    x, y = position
    (w, h), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
    overlay = img.copy()

    rect_bgr = bg_color[:3]
    alpha = bg_color[3] / 255.0

    cv2.rectangle(overlay, (x - 5, y - h - 5), (x + w + 5, y + baseline + 5), rect_bgr, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    cv2.putText(img, text, (x, y), font, font_scale, text_color, font_thickness, lineType=cv2.LINE_AA)

def update():
    global current_drone_data
    
    ret, frame = cap.read()
    if not ret:
        window.after(30, update)
        return

    results = model(frame)
    annotated_frame = results[0].plot()

    threat_level = "YOK"
    alert_triggered = False
    detections = []

    info_line_height = 30
    left_x = 10
    right_x_offset = 10

    frame_height, frame_width = frame.shape[:2]

    confidence_texts = []
    area_texts = []

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

            # Ekran boyutlarını al
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            
            # GPS koordinatlarını simüle et (gerçek projede GPS modülünden alınır)
            # Örnek konum: Eskişehir, Türkiye civarı
            base_lat = 39.7767  # Eskişehir enlem
            base_lon = 30.5206  # Eskişehir boylam
            
            # Ekran koordinatlarını GPS koordinatlarına çevir
            # Her piksel yaklaşık 0.0001 derece (yaklaşık 11 metre)
            lat_offset = ((center_y - frame_height/2) / (frame_height/2)) * 0.01  # ±0.01 derece
            lon_offset = ((center_x - frame_width/2) / (frame_width/2)) * 0.01   # ±0.01 derece
            
            drone_lat = base_lat - lat_offset  # Y eksenini ters çevir (ekranda aşağı = güneye)
            drone_lon = base_lon + lon_offset
            
            # Konum bilgilerini anlaşılır hale getir
            # Ekranı 9 bölgeye ayır (3x3 grid)
            h_zone = "Batı" if center_x < frame_width/3 else ("Merkez" if center_x < 2*frame_width/3 else "Doğu")
            v_zone = "Kuzey" if center_y < frame_height/3 else ("Merkez" if center_y < 2*frame_height/3 else "Güney")
            zone_name = f"{v_zone} {h_zone}" if v_zone != "Merkez" or h_zone != "Merkez" else "Merkez"
            
            # Mesafe tahmini (alan bazlı)
            if area > 40000:
                distance = "Çok Yakın"
                distance_color = "red"
                distance_meters = f"{int(50 + (60000-area)/1000)}m"  # 50-70m arası
            elif area > 20000:
                distance = "Yakın"
                distance_color = "orange"
                distance_meters = f"{int(100 + (40000-area)/500)}m"  # 100-140m arası
            elif area > 5000:
                distance = "Orta"
                distance_color = "yellow"  
                distance_meters = f"{int(200 + (20000-area)/100)}m"  # 200-350m arası
            else:
                distance = "Uzak"
                distance_color = "green"
                distance_meters = f"{int(400 + (10000-max(area,1000))/50)}m"  # 400m+
            
            # Yükseklik tahmini (area ve distance'a göre)
            if area > 40000:
                altitude = f"{int(20 + (area-40000)/2000)}m"  # 20-30m
            elif area > 20000:
                altitude = f"{int(40 + (area-20000)/1000)}m"  # 40-60m
            else:
                altitude = f"{int(80 + (20000-max(area,5000))/500)}m"  # 80-110m
            
            # Boyut kategorisi
            if width > height * 1.5:
                orientation = "Yatay"
            elif height > width * 1.5:
                orientation = "Dikey"
            else:
                orientation = "Dengeli"

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
                    "orientation": orientation,
                    "size": f"{int(width)}x{int(height)}",
                    "gps": {
                        "latitude": round(drone_lat, 6),
                        "longitude": round(drone_lon, 6),
                        "altitude_m": int(altitude.replace('m', ''))
                    },
                    # Harita için normalize edilmiş koordinatlar (0-1 arası)
                    "map_x": center_x / frame_width,
                    "map_y": center_y / frame_height,
                    "center_x": center_x,
                    "center_y": center_y
                }
            }
            detections.append(drone_info)

            # Tehlike seviyesi belirleme
            if area > 40000:
                threat_level = "YUKSEK TEHLİKE"
                alert_triggered = True
                fire_button.config(state=tk.NORMAL, bg="red")
                status_label.config(fg="red")
            elif area > 20000:
                if threat_level != "YUKSEK TEHLİKE":
                    threat_level = "ORTA SEVİYE"
                    fire_button.config(state=tk.DISABLED, bg="orange")
                    status_label.config(fg="orange")
            else:
                if threat_level not in ["YUKSEK TEHLİKE", "ORTA SEVİYE"]:
                    threat_level = "DUSUK"
                    fire_button.config(state=tk.DISABLED, bg="gray")
                    status_label.config(fg="green")

            # Görsel çizimler
            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
            confidence_texts.append(f"Drone {j+1}: %{confidence:.1f}")
            area_texts.append(f"Drone {j+1}: Alan={int(area)}")

    # Tehlike seviyesi yazısı
    threat_y = 25
    put_text_with_background(annotated_frame, f"Tehlike Seviyesi: {threat_level}",
                             (left_x, threat_y),
                             font_scale=0.9,
                             font_thickness=3,
                             text_color=(0,255,0) if threat_level=="YOK" else
                                        (0,165,255) if threat_level=="ORTA SEVİYE" else (0,0,255),
                             bg_color=(0,0,0,150))

    # Confidence yazıları
    for idx, text in enumerate(confidence_texts):
        y = threat_y + 10 + (idx + 1) * info_line_height
        put_text_with_background(annotated_frame, text, (left_x, y), text_color=(0,255,0), bg_color=(0,0,0,150))

    # Alan bilgileri
    for idx, text in enumerate(area_texts):
        y = threat_y + 10 + idx * info_line_height
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        x = frame_width - text_size[0] - right_x_offset
        put_text_with_background(annotated_frame, text, (x, y), text_color=(0,255,255), bg_color=(0,0,0,150))

    # Global verileri güncelle
    current_drone_data = {
        "drone_count": len(detections),
        "threat_level": threat_level,
        "detections": detections,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "fire_authorized": threat_level == "YUKSEK TEHLİKE"
    }

    # GUI güncelle
    status_label.config(text=f"Tehlike Seviyesi: {threat_level}")
    drone_count_label.config(text=f"Tespit Edilen Drone: {len(detections)}")
    client_count_label.config(text=f"Bağlı İstemci: {len(connected_clients)}")

    if alert_triggered:
        play_alert()
        log_label.config(text=f"Son Tespit: {current_drone_data['timestamp']}\n"
                              f"Yüksek Tehlike Uyarısı!")

    # Video göster
    frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    # Video boyutunu ayarla
    img = img.resize((800, 600), Image.Resampling.LANCZOS)
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    # Verileri istemcilere gönder
    broadcast_drone_data()

    window.after(30, update)

# Sunucuyu başlat
start_server()

# Ana döngüyü başlat
update()

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
