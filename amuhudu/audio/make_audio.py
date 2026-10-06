"""
AMUHUDU - Audio Pass Builder
============================
Generates for each episode:
  ep{N}_vo.wav      scratch narration (Windows TTS "Hazel", storybook pace)
  ep{N}_music.wav   original music bed (procedural, numpy-synthed)
  ep{N}_mix.wav     final mix: music ducked under every VO line

All timings match the shot markers in the .blend files (30 fps).

Run:  python make_audio.py
"""
import os, subprocess, wave, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
FPS = 30.0
TTS_VOICE = "Microsoft Hazel Desktop"
TTS_RATE = -1          # slightly slower = storybook pace

# ---------------------------------------------------------------- VO scripts
# (start_seconds, text) — start times match scene shot markers
EPISODES = {
    1: {
        "duration": 38.0,
        "title": "The Boy Who Talks to Hills",
        "vo": [
            (0.6,  "Everyone asks me... why do you talk to the hills?"),
            (5.6,  "They never answer. But they always listen."),
            (13.2, "Some days I tell them about school. About Ammamma's sambar. About everything."),
            (20.6, "This is Bujji. He listens too. But he never talks back."),
            (26.2, "Ammamma says, friends are like seasons. They arrive... when you stop waiting."),
            (32.6, "That morning, on the old stone path,"),
            (36.1, "something else arrived in Amuhudu."),
        ],
    },
    3: {
        "duration": 40.0,
        "title": "Seven Stones",
        "vo": [
            (0.8,  "I had a game. Seven stones, one ball... and no one to play with."),
            (7.4,  "Until that morning... somebody was watching. From behind the old banyan tree."),
            (13.4, "I threw. The stones flew. And we laughed, loud enough for the whole village."),
            (21.0, "Turns out, seven stones feel lighter... when two people carry them."),
            (31.0, "I didn't need a team. I just needed one person. And one dog who thinks he's people."),
        ],
    },
    2: {
        "duration": 35.0,
        "title": "The New Family",
        "vo": [
            (0.6,  "New faces in Amuhudu. That never happens."),
            (7.6,  "A boy. My age. Hiding behind his father's jeep."),
            (13.6, "I walked past, very slow... pretending not to look."),
            (18.8, "And then... a box lid, rolling straight to my feet."),
            (22.8, "Neither of us moved. For a long, long time."),
            (25.8, "He waved first. I still remember that."),
            (29.8, "Ammamma says a season arrived that day. I just know... it felt like the hills finally answered."),
        ],
    },
}

# ---------------------------------------------------------------- TTS
def tts_line(text, path):
    ps = (
        "Add-Type -AssemblyName System.Speech;"
        f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.SelectVoice('{TTS_VOICE}');"
        f"$s.Rate = {TTS_RATE};"
        "$s.SetOutputToWaveFile('%s', (New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)));"
        "$s.Speak('%s');"
        "$s.Dispose()"
    ) % (path.replace("\\", "\\\\"), text.replace("'", ""))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
    return sr, data

def write_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((data * 32767).astype(np.int16).tobytes())

# ---------------------------------------------------------------- music synth
def adsr(n, a=0.02, d=0.1, s=0.7, r=0.2):
    t = np.linspace(0, 1, n)
    env = np.piecewise(t, [t < a / (a + d + r + 0.1), t < 1 - r / (a + d + r + 0.1)],
                       [lambda x: x / max(a, 1e-4) * 0.4,
                        lambda x: 0.4 + s * 0.6])
    return env

