"""Generate the ENGLISH tutorial voiceover and mux it over the existing visuals.
Reuses /app/frontend/public/ordia-tutorial-{16x9,9x16}.mp4 (Italian) visuals,
replaces audio with a native English edge-tts voiceover. Idempotent, isolated
from the running app.
"""
import asyncio, os, subprocess, json, tempfile

PUB = "/app/frontend/public"
WORK = "/app/scripts/_video_work"
os.makedirs(WORK, exist_ok=True)

VOICE = "en-US-AriaNeural"  # professional female English voice
SPEED = 1.25  # speed up the visuals for a snappier rhythm

# (start_seconds, text) — placed on the SPED-UP (~70s) timeline
SEGMENTS = [
    (0.4,  "Every day, wholesale distributors drown in orders. WhatsApp messages, emails, PDFs, even photos. And someone retypes every single one, by hand."),
    (12.5, "Meet Ordia. It turns any order, from any channel, into a clean order ready for your ERP. Automatically."),
    (22.5, "Just paste or upload the order. Ordia's AI reads the customer, the products and the quantities, and matches them to your catalog."),
    (35.5, "You only review the lines it's unsure about. Everything else is done. One click, and you approve."),
    (47.0, "And here's the key. Ordia is not an ERP. It works with the one you already use. With Ordia Bridge it even connects to systems without an API. It learns your procedure and runs it for you."),
    (64.0, "From chaos to order ready. That's Ordia."),
]


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


async def synth():
    import edge_tts
    files = []
    for i, (start, text) in enumerate(SEGMENTS):
        out = f"{WORK}/seg_{i}.mp3"
        await edge_tts.Communicate(text, VOICE, rate="+16%").save(out)
        files.append((start, out, dur(out)))
        print(f"seg {i}: start={start} dur={files[-1][2]:.2f}")
    return files


def build_audio(files, total):
    # place each segment at its start via adelay, mix, pad/trim to total
    inputs = []
    filters = []
    for i, (start, path, _d) in enumerate(files):
        inputs += ["-i", path]
        ms = int(start * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
    mix_in = "".join(f"[a{i}]" for i in range(len(files)))
    filters.append(f"{mix_in}amix=inputs={len(files)}:normalize=0:dropout_transition=0[mixed]")
    filters.append(f"[mixed]apad=whole_dur={total},atrim=0:{total},aresample=44100[out]")
    fc = ";".join(filters)
    audio = f"{WORK}/voice_en.m4a"
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]",
           "-c:a", "aac", "-b:a", "192k", audio]
    subprocess.run(cmd, check=True, capture_output=True)
    print("audio built:", audio, dur(audio))
    return audio


def mux(video_it, audio, out):
    vdur = dur(video_it)
    cmd = ["ffmpeg", "-y", "-i", video_it, "-i", audio,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{vdur}", "-shortest", out]
    subprocess.run(cmd, check=True, capture_output=True)
    print("muxed:", out, dur(out))


def speed_video(src, dst, speed):
    # speed up visuals only (no audio), keep quality
    subprocess.run(["ffmpeg", "-y", "-an", "-i", src,
                    "-filter:v", f"setpts=PTS/{speed}",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", dst],
                   check=True, capture_output=True)
    print("sped video:", dst, dur(dst))


async def main():
    files = await synth()
    for src, dst in [("ordia-tutorial-16x9.mp4", "ordia-tutorial-en-16x9.mp4"),
                     ("ordia-tutorial-9x16.mp4", "ordia-tutorial-en-9x16.mp4")]:
        fast = f"{WORK}/fast_{src}"
        speed_video(f"{PUB}/{src}", fast, SPEED)
        total = dur(fast)
        audio = build_audio(files, total)
        mux(fast, audio, f"{PUB}/{dst}")
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
