#!/usr/bin/env python3
"""Friendly setup window for Ordia Bridge (Tkinter, stdlib only).

The only screen a non-technical user sees:
  Welcome  ->  enter the connection code (or read it from the QR shown in Ordia)
  ->  progress: Collegamento a Ordia… -> Verifica connessione… -> Bridge pronto
  ->  a big green check: "Il Bridge è pronto."
No terminal, no Docker, no config files.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk

from ordia_bridge import pair, load_config, save_config, DEFAULT_BACKEND

BG = "#0f172a"
CARD = "#111c34"
ACCENT = "#6366f1"
OK = "#10b981"
ERR = "#ef4444"
MUTED = "#94a3b8"


def launch_gui():
    cfg = load_config()
    backend = cfg.get("backend", DEFAULT_BACKEND)

    root = tk.Tk()
    root.title("Ordia Bridge")
    root.configure(bg=BG)
    root.geometry("480x480")
    root.resizable(False, False)

    tk.Label(root, text="Ordia Bridge", bg=BG, fg="white",
             font=("Segoe UI", 22, "bold")).pack(pady=(30, 2))
    tk.Label(root, text="Collega Ordia al tuo gestionale in un minuto.",
             bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack()

    already = bool(cfg.get("token"))

    # --- container that we swap between "form" and "done" -----------------------
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True)

    def clear_body():
        for w in body.winfo_children():
            w.destroy()

    def show_done():
        """Final screen: big green check + reassuring message."""
        clear_body()
        tk.Label(body, text="✓", bg=BG, fg=OK, font=("Segoe UI", 64, "bold")).pack(pady=(30, 4))
        tk.Label(body, text="Il Bridge è pronto.", bg=BG, fg="white",
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(body,
                 text="Da questo momento gli ordini verranno inviati\nautomaticamente al tuo gestionale.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10), justify="center").pack(pady=(8, 0))
        tk.Label(body, text="Puoi chiudere questa finestra: il Bridge lavora da solo in background.",
                 bg=BG, fg="#64748b", font=("Segoe UI", 9), wraplength=380,
                 justify="center").pack(pady=(14, 10))
        tk.Button(body, text="Fatto", command=root.destroy, bg=OK, fg="white",
                  font=("Segoe UI", 12, "bold"), bd=0, relief="flat", padx=40, pady=10,
                  activebackground="#0ea472", cursor="hand2").pack(pady=6)

    def show_form():
        clear_body()
        frame = tk.Frame(body, bg=BG)
        frame.pack(pady=(22, 6), padx=40, fill="x")

        tk.Label(frame, text="Codice di collegamento", bg=BG, fg="white",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(frame,
                 text="Questo codice collega in modo sicuro il PC del tuo gestionale al tuo "
                      "account Ordia. Lo trovi in Ordia → Impostazioni → Collega Bridge "
                      "(puoi anche leggerlo dal QR Code).",
                 bg=BG, fg="#64748b", font=("Segoe UI", 8), wraplength=390,
                 justify="left").pack(anchor="w", pady=(2, 10))

        code_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=code_var, font=("Consolas", 24), justify="center",
                         width=8, bd=0, relief="flat")
        entry.pack(ipady=9, fill="x")
        entry.focus_set()

        status_var = tk.StringVar(value="")
        status = tk.Label(body, textvariable=status_var, bg=BG, fg="white",
                          font=("Segoe UI", 10, "bold"), wraplength=390)
        status.pack(pady=(12, 4))

        bar = ttk.Progressbar(body, mode="determinate", length=360, maximum=100)

        # Persist consent for automatic log sharing (helps support).
        consent = tk.BooleanVar(value=cfg.get("log_consent", True))

        def save_consent():
            c = load_config()
            c["log_consent"] = consent.get()
            c.setdefault("backend", backend)
            save_config(c)

        def set_step(text, pct):
            status.config(fg="white")
            status_var.set(text)
            bar["value"] = pct
            body.update_idletasks()

        def do_connect():
            code = code_var.get().strip()
            if len(code) < 4:
                status.config(fg=ERR)
                status_var.set("Inserisci il codice mostrato in Ordia.")
                return
            btn.config(state="disabled", text="Collegamento…")
            entry.config(state="disabled")
            bar.pack(pady=(4, 2))

            def worker():
                root.after(0, lambda: set_step("Collegamento a Ordia…", 35))
                time.sleep(0.4)
                ok, msg = pair(backend, code)
                if ok:
                    root.after(0, lambda: set_step("Verifica connessione…", 75))
                    time.sleep(0.5)
                    root.after(0, lambda: set_step("Bridge pronto.", 100))
                    time.sleep(0.4)
                    root.after(0, show_done)
                else:
                    def fail():
                        bar.pack_forget()
                        status.config(fg=ERR)
                        status_var.set(msg)
                        btn.config(text="Riprova", state="normal")
                        entry.config(state="normal")
                    root.after(0, fail)

            threading.Thread(target=worker, daemon=True).start()

        btn = tk.Button(body, text="Connetti", command=do_connect, bg=ACCENT, fg="white",
                        font=("Segoe UI", 12, "bold"), bd=0, relief="flat", padx=30, pady=10,
                        activebackground="#4f46e5", cursor="hand2")
        btn.pack(pady=6)
        root.bind("<Return>", lambda e: do_connect())

        ttk.Checkbutton(body, text="Invia log a Ordia per assistenza (consigliato)",
                        variable=consent, command=save_consent).pack(pady=(8, 0))

    if already:
        show_done()
    else:
        show_form()

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
