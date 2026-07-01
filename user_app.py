import os
import json
import uuid
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import face_recognition
import cv2
import hashlib
import time
import shutil
import numpy as np
from ttkbootstrap import Style
from ttkbootstrap import Button, Frame, Label, Entry, Combobox

# ======================================================
#                    CONFIGURATION
# ======================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
ENCODINGS_CACHE = os.path.join(DATA_DIR, "encodings_cache.json")

DIST_THRESHOLD = 0.45

os.makedirs(PROFILES_DIR, exist_ok=True)


# ======================================================
#                 UTILITY FUNCTIONS
# ======================================================
def load_profiles():
    if not os.path.exists(PROFILES_FILE):
        return []
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("profiles", [])
    except:
        return []


def save_profiles(profiles):
    data = {"profiles": profiles}
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def compute_encodings_for_profile(profile):
    encs = []
    if "image" in profile:
        images = [profile["image"]]
    else:
        images = profile.get("images", [])

    for img_path in images:
        try:
            img = face_recognition.load_image_file(img_path)
            faces = face_recognition.face_encodings(img)
            if faces:
                encs.append(faces[0])
        except:
            pass

    return encs


def rebuild_encodings_cache():
    profiles = load_profiles()
    cache = []

    for p in profiles:
        encs = compute_encodings_for_profile(p)
        for e in encs:
            cache.append({
                "id": p.get("id"),
                "name": p.get("nom") + " " + p.get("prenom"),
                "enc": e.tolist()
            })

    with open(ENCODINGS_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)

    return cache