def tone(freq, dur, kind="flute", vol=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "flute":                     # soft breathy flute
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
        x = np.sin(2 * np.pi * freq * vib * t)
        x += 0.28 * np.sin(2 * np.pi * 2 * freq * t)
        x += 0.10 * np.sin(2 * np.pi * 3 * freq * t)
        env = np.minimum(1, t / 0.18) * np.exp(-t * 0.5 / dur)
        x = x * env
    elif kind == "pluck":                   # kalimba-ish pluck
        x = (np.sin(2 * np.pi * freq * t)
             + 0.5 * np.sin(2 * np.pi * 2 * freq * t)
             + 0.25 * np.sin(2 * np.pi * 3.01 * freq * t))
        x *= np.exp(-t * 6.0 / dur)
    elif kind == "pad":                     # warm chord pad
        x = (np.sin(2 * np.pi * freq * t)
             + 0.4 * np.sin(2 * np.pi * freq * 1.005 * t)
             + 0.3 * np.sin(2 * np.pi * 2 * freq * t))
        x *= np.minimum(1, t / (dur * 0.35)) * np.minimum(1, (dur - t) / (dur * 0.35))
    return x * vol

def place(buf, sig, at):
    i = int(at * SR)
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[:j - i]

NOTE = {"C": 261.63, "D": 293.66, "E": 329.63, "F": 349.23, "G": 392.00,
        "A": 440.00, "B": 493.88, "C5": 523.25, "D5": 587.33, "E5": 659.26,
        "G5": 783.99, "A5": 880.00}
def f(semi):  # semitones above C4
    return 261.63 * 2 ** (semi / 12)

def music_ep1(dur):
    """'Morning Hills' — slow D-major pentatonic flute over warm pads."""
    buf = np.zeros(int(dur * SR))
    # chord pads: D, Bm, G, A — one every ~4.75s, looping
    chords = [(f(-7), f(2), f(4)), (f(-9), f(0), f(2)), (f(-12), f(-1), f(2)), (f(-10), f(-3), f(2))]
    bar = 4.75
    t0 = 0.0
    ci = 0
    while t0 < dur:
        for semi in chords[ci % 4]:
            place(buf, tone(f(semi - 12), bar, "pad", vol=0.05), t0)
        ci += 1
        t0 += bar
    # melody: D E F# A B A F# E D ... pentatonic phrases, sparse
    phrases = [
        (1.0,  [(f(2), 1.2), (f(4), 0.8), (f(7), 1.6)]),
        (6.0,  [(f(9), 1.4), (f(7), 0.9), (f(4), 1.8)]),
        (11.0, [(f(2), 0.9), (f(4), 0.9), (f(7), 0.9), (f(9), 2.2)]),
        (17.0, [(f(11), 1.4), (f(9), 1.0), (f(7), 2.0)]),
        (22.5, [(f(7), 1.2), (f(4), 1.0), (f(2), 1.2), (f(-1), 2.4)]),
        (28.5, [(f(0), 1.2), (f(2), 1.0), (f(4), 2.4)]),
        (33.5, [(f(4), 1.0), (f(7), 1.0), (f(9), 1.2), (f(11), 2.2)]),
    ]
    for at, notes in phrases:
        tt = at
        for semi, d in notes:
            place(buf, tone(f(semi), d, "flute", vol=0.16), tt)
            tt += d * 0.85
    return buf

def music_ep2(dur):
    """'Golden Afternoon' — kalimba plucks, G-major, light and hopeful."""
    buf = np.zeros(int(dur * SR))
    chords = [(f(-5), f(-1), f(2)), (f(-7), f(0), f(2)), (f(-10), f(-1), f(2)), (f(-8), f(0), f(4))]
    bar = 4.375
    t0, ci = 0.0, 0
    while t0 < dur:
        for semi in chords[ci % 4]:
            place(buf, tone(f(semi - 12), bar, "pad", vol=0.045), t0)
        # arpeggio plucks on the bar
        arp = chords[ci % 4] + (chords[ci % 4][0] + 12,)
        for k, semi in enumerate(arp):
            place(buf, tone(f(semi), 0.5, "pluck", vol=0.13), t0 + k * 0.28)
            place(buf, tone(f(semi), 0.5, "pluck", vol=0.10), t0 + 2.2 + k * 0.28)
        ci += 1
        t0 += bar
    # little melodic sparkles
    sparkles = [(3.4, f(9)), (7.8, f(11)), (12.2, f(14)), (16.4, f(12)),
                (21.0, f(11)), (25.4, f(14)), (30.0, f(16))]
    for at, fq in sparkles:
        place(buf, tone(fq, 0.7, "pluck", vol=0.12), at)
        place(buf, tone(fq * 1.5, 0.5, "pluck", vol=0.06), at + 0.12)
    # soft glockenspiel answer at the end
    place(buf, tone(f(16), 1.2, "pluck", vol=0.12), dur - 2.2)
    place(buf, tone(f(19), 1.6, "pluck", vol=0.12), dur - 1.4)
    return buf

def music_ep3(dur):
    """'Stone Game' — bouncy D-major plucks, game-time energy."""
    buf = np.zeros(int(dur * SR))
    chords = [(f(-7), f(2), f(4)), (f(-12), f(-1), f(2)), (f(-10), f(-3), f(2)), (f(-12), f(-5), f(0))]
    bar = 4.0
    t0, ci = 0.0, 0
    while t0 < dur:
        for semi in chords[ci % 4]:
            place(buf, tone(f(semi - 12), bar, "pad", vol=0.04), t0)
        arp = chords[ci % 4] + (chords[ci % 4][2] + 7,)
        for k, semi in enumerate(arp):
            place(buf, tone(f(semi), 0.45, "pluck", vol=0.14), t0 + k * 0.24)
            place(buf, tone(f(semi), 0.45, "pluck", vol=0.11), t0 + 2.0 + k * 0.24)
        ci += 1
        t0 += bar
    sparkles = [(2.6, f(14)), (6.8, f(16)), (11.4, f(18)), (15.6, f(16)),
                (19.8, f(14)), (24.2, f(18)), (28.6, f(19)), (33.0, f(21)), (37.0, f(23))]
    for at, fq in sparkles:
        place(buf, tone(fq, 0.6, "pluck", vol=0.13), at)
        place(buf, tone(fq * 1.5, 0.45, "pluck", vol=0.06), at + 0.1)
    place(buf, tone(f(14), 1.2, "pluck", vol=0.12), dur - 2.4)
    place(buf, tone(f(19), 1.8, "pluck", vol=0.13), dur - 1.5)
    return buf

# ---------------------------------------------------------------- mix
def build_episode(ep, spec):
    dur = spec["duration"]
    # --- VO track
    vo = np.zeros(int(dur * SR))
    line_files = []
    for i, (at, text) in enumerate(spec["vo"]):
        lp = os.path.join(HERE, f"ep{ep}_line{i:02d}.wav")
        if not os.path.exists(lp):
            tts_line(text, lp)
        sr, d = read_wav(lp)
        if sr != SR:
            x = np.linspace(0, 1, int(len(d) * SR / sr))
            d = np.interp(x, np.linspace(0, 1, len(d)), d)
        d = d * 0.95
        fade = int(0.05 * SR)
        d[:fade] *= np.linspace(0, 1, fade)
        d[-fade:] *= np.linspace(1, 0, fade)
        place(vo, d, at)
        line_files.append((at, at + len(d) / SR, text))
    write_wav(os.path.join(HERE, f"ep{ep}_vo.wav"), vo)

    # --- music track
    mus = {1: music_ep1, 2: music_ep2, 3: music_ep3}[ep](dur)
    mus = mus * 0.5
    write_wav(os.path.join(HERE, f"ep{ep}_music.wav"), mus)

    # --- mix with ducking (music dips under each VO line)
    duck = np.ones_like(mus)
    for a, b, _ in line_files:
        i0, i1 = int(max(0, a - 0.35) * SR), int(min(dur, b + 0.35) * SR)
        duck[i0:i1] = 0.45
    # smooth the duck edges
    k = np.hanning(int(0.25 * SR))
    duck = np.convolve(duck, k / k.sum(), mode="same")
    mix = (vo * 1.0 + mus * duck) * 0.82
    fade = int(0.6 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    write_wav(os.path.join(HERE, f"ep{ep}_mix.wav"), mix)
    return line_files

if __name__ == "__main__":
    for ep, spec in EPISODES.items():
        lines = build_episode(ep, spec)
        print(f"EP{ep} '{spec['title']}': {len(lines)} VO lines, {spec['duration']}s "
              f"-> ep{ep}_mix.wav")
    print("DONE")
