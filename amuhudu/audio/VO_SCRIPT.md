# AMUHUDU — VO Scripts & Audio Guide (Ep 1–2)

Every line below is already **timed to the shot markers** in the episode files.
Scratch audio (Windows TTS "Hazel" narrator + synthesized music) is generated in
this folder and embedded in the episode `.blend` files as a guide track.

**For the real videos:** record a kid (or kid-ish) voice reading these lines,
roughly matching the start times below, then rebuild the mix:

```
python make_audio.py        # regenerates all wavs (skips TTS lines that already exist)
```

To use a real recording instead of TTS: replace `ep1_line00.wav` … `ep2_line06.wav`
with your recordings (44.1 kHz mono wav, same filenames) and delete the
`ep{1,2}_vo.wav / _music.wav / _mix.wav` files so they regenerate.

---

## EP 1 — "The Boy Who Talks to Hills" (38s)

| Start | Shot | Line (Aru, 9yo, voiceover — calm, a little dreamy) |
|---|---|---|
| 0.6s | S1 valley | "Everyone asks me... why do you talk to the hills?" |
| 5.6s | S1→S2 | "They never answer. But they always listen." |
| 13.2s | S3 close-up | "Some days I tell them about school. About Ammamma's sambar. About everything." |
| 20.6s | S4 Bujji | "This is Bujji. He listens too. But he never talks back." |
| 26.2s | S5 silhouette | "Ammamma says, friends are like seasons. They arrive... when you stop waiting." |
| 32.6s | S6 jeep | "That morning, on the old stone path," |
| 36.1s | S7 turn | "something else arrived in Amuhudu." |

**Music:** "Morning Hills" — slow flute over warm pads (D major). Music ducks under every line automatically.

---

## EP 2 — "The New Family" (35s)

| Start | Shot | Line |
|---|---|---|
| 0.6s | S1 arrival | "New faces in Amuhudu. That never happens." |
| 7.6s | S2 Dev peek | "A boy. My age. Hiding behind his father's jeep." |
| 13.6s | S3 approach | "I walked past, very slow... pretending not to look." |
| 18.8s | S4 lid | "And then... a box lid, rolling straight to my feet." |
| 22.8s | S5 freeze | "Neither of us moved. For a long, long time." |
| 25.8s | S6 wave CU | "He waved first. I still remember that." |
| 29.8s | S7 end | "Ammamma says a season arrived that day. I just know... it felt like the hills finally answered." |

**Music:** "Golden Afternoon" — kalimba-style plucks over a warm pad (G major), with a little glockenspiel answer at the end.

---

## Files in this folder

| File | What it is |
|---|---|
| `ep1_mix.wav` / `ep2_mix.wav` | **Ready to use** — VO + music with auto-ducking. Embedded in the .blend files as guide track; also import this into CapCut/Premiere. |
| `ep1_vo.wav` / `ep2_vo.wav` | Narration only |
| `ep1_music.wav` / `ep2_music.wav` | Music bed only |
| `ep1_lineXX.wav` / `ep2_lineXX.wav` | Individual scratch lines — replace these with real recordings |
| `make_audio.py` | Regenerates everything; edit `EPISODES` at the top to change words/timings |

**Recording tips for the real VO:** phone mic 15–20 cm from the mouth, quiet room
(under a blanket works!), one take per line, leave 1s of silence before/after
each line. If a line runs long, it's fine — the mix ducks the music but won't
shift your picture; keep lines under their shot lengths listed above.