def load_encodings_cache():
    if not os.path.exists(ENCODINGS_CACHE):
        return rebuild_encodings_cache()

    with open(ENCODINGS_CACHE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [{"id": x["id"], "name": x["name"], "enc": np.array(x["enc"])}
            for x in data]


# ======================================================
#                      FACE APP
# ======================================================
class FaceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.style = Style("litera")
        self.title("Reconnaissance Faciale")
        icon_path = os.path.join(APP_DIR, "assets", "logo.png")
        icon_img = tk.PhotoImage(file=icon_path)
        self.iconphoto(True, icon_img)
        self._icon_img = icon_img


        self.geometry("1000x650")
        self.minsize(1000, 650)
        self.resizable(False, False)
        rebuild_encodings_cache()
        self.enc_cache = load_encodings_cache()

        self.tab_control = tk.Frame(self)
        self.tab_control.pack(fill="both", expand=True)

        header = Frame(self.tab_control, bootstyle="dark")
        header.pack(fill="x")
        logo_path = os.path.join(APP_DIR, "assets", "logo.png")
        logo_img = Image.open(logo_path)
        logo_img = logo_img.resize((90, 90))
        self.logo_tk = ImageTk.PhotoImage(logo_img)

        logo_label = Label(header, image=self.logo_tk, bootstyle="dark")
        logo_label.pack(side="left", padx=20, pady=10)
        Label(header, text="Reconnaissance Faciale",
              font=("Segoe UI", 18, "bold"),
              bootstyle="secondly").pack(pady=10)

        self.body = tk.Frame(self.tab_control)
        self.body.pack(fill="both", expand=True)

        self.webcam_running = False
        self.cap = None

        self.show_user()

    def clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def show_user(self):
        self.clear_body()

        container = Frame(self.body)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left = Frame(container, width=350, bootstyle="litera")
        left.pack(side="left", fill="y", padx=10, pady=10)

        Button(left, text="📷 Utiliser Webcam",
               bootstyle="success",
               command=self.start_webcam).pack(fill="x", pady=5)
        Button(left, text="❌ Quitter Webcam",
               bootstyle="danger",
               command=self.stop_webcam).pack(fill="x", pady=5)

        Button(left, text="🖼️ Import Image",
               bootstyle="primary",
               command=self.import_image).pack(fill="x", pady=5)

        result_frame = Frame(left, bootstyle="info")
        result_frame.pack(fill="both", expand=True, pady=10)

        Label(result_frame, text="Résultats", bootstyle="inverse-info").pack(fill="x")

        self.result_box = tk.Text(result_frame, height=18, width=40, font=("Consolas", 10))
        self.result_box.pack(fill="both", expand=True, padx=5, pady=5)

        right = Frame(container)
        right.pack(side="right", fill="both", expand=True)

        self.image_label = Label(right)
        self.image_label.pack(expand=True)

    # ======================================================
    #                 IMAGE / CAMERA
    # ======================================================
    def import_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        self.enc_cache = load_encodings_cache()
        img = face_recognition.load_image_file(path)
        rgb = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        self.enc_cache = load_encodings_cache()
        self.display_image(rgb)
        self.identify_faces_in_image(img)

    def display_image(self, bgr_image):
        h, w = bgr_image.shape[:2]
        max_w = 650
        scale = min(max_w / w, 1.0)
        disp = cv2.resize(bgr_image, (int(w * scale), int(h * scale)))

        img = Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(img)

        self.image_label.imgtk = imgtk
        self.image_label.configure(image=imgtk)

    def identify_faces_in_image(self, image):
        face_locations = face_recognition.face_locations(image)
        face_encs = face_recognition.face_encodings(image, face_locations)

        self.result_box.delete("1.0", tk.END)

        if not face_encs:
            self.result_box.insert(tk.END, "Aucun utilisateur trouvé.\n")
            return

        profiles = load_profiles()
        known_encs = np.array([item["enc"] for item in self.enc_cache])
        known_names = [item["name"] for item in self.enc_cache]
        known_ids = [item["id"] for item in self.enc_cache]
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        for i, (fe, (top, right, bottom, left)) in enumerate(zip(face_encs, face_locations), 1):
            name = "Inconnu"
            sexe = "N/A"
            color = (0, 0, 255)
            if len(known_encs) > 0:
                dists = np.linalg.norm(known_encs - fe, axis=1)
                best = np.argmin(dists)
                sorted_dists = np.sort(dists)
                if (dists[best] <= DIST_THRESHOLD and (len(sorted_dists) == 1 or sorted_dists[1] - sorted_dists[0] > 0.08)):
                    name = known_names[best]
                    pid = known_ids[best]
                    p = next((x for x in profiles if x.get("id") == pid), None)
                    sexe = p.get("sexe", "N/A") if p else "N/A"
                    color = (0, 255, 0)
            cv2.rectangle(bgr, (left, top), (right, bottom), color, 3)
            cv2.putText(bgr, f"{name} | {sexe}", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            self.result_box.insert(tk.END, f"Utilisateur {i}: {name} | Sexe : {sexe}\n")
        self.display_image(bgr)
    # ======================================================
    #                     WEBCAM
    # ======================================================
    def start_webcam(self):
        if self.webcam_running:
            return

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

        if not self.cap.isOpened():
            messagebox.showerror(
                "Erreur Webcam",
                "Impossible d'accéder à la webcam.\n"
                "Veuillez autoriser l'accès à la caméra ou vérifier qu'elle est activée."
            )
            self.cap.release()
            self.cap = None
            return

        self.webcam_running = True
        self.result_box.delete("1.0", tk.END)
        self.result_box.insert(tk.END, "Webcam démarrée...\n")

        threading.Thread(target=self._webcam_loop, daemon=True).start()
    def stop_webcam(self):
        if self.webcam_running:
            self.webcam_running = False
            if self.cap:
                self.cap.release()
                self.cap = None
            self.result_box.delete("1.0", tk.END)
            self.result_box.insert(tk.END, "Webcam arrêtée.\n")
            self.image_label.configure(image="")  
    def _webcam_loop(self):
        black_frames = 0
        frame_count = 0
        profiles = load_profiles()

        try:
            while self.webcam_running and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()

                if not ret or frame is None or frame.size == 0:
                    time.sleep(0.1)
                    continue

                if np.mean(frame) < 5:
                    black_frames += 1
                    if black_frames > 20:
                        self.result_box.delete("1.0", tk.END)
                        self.result_box.insert(
                            tk.END,
                            "Attention!.\n"
                            "La webcam semble être couverte ou complètement sombre.\n"
                        )
                    time.sleep(0.1)
                    continue
                else:
                    black_frames = 0

                display = frame.copy()
                small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

                try:
                    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                except cv2.error:
                    continue

                if frame_count % 10 == 0:
                    face_locations = face_recognition.face_locations(rgb_small)
                    face_encs = face_recognition.face_encodings(rgb_small, face_locations)

                    known_encs = np.array([item["enc"] for item in self.enc_cache])
                    known_names = [item["name"] for item in self.enc_cache]
                    known_ids = [item["id"] for item in self.enc_cache]

                    names = []
                    sexes = []

                    for fe, (top, right, bottom, left) in zip(face_encs, face_locations):
                        if len(known_encs) > 0:
                            dists = np.linalg.norm(known_encs - fe, axis=1)
                            best = np.argmin(dists)
                            if dists[best] <= DIST_THRESHOLD:
                                name = known_names[best]
                                pid = known_ids[best]
                                p = next((x for x in profiles if x.get("id") == pid), None)
                                sexe = p.get("sexe", "N/A") if p else "N/A"
                            else:
                                name, sexe = "Inconnu", "N/A"
                        else:
                            name, sexe = "Inconnu", "N/A"

                        names.append(name)
                        sexes.append(sexe)

                        top *= 2; right *= 2; bottom *= 2; left *= 2
                        color = (0, 255, 0) if name != "Inconnu" else (0, 0, 255)

                        cv2.rectangle(display, (left, top), (right, bottom), color, 2)
                        cv2.putText(
                            display,
                            f"{name} | {sexe}",
                            (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            color,
                            2
                        )

                        if name != "Inconnu":
                            self.webcam_running = False
                            self.cap.release()
                            self.cap = None

                            self.display_image(display)
                            self.result_box.delete("1.0", tk.END)
                            self.result_box.insert(
                                tk.END,
                                f"Utilisateur reconnu : {name} | Sexe : {sexe}\n"
                            )
                            return

                    self.result_box.delete("1.0", tk.END)
                    for i, (n, s) in enumerate(zip(names, sexes), 1):
                        self.result_box.insert(
                            tk.END, f"Utilisateur {i}: {n} | Sexe : {s}\n"
                        )

                frame_count += 1
                self.display_image(display)
                time.sleep(0.03)

        finally:
            if self.cap:
                self.cap.release()
                self.cap = None
            self.webcam_running = False


# ======================================================
#                     START APP
# ======================================================
if __name__ == "__main__":
    app = FaceApp()
    app.mainloop()
