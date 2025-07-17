import cv2
from ultralytics import YOLO
import pygame
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk

# 📌 KENDİ EĞİTTİĞİN YOLOV8 MODELİNİN TAM YOLU
model_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\runs\detect\train\weights\best.pt"
model = YOLO(model_path)

# 📌 SES DOSYASININ TAM YOLU (veya aynı klasördeyse adı yeterlidir)
sound_path = "C:/Users/yaren/OneDrive/Masaüstü/drone_dataset/alert.wav"

# 📌 Pygame ile ses sistemi başlat
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load(sound_path)

def play_alert():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play()

# 📌 Tkinter SCADA Arayüzü
window = tk.Tk()
window.title("Drone Tespit SCADA Ekranı")
window.geometry("1000x700")

# Kamera Görüntüsü için Panel
video_label = tk.Label(window)
video_label.pack()

# Tehlike seviyesi gösterimi
status_label = tk.Label(window, text="Tehlike Seviyesi: Yok", font=("Arial", 16))
status_label.pack(pady=10)

# Drone tespiti zamanını göster
log_label = tk.Label(window, text="", font=("Arial", 12))
log_label.pack()

# Ateş Et butonu
fire_button = tk.Button(window, text="ATEŞ ET", font=("Arial", 14), state=tk.DISABLED, bg="gray")
fire_button.pack(pady=10)

# 📌 Kamera başlat
cap = cv2.VideoCapture(0)

def update():
    ret, frame = cap.read()
    if not ret:
        return

    results = model(frame)
    annotated_frame = results[0].plot()

    threat_level = "YOK"
    alert_triggered = False

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            cls_name = model.names[cls_id]

            # ❗ SADECE DRONE SINIFINI ALGILA
            if cls_name.lower() != "drone":
                continue

            # Drone bulunduysa alanını hesapla
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            width = x2 - x1
            height = y2 - y1
            area = width * height

            if area > 40000:
                threat_level = "YÜKSEK TEHLİKE"
                alert_triggered = True
                fire_button.config(state=tk.NORMAL, bg="red")
                status_label.config(fg="red")
            elif area > 20000:
                threat_level = "ORTA SEVİYE"
                fire_button.config(state=tk.DISABLED, bg="gray")
                status_label.config(fg="orange")
            else:
                threat_level = "DÜŞÜK"
                fire_button.config(state=tk.DISABLED, bg="gray")
                status_label.config(fg="green")

            # Alanı bounding box’a yazdır
            cv2.putText(annotated_frame, f"Alan: {int(area)}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # SCADA arayüzünde tehlike seviyesi yazdır
    status_label.config(text=f"Tehlike Seviyesi: {threat_level}")

    # Eğer tehlike varsa, ses çal ve zaman yaz
    if alert_triggered:
        play_alert()
        log_label.config(text=f"Tespit Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Görüntüyü SCADA’ya aktar
    frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    window.after(30, update)

# 🔁 Döngüyü başlat
update()
window.mainloop()

# 📌 Temizlik
cap.release()
cv2.destroyAllWindows()
pygame.quit()
