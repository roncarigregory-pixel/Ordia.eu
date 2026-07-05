#!/usr/bin/env python3
"""Friendly setup window for Ordia Bridge (Tkinter, stdlib only).

The only screen a non-technical user sees:
  Welcome  ->  enter pairing code (or read it from the QR shown in Ordia)  ->  Connect
  ->  "Bridge collegato con successo."
No terminal, no Docker, no config files.
"""
import threading
import tkinter as tk
from tkinter import ttk

from ordia_bridge import pair, load_config, save_config, DEFAULT_BACKEND

BG = "#0f172a"
ACCENT = "#6366f1"
OK = "#10b981"
ERR = "#ef4444"


def launch_gui():
    cfg = load_config()
    backend = cfg.get("backend", DEFAULT_BACKEND)

    root = tk.Tk()
    root.title("Ordia Bridge")
    root.configure(bg=BG)
    root.geometry("460x420")
    root.resizable(False, False)

    tk.Label(root, text="Ordia Bridge", bg=BG, fg="white",
             font=("Segoe UI", 22, "bold")).pack(pady=(34, 4))
    tk.Label(root, text="Collega Ordia al tuo gestionale in un minuto.",
             bg=BG, fg="#94a3b8", font=("Segoe UI", 11)).pack()

    already = bool(cfg.get("token"))
    status_var = tk.StringVar(value="Bridge già collegato ✓" if already else "")

    frame = tk.Frame(root, bg=BG)
    frame.pack(pady=26, padx=40, fill="x")

    tk.Label(frame, text="Inserisci il codice di accoppiamento", bg=BG, fg="white",
             font=("Segoe UI", 11)).pack(anchor="w")
    tk.Label(frame, text="Lo trovi in Ordia → Configurazione → Bridge (puoi anche leggerlo dal QR Code).",
             bg=BG, fg="#64748b", font=("Segoe UI", 8), wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

    code_var = tk.StringVar()
    entry = tk.Entry(frame, textvariable=code_var, font=("Consolas", 22), justify="center",
                     width=8, bd=0, relief="flat")
    entry.pack(ipady=8, fill="x")
    entry.focus_set()

    status = tk.Label(root, textvariable=status_var, bg=BG, fg=OK if already else "white",
                      font=("Segoe UI", 10, "bold"), wraplength=380)
    status.pack(pady=8)

    def do_connect():
        code = code_var.get().strip()
        if len(code) < 4:
            status.config(fg=ERR); status_var.set("Inserisci il codice mostrato in Ordia.")
            return
        btn.config(state="disabled", text="Connessione…")
        status.config(fg="white"); status_var.set("Connessione in corso…")

        def worker():
            ok, msg = pair(backend, code)
            def done():
                if ok:
                    status.config(fg=OK); status_var.set("Bridge collegato con successo ✓")
                    btn.config(text="Fatto", state="normal", command=root.destroy)
                    tk.Label(root, text="Puoi chiudere questa finestra. Il Bridge lavora da solo in background.",
                             bg=BG, fg="#94a3b8", font=("Segoe UI", 9), wraplength=380).pack(pady=(0, 6))
                else:
                    status.config(fg=ERR); status_var.set(msg)
                    btn.config(text="Riprova", state="normal")
            root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    btn = tk.Button(root, text="Connetti", command=do_connect, bg=ACCENT, fg="white",
                    font=("Segoe UI", 12, "bold"), bd=0, relief="flat", padx=30, pady=10,
                    activebackground="#4f46e5", cursor="hand2")
    btn.pack(pady=6)
    root.bind("<Return>", lambda e: do_connect())

    # Persist consent for automatic log sharing (helps support).
    consent = tk.BooleanVar(value=cfg.get("log_consent", True))

    def save_consent():
        c = load_config(); c["log_consent"] = consent.get(); c.setdefault("backend", backend); save_config(c)

    ttk.Checkbutton(root, text="Invia log a Ordia per assistenza (consigliato)",
                    variable=consent, command=save_consent).pack(pady=(6, 0))

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
