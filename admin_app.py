import os
import json
import shutil
import uuid
import time
from pathlib import Path
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk
from ttkbootstrap import Style
from ttkbootstrap import Button, Frame, Label, Entry, Combobox

# ---------------- Configuration ----------------
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ADMIN_FILE = DATA_DIR / "admin_credentials.json"
PROFILES_FILE = DATA_DIR / "profiles.json"
PHOTOS_DIR = DATA_DIR / "profiles"

THEME = "litera"
WINDOW_SIZE = "1200x780"
CARD_SIZE = (140, 140)
PREVIEW_SIZE = (360, 360)

# ---------------- Helpers ----------------
def ensure_data_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    if not ADMIN_FILE.exists():
        ADMIN_FILE.write_text(json.dumps({"email": "admin@gmail.com", "password": "admin123"}, indent=2, ensure_ascii=False))
    if not PROFILES_FILE.exists():
        PROFILES_FILE.write_text(json.dumps({"profiles": []}, indent=2, ensure_ascii=False))

def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def copy_photo_to_storage(src_path: str, dest_id: str) -> str:
    ext = Path(src_path).suffix or ".jpg"
    dest = PHOTOS_DIR / f"{dest_id}{ext}"
    try:
        shutil.copy(src_path, dest)
    except Exception:
        try:
            img = Image.open(src_path)
            img.save(dest)
        except Exception as e:
            raise e
    return str(dest)

# ---------------- UI Components ----------------
class TopStatus(Frame):
    def __init__(self, master, **kw):
        super().__init__(master, padding=6, **kw)
        self.var = tk.StringVar(value="")
        self.lbl = Label(self, textvariable=self.var, anchor="w")
        self.lbl.pack(fill="x")

    def set(self, text: str, type="info"):
        colors = {"info":"#007bff", "success":"#28a745", "error":"#dc3545"}
        self.var.set(text)
        self.lbl.config(foreground=colors.get(type, "#000"))
        self.after(4000, lambda: self.var.set(""))

# ---------------- Modal ----------------
class Modal(Frame):
    def __init__(self, master, title="Modal", size=(520, 380)):
        self.win = tk.Toplevel(master)
        self.win.transient(master)
        self.win.grab_set()
        self.win.title(title)
        w, h = size
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.frame = Frame(self.win, padding=12)
        self.frame.pack(fill="both", expand=True)

# ---------------- Alerts ----------------
def alert_info(msg):
    messagebox.showinfo("Info", msg)
def alert_success(msg):
    messagebox.showinfo("Succès", msg)
def alert_error(msg):
    messagebox.showerror("Erreur", msg)


