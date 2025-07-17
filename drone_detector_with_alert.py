import cv2
from ultralytics import YOLO
import pygame
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk
import numpy as np

# Model ve ses dosyası yolları
model_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\runs\detect\train\weights\best.pt"
sound_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\alert.wav"

# Modeli yükle
model = YOLO(model_path)

# Pygame ses sistemi başlat
pygame.init()
pygame.mixer.init()
pygame.mixer.music.load(sound_path)

def play_alert():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.play()

# Tkinter SCADA arayüzü oluştur
window = tk.Tk()
window.title("Drone Tespit SCADA Ekranı")
window.geometry("1000x700")

video_label = tk.Label(window)
video_label.pack()

status_label = tk.Label(window, text="Tehlike Seviyesi: Yok", font=("Arial", 16))
status_label.pack(pady=10)

log_label = tk.Label(window, text="", font=("Arial", 12))
log_label.pack()

fire_button = tk.Button(window, text="ATEŞ ET", font=("Arial", 14), state=tk.DISABLED, bg="gray")
fire_button.pack(pady=10)

# Kamera başlat
cap = cv2.VideoCapture(0)

def put_text_with_background(img, text, position, font=cv2.FONT_HERSHEY_SIMPLEX,
                             font_scale=0.7, font_thickness=2,
                             text_color=(255,255,255), bg_color=(0,0,0,150)):
    """
    Yazıyı arka plan rengiyle birlikte çizer (arka plan yarı saydam olur).
    img: görüntü
    text: yazı metni
    position: (x,y) koordinatı
    bg_color: (B,G,R,alpha) olarak yarı saydam renk
    """
    x, y = position
    (w, h), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
    overlay = img.copy()

    # Arka plan dikdörtgeni (yarı saydam)
    rect_bgr = bg_color[:3]
    alpha = bg_color[3] / 255.0

    cv2.rectangle(overlay, (x - 5, y - h - 5), (x + w + 5, y + baseline + 5), rect_bgr, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    # Yazıyı çiz
    cv2.putText(img, text, (x, y), font, font_scale, text_color, font_thickness, lineType=cv2.LINE_AA)

def update():
    ret, frame = cap.read()
    if not ret:
        return

    results = model(frame)
    annotated_frame = results[0].plot()

    threat_level = "YOK"
    alert_triggered = False

    info_line_height = 30
    left_x = 10         # Sol üst köşe x koordinatı (confidence için)
    right_x_offset = 10 # Sağ üst köşe iç boşluk

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
            confidence = box.conf[0].item() * 100  # yüzde olarak

            if area > 40000:
                threat_level = "YUKSEK TEHLİKE"
                alert_triggered = True
                fire_button.config(state=tk.NORMAL, bg="red")
                status_label.config(fg="red")
            elif area > 20000:
                if threat_level != "YUKSEK TEHLİKE":
                    threat_level = "ORTA SEVİYE"
                    fire_button.config(state=tk.DISABLED, bg="gray")
                    status_label.config(fg="orange")
            else:
                if threat_level not in ["YUKSEK TEHLİKE", "ORTA SEVİYE"]:
                    threat_level = "DUSUK"
                    fire_button.config(state=tk.DISABLED, bg="gray")
                    status_label.config(fg="green")

            # Bounding box çiz (kırmızı ve kalın)
            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)

            # Alan bilgisi bbox üstündeki yazıyı kaldırdım

            # Sol üst köşeye confidence ekle
            confidence_texts.append(f"Drone {j+1}: %{confidence:.1f}")

            # Sağ üst köşeye alan bilgisi ekle
            area_texts.append(f"Drone {j+1}: Alan={int(area)}")

    # Tehlike seviyesi yazısı konumu
    threat_y = 25
    put_text_with_background(annotated_frame, f"Tehlike Seviyesi: {threat_level}",
                             (left_x, threat_y),
                             font_scale=0.9,
                             font_thickness=3,
                             text_color=(0,255,0) if threat_level=="YOK" else
                                        (0,165,255) if threat_level=="ORTA SEVİYE" else (0,0,255),
                             bg_color=(0,0,0,150))

    # Confidence yazılarını sol üstte, tehlike seviyesinin hemen altında yaz
    for idx, text in enumerate(confidence_texts):
        y = threat_y + 10 + (idx + 1) * info_line_height
        put_text_with_background(annotated_frame, text, (left_x, y), text_color=(0,255,0), bg_color=(0,0,0,150))

    # Alan bilgilerini sağ üst köşeye yaz
    for idx, text in enumerate(area_texts):
        y = threat_y + 10 + idx * info_line_height
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        x = frame_width - text_size[0] - right_x_offset
        put_text_with_background(annotated_frame, text, (x, y), text_color=(0,255,255), bg_color=(0,0,0,150))

    status_label.config(text=f"Tehlike Seviyesi: {threat_level}")

    if alert_triggered:
        play_alert()
        log_label.config(text=f"Tespit Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    imgtk = ImageTk.PhotoImage(image=img)
    video_label.imgtk = imgtk
    video_label.configure(image=imgtk)

    window.after(30, update)

update()
window.mainloop()

cap.release()
cv2.destroyAllWindows()
pygame.quit()
