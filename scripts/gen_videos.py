"""Regenerate Ordia tutorial videos (IT + EN, 16:9 + 9:16) with a FASTER, more
dynamic rhythm. Narration (edge-tts, fast rate) drives the pacing; the base
visuals are time-scaled so the whole clip is covered by the voiceover with no
dead air. Idempotent, isolated from the running app.

Run:  python /app/scripts/gen_videos.py
"""
import asyncio, os, subprocess

PUB = "/app/frontend/public"
WORK = "/app/scripts/_video_work"
os.makedirs(WORK, exist_ok=True)

GAP = 0.30   # seconds of silence between narration segments
TAIL = 0.7   # trailing silence
RATE = "+25%"  # snappier delivery

LANGS = {
    "it": {
        "voice": "it-IT-IsabellaNeural",
        "out16": "ordia-tutorial-16x9.mp4",
        "out9": "ordia-tutorial-9x16.mp4",
        "segments": [
            "Ogni giorno i grossisti annegano negli ordini: WhatsApp, email, PDF, perfino foto. E qualcuno li riscrive a mano, uno per uno.",
            "Ecco Ordia. Trasforma qualsiasi ordine, da qualsiasi canale, in un ordine pronto per il tuo gestionale. In automatico.",
            "Incolli o carichi l'ordine: l'AI legge cliente, prodotti e quantità e li abbina al tuo catalogo.",
            "Controlli solo le righe incerte. Tutto il resto è già fatto. Un click e approvi.",
            "E qui sta il punto: Ordia non è un gestionale, lavora con quello che usi già. Con Ordia Bridge si collega anche a sistemi senza API: impara la tua procedura e la esegue per te.",
            "Dal caos all'ordine pronto. Questa è Ordia.",
        ],
    },
    "en": {
        "voice": "en-US-AriaNeural",
        "out16": "ordia-tutorial-en-16x9.mp4",
        "out9": "ordia-tutorial-en-9x16.mp4",
        "segments": [
            "Every day, wholesale distributors drown in orders. WhatsApp messages, emails, PDFs, even photos. And someone retypes every single one, by hand.",
            "Meet Ordia. It turns any order, from any channel, into a clean order ready for your ERP. Automatically.",
            "Just paste or upload the order. Ordia's AI reads the customer, the products and the quantities, and matches them to your catalog.",
            "You only review the lines it's unsure about. Everything else is done. One click, and you approve.",
            "And here's the key. Ordia is not an ERP, it works with the one you already use. With Ordia Bridge it even connects to systems without an API: it learns your procedure and runs it for you.",
            "From chaos to order ready. That's Ordia.",
        ],
    },
}

# Base visuals per aspect ratio — pristine originals are backed up in WORK once,
# so we never read a file we're about to overwrite.
BASE = {"16": f"{WORK}/orig_16x9.mp4", "9": f"{WORK}/orig_9x16.mp4"}
ORIG_SRC = {"16": f"{PUB}/ordia-tutorial-16x9.mp4", "9": f"{PUB}/ordia-tutorial-9x16.mp4"}


def ensure_base():
    import shutil
    for k, dst in BASE.items():
        if not os.path.exists(dst):
            shutil.copy2(ORIG_SRC[k], dst)
            print(f"backed up pristine base {k} -> {dst}")


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


async def synth(lang, cfg):
    import edge_tts
    files = []
    t = 0.0
    for i, text in enumerate(cfg["segments"]):
        out = f"{WORK}/{lang}_seg_{i}.mp3"
        await edge_tts.Communicate(text, cfg["voice"], rate=RATE).save(out)
        d = dur(out)
        files.append((t, out, d))
        t += d + GAP
    total = t - GAP + TAIL
    return files, total


def build_audio(lang, files, total):
    inputs, filters = [], []
    for i, (start, path, _d) in enumerate(files):
        inputs += ["-i", path]
        ms = int(start * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    mix_in = "".join(f"[a{i}]" for i in range(len(files)))
    filters.append(f"{mix_in}amix=inputs={len(files)}:normalize=0:dropout_transition=0[m]")
    filters.append(f"[m]apad=whole_dur={total},atrim=0:{total},aresample=44100[out]")
    audio = f"{WORK}/{lang}_voice.m4a"
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-c:a", "aac", "-b:a", "192k", audio],
                   check=True, capture_output=True)
    return audio


def render(base_path, audio, total, out):
    base_dur = dur(base_path)
    speed = max(1.15, base_dur / total)  # never slower than 1.15x
    fast = f"{WORK}/fast_{os.path.basename(out)}"
    subprocess.run(["ffmpeg", "-y", "-an", "-i", base_path,
                    "-filter:v", f"setpts=PTS/{speed}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", fast],
                   check=True, capture_output=True)
    fast_dur = dur(fast)
    subprocess.run(["ffmpeg", "-y", "-i", fast, "-i", audio,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{fast_dur}", "-shortest", out],
                   check=True, capture_output=True)
    print(f"  -> {out}  video={fast_dur:.1f}s  speed={speed:.2f}x")


async def main():
    ensure_base()
    for lang, cfg in LANGS.items():
        files, total = await synth(lang, cfg)
        audio = build_audio(lang, files, total)
        print(f"[{lang}] narration total={total:.1f}s")
        render(BASE["16"], audio, total, f"{PUB}/{cfg['out16']}")
        render(BASE["9"], audio, total, f"{PUB}/{cfg['out9']}")
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