# ---------------- Profile Editor ----------------
class ProfileEditor:
    def __init__(self, master, profile=None, on_save=None):
        self.master = master
        self.profile = profile
        self.on_save = on_save
        self.modal = Modal(master, title="Modifier Utilisateur" if profile else "Créer utilisateur", size=(540, 600))
        frame = self.modal.frame

        Label(frame, text="Nom", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(4, 2))
        self.nom_entry = Entry(frame, width=40)
        self.nom_entry.pack(fill="x")

        Label(frame, text="Prénom", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.prenom_entry = Entry(frame, width=40)
        self.prenom_entry.pack(fill="x")

        Label(frame, text="Sexe", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.sexe_combo = Combobox(frame, values=["Homme", "Femme"], state="readonly", width=20)
        self.sexe_combo.pack(fill="x")

        Label(frame, text="Photo", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(8, 2))
        btn_frame = Frame(frame)
        btn_frame.pack(fill="x")
        self.choose_btn = Button(btn_frame, text="➕ Choisir une image", bootstyle="secondary", command=self.choose_photo)
        self.choose_btn.pack(side="left")
        self.photo_label = Label(frame)
        self.photo_label.pack(pady=(10, 8))

        actions = Frame(frame)
        actions.pack(fill="x", pady=(6, 0))
        self.save_btn = Button(actions, text="💾 Enregistrer", bootstyle="success", command=self.save)
        self.save_btn.pack(side="right", padx=6)
        cancel_btn = Button(actions, text="Annuler", bootstyle="secondary", command=self.close)
        cancel_btn.pack(side="right", padx=6)

        self.photo_path = None
        self.photo_thumb = None
        if profile:
            self.nom_entry.insert(0, profile.get("nom", ""))
            self.prenom_entry.insert(0, profile.get("prenom", ""))
            sexe = profile.get("sexe", "")
            if sexe in ("Homme", "Femme"):
                self.sexe_combo.set(sexe)
            img = profile.get("image")
            if img and os.path.exists(img):
                self.photo_path = img
                self.load_preview(img)

    def choose_photo(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if p:
            self.photo_path = p
            self.load_preview(p)

    def load_preview(self, path):
        try:
            thumb = Image.open(path)
            thumb.thumbnail((220, 220))
            self.photo_thumb = ImageTk.PhotoImage(thumb)
            self.photo_label.config(image=self.photo_thumb)
        except Exception as e:
            self.master.status.set(f"Preview failed: {e}", type="error")

    def save(self):
        
        nom = self.nom_entry.get().strip()
        prenom = self.prenom_entry.get().strip()
        sexe = self.sexe_combo.get().strip()
        if not nom or not prenom:
            self.master.status.set("Nom et Prénom obligatoires.", type="error")
            alert_error("Veuillez remplir Nom et Prénom.")
            return
        if sexe not in ("Homme", "Femme"):
            self.master.status.set("Choisissez le sexe.", type="error")
            alert_error("Veuillez sélectionner le sexe.")
            return
        if not self.photo_path:
            self.master.status.set("Choisissez une image.", type="error")
            alert_error("Veuillez choisir une image.")
            return

        data = load_json(PROFILES_FILE, {"profiles": []})
        for p in data["profiles"]:
            if self.profile and p.get("id") == self.profile.get("id"):
                continue  
            existing_img = p.get("image")
            if existing_img and os.path.exists(existing_img) and self.photo_path:
                try:
                    import hashlib
                    def hash_file(path):
                        h = hashlib.md5()
                        with open(path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                h.update(chunk)
                        return h.hexdigest()
                    if hash_file(existing_img) == hash_file(self.photo_path):
                        self.master.status.set("Cette image est déjà utilisée pour un autre profil.", type="error")
                        alert_error("Impossible : la photo est déjà utilisée !")
                        self.save_btn.config(state="normal")
                        return
                except Exception:
                    pass
        if self.profile:  
            pid = self.profile.get("id")
            for p in data["profiles"]:
                if p.get("id") == pid:
                    if self.photo_path and not str(self.photo_path).startswith(str(PHOTOS_DIR)):
                        new_path = copy_photo_to_storage(self.photo_path, pid)
                    else:
                        new_path = self.photo_path
                    p.update({
                        
                        "nom": nom,
                        "prenom": prenom,
                        "sexe": sexe,
                        "image": new_path,
                        "modified_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    break
            save_json(PROFILES_FILE, data)
            self.master.status.set("Profil modifié.", type="success")
            alert_success("Profil modifié avec succès !")
        else:  
            pid = str(uuid.uuid4())
            new_path = copy_photo_to_storage(self.photo_path, pid)
            new_prof = {
                "id": pid,
                "nom": nom,
                "prenom": prenom,
                "sexe": sexe,
                "image": new_path,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            data["profiles"].append(new_prof)
            save_json(PROFILES_FILE, data)
            self.master.status.set("Utilisateur créé.", type="success")
            alert_success("Utilisateur créé avec succès !")

        if callable(self.on_save):
            self.on_save()
        self.close()

    def close(self):
        try:
            self.modal.win.grab_release()
        except Exception:
            pass
        self.modal.win.destroy()

# ---------------- Main Application ----------------
class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_data_dirs()
        self.style = Style(theme=THEME)
        self.title("Administration des profils utilisateurs")
        icon_path = os.path.join(APP_DIR, "assets", "logo.png")
        icon_img = tk.PhotoImage(file=icon_path)
        self.iconphoto(True, icon_img)
        self._icon_img = icon_img
        self.geometry(WINDOW_SIZE)
        self.minsize(1000, 650)

        self.current_admin = None
        self.profiles_data = {"profiles": []}
        self.card_images = {}
        self.preview_image = None
        self.selected_profile = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # left sidebar
        self.sidebar = Frame(self, width=260, padding=12)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.build_sidebar()

        # main content
        self.content = Frame(self, padding=12)
        self.content.grid(row=0, column=1, sticky="nsew")

        # status bar
        self.status = TopStatus(self)
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.show_login()

    def build_sidebar(self):
        title = Label(self.sidebar, text="Gestionnaire de Profils", font=("Helvetica", 14, "bold"))
        title.pack(anchor="w", pady=(4, 12))

        self.btn_profiles = Button(self.sidebar, text="👥 Utilisateurs", bootstyle="info-outline", command=self.show_profiles_view)
        self.btn_profiles.pack(fill="x", pady=6)

        self.btn_add_profile = Button(self.sidebar, text="➕ Ajouter utlisateur", bootstyle="success-outline", command=self.open_create_modal)
        self.btn_add_profile.pack(fill="x", pady=6)

        self.btn_theme = Button(self.sidebar, text="🌓 Mode", bootstyle="secondary", command=self.toggle_theme)
        self.btn_theme.pack(fill="x", pady=6)

    # Disable initially
        self.btn_profiles.config(state="disabled")
        self.btn_add_profile.config(state="disabled")
    


        sep = ttk.Separator(self.sidebar, orient="horizontal")
        sep.pack(fill="x", pady=(12, 12))

        info = Frame(self.sidebar, padding=10)
        info.pack(fill="x", pady=(6, 0))
        self.count_label = Label(info, text="Utilisateurs: 0", font=("Helvetica", 10))
        self.count_label.pack(anchor="w")

    def toggle_theme(self):
        current = self.style.theme_use()
        self.style.theme_use("flatly" if current == "cyborg" else "dar")
        self.status.set(f"Theme switched.", type="info")

    # ---------------- Login ----------------
    def show_login(self):
        for w in self.content.winfo_children():
            w.destroy()
        login_card = Frame(self.content, padding=24, relief="raised")
        login_card.place(relx=0.5, rely=0.45, anchor="center")
        # ===== Logo =====
        logo_path = os.path.join(APP_DIR, "assets", "logo.png")
        logo_img = Image.open(logo_path)
        logo_img = logo_img.resize((120, 120))  
        self.login_logo = ImageTk.PhotoImage(logo_img)

        Label(login_card, image=self.login_logo).pack(pady=(0, 10))



        Label(login_card, text="Bienvenue", font=("Helvetica", 20, "bold")).pack(pady=(6, 12))
        Label(login_card, text="Connexion", font=("Helvetica", 10)).pack(pady=(0, 12))

        Label(login_card, text="Email", anchor="w").pack(fill="x")
        self.email_entry = Entry(login_card, width=40)
        self.email_entry.pack(pady=(4, 8))
        Label(login_card, text="Mot de passe", anchor="w").pack(fill="x")
        self.password_entry = Entry(login_card, width=40, show="*")
        self.password_entry.pack(pady=(4, 10))

        btns = Frame(login_card)
        btns.pack(fill="x", pady=(8, 0))
        Button(btns, text="🔐 Connexion", bootstyle="primary", command=self.do_login).pack(side="left")
        self.status.set("Veuillez vous connecter.")

    def do_login(self):
        email = self.email_entry.get().strip()
        pw = self.password_entry.get().strip()

        if not email or not pw:
            alert_error("Veuillez remplir tous les champs.")
            self.status.set("Champs manquants.", type="error")
            return

        creds = load_json(ADMIN_FILE, {"email": "", "password": ""})

        if email != creds.get("email"):
            alert_error("Email incorrect.")
            self.status.set("Email incorrect.", type="error")
            return
        if pw != creds.get("password"):
            alert_error("Mot de passe incorrect.")
            self.status.set("Mot de passe incorrect.", type="error")
            return

        self.current_admin = email
        self.status.set(f"Connexion réussie : {email}", type="success")
        alert_success("Connexion réussie !")
        self.btn_profiles.config(state="normal")
        self.btn_add_profile.config(state="normal")
        self.show_profiles_view()

    # ---------------- Profiles View ----------------
    def show_profiles_view(self):
        if not self.current_admin:
            self.status.set("Veuillez vous connecter.", type="error")
            self.show_login()
            return

        for w in self.content.winfo_children():
            w.destroy()

        # toolbar
        toolbar = Frame(self.content, padding=6)
        toolbar.pack(fill="x", pady=(0, 8))
        

        main = Frame(self.content)
        main.pack(fill="both", expand=True)

        # left cards
        left = Frame(main)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.canvas = tk.Canvas(left, borderwidth=0, highlightthickness=0)
        self.cards_frame = ttk.Frame(self.canvas)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # right details
        right = Frame(main, width=380, padding=12)
        right.pack(side="right", fill="y")
        Label(right, text="Informations personnelles", font=("Helvetica", 12, "bold")).pack(anchor="w")
        self.detail_preview = Label(right)
        self.detail_preview.pack(pady=(8, 10))
        self.detail_name = Label(right, text="", font=("Helvetica", 11, "bold"))
        self.detail_name.pack(anchor="w", pady=(6, 2))
        self.detail_sexe = Label(right, text="", foreground="#5a5a5a")
        self.detail_sexe.pack(anchor="w", pady=(2, 2))
        self.detail_notes = Label(right, text="", wraplength=340, justify="left")
        self.detail_notes.pack(anchor="w", pady=(6, 2))

        btns = Frame(right)
        btns.pack(fill="x", pady=(12, 0))
        Button(btns, text="✏️ Modifier", bootstyle="warning", command=self.edit_selected).pack(side="left", padx=6)
        Button(btns, text="🗑️ Supprimer", bootstyle="danger", command=self.delete_selected).pack(side="left", padx=6)

        self.reload_profiles()

    # ---------------- Reload & Render ----------------
    def reload_profiles(self):
        data = load_json(PROFILES_FILE, {"profiles": []})
        self.profiles_data = data
        self.count_label.config(text=f"Profiles: {len(self.profiles_data.get('profiles', []))}")
        self.card_images.clear()
        self.render_cards()
        self.status.set(f"{len(self.profiles_data.get('profiles', []))} profils chargés.", type="success")

    def render_cards(self):
        for w in self.cards_frame.winfo_children():
            w.destroy()

        query = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        profiles = self.profiles_data.get("profiles", [])
        if query:
            profiles = [p for p in profiles if query in (p.get("nom", "").lower() + " " + p.get("prenom", "").lower())]

        cols = 3
        pad_x = 12
        pad_y = 12
        for idx, p in enumerate(profiles):
            r = idx // cols
            c = idx % cols
            card = Frame(self.cards_frame, padding=8, relief="raised")
            card.grid(row=r, column=c, padx=pad_x, pady=pad_y, sticky="n")

            # hover effect
            def on_enter(e):
                e.widget.config(relief="solid", borderwidth=2, background="#f0f8ff")
            def on_leave(e):
                e.widget.config(relief="raised", borderwidth=1, background="SystemButtonFace")
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)

            img_path = p.get("image")
            if img_path and os.path.exists(img_path):
                try:
                    thumb = Image.open(img_path)
                    thumb.thumbnail(CARD_SIZE)
                    tkimg = ImageTk.PhotoImage(thumb)
                    self.card_images[p.get("id")] = tkimg
                    Label(card, image=tkimg).pack()
                except:
                    Label(card, text="Image error").pack()
            else:
                Label(card, text="No image").pack()

            Label(card, text=f"{p.get('nom', '')} {p.get('prenom', '')}", font=("Helvetica", 10, "bold")).pack()
            Label(card, text=p.get("sexe", ""), font=("Helvetica", 9), foreground="#5a5a5a").pack()
            Button(card, text="👁️ Voir", bootstyle="info-outline", command=lambda prof=p: self.show_details(prof)).pack(pady=(6,0))

    # ---------------- Detail View ----------------
    def show_details(self, profile):
        self.selected_profile = profile
        img_path = profile.get("image")
        if img_path and os.path.exists(img_path):
            thumb = Image.open(img_path)
            thumb.thumbnail(PREVIEW_SIZE)
            self.preview_image = ImageTk.PhotoImage(thumb)
            self.detail_preview.config(image=self.preview_image)
        else:
            self.detail_preview.config(image="", text="Pas d’image")

        self.detail_name.config(text=f"{profile.get('nom', '')} {profile.get('prenom', '')}")
        self.detail_sexe.config(text=f"Sexe: {profile.get('sexe', '')}")
        self.detail_notes.config(text=f"ID: {profile.get('id', '')}")

    # ---------------- Actions ----------------
    def edit_selected(self):
        if self.selected_profile:
            ProfileEditor(self, profile=self.selected_profile, on_save=self.reload_profiles)

    def delete_selected(self):
        if not self.selected_profile:
            alert_error("Aucun profil sélectionné.")
            return
        confirm = messagebox.askyesno("Confirmer", "Voulez-vous vraiment supprimer ce profil ?")
        if not confirm:
            return
        pid = self.selected_profile.get("id")
        data = self.profiles_data
        data["profiles"] = [p for p in data["profiles"] if p.get("id") != pid]
        save_json(PROFILES_FILE, data)
        self.status.set("Profil supprimé.", type="success")
        alert_success("Profil supprimé avec succès !")
        self.selected_profile = None
        self.reload_profiles()

    def open_create_modal(self):
        ProfileEditor(self, profile=None, on_save=self.reload_profiles)

# ---------------- Run ----------------
if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()
