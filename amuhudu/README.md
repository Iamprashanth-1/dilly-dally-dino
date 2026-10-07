# AMUHUDU — Animated Reels Project

Instagram Reels series built in Blender. **Everything here was built without rendering** — hand it to a laptop with more RAM for rendering.

```
amuhudu/
├── characters/
│   ├── build_characters.py    ← regenerates all characters from scratch
│   └── characters.blend      ← master file: all 6 rigged characters in one scene
├── environments/
│   ├── build_environment.py   ← regenerates all locations & props from scratch
│   └── environment.blend     ← master file: all locations laid out in a grid
├── library/                   ← REUSABLE ASSETS (one file each, Asset Browser ready)
│   ├── Characters: Aru, Dev, Ammamma, Latha, Ravi, Bujji
│   ├── Environments: Hilltop, Chowk, DevHouse, Path
│   ├── Props: RedBall, SevenStones, Bench, Jeep, PaperBoat
│   ├── Rig.blend             ← ground + sun + camera starter rig
│   ├── blender_assets.cats.txt ← Asset Browser catalog ("Amuhudu/…")
│   └── make_library.py       ← rebuilds library files from either master
├── episodes/                  ← ANIMATED EPISODES (render-ready)
│   ├── episode_lib.py         ← animation toolkit (walks, sits, shots, blinks, wags)
│   ├── build_ep01.py / ep01.blend   ← "The Boy Who Talks to Hills" (~38s)
│   ├── build_ep02.py / ep02.blend   ← "The New Family" (~35s)
│   └── build_ep03.py / ep03.blend   ← "Seven Stones" (~40s)
├── audio/                     ← VO + music, mixed & timed to the episodes
│   ├── ep1/2/3_mix.wav       ← ready-to-use soundtracks (also embedded in the blends)
│   ├── VO_SCRIPT.md           ← timed scripts for recording the real kid VO
│   └── make_audio.py          ← regenerates everything
├── story/
│   └── STORYBOARD.md         ← series bible + all 8 episode shot lists
├── previews/                 ← tiny QA thumbnails (NOT final renders)
└── README.md
```

## The cast (all inside `characters.blend`, each in its own collection)

| Collection | Character | Notes |
|---|---|---|
| `CHAR_Aru` | 9yo village boy — protagonist | Curly hair, red shirt |
| `CHAR_Dev` | 9yo city boy | Yellow shirt, white shoes |
| `CHAR_Ammamma` | Aru's grandmother | Saree, glasses, hair bun |
| `CHAR_Latha` | Dev's mother | Maroon saree, gold shawl |
| `CHAR_Ravi` | Dev's father | Blue shirt |
| `CHAR_Bujji` | The village dog | Rigged quadruped |
| `PREVIEW_Rig` | Ground + sun + camera | Delete or hide when building real scenes |

## How to animate with the rigs

- Each character has an armature named e.g. `Aru_Rig`. Select any bone and press `I` → *Location & Rotation* to keyframe. FK-style bones, X-mirror enabled by `.L` / `.R` naming.
- **Face acting without touching bones:** select the face part and use shape keys in the Object Data properties:
  - `Aru_Mouth` → `Smile`, `Sad`, `Open`
  - `Aru_Lid_L` / `Aru_Lid_R` → `Blink` (keyframe both together)
  - `Aru_Brow_L` / `Aru_Brow_R` → `Brow.Raise`
- All characters face **−Y**, stand on **Z=0**, real-world scale (kids ≈ 1.25 m).

## Using the reusable character library (`library/`)

Each character is its own asset file. In any episode scene you have 3 ways to pull them in:

1. **Asset Browser (easiest):** In Blender, open the Asset Browser editor → click the folder icon → choose `amuhudu/library/` → bookmark it. All characters show up under the **Amuhudu/Characters** catalog with thumbnails — **drag one into the viewport** and you're done.
2. **File → Link:** navigate to `library/Aru.blend` → `Collection` → `CHAR_Aru`. The character comes in as a linked instance (stays light — best for the low-RAM laptop).
3. **File → Append:** same navigation, but copies everything in — use this if you want to edit that character inside the episode file.

Tips for episodes:

- With a **linked** collection you can still animate: select the instance → `Object → Apply → Make Instances Real`, or pose the armature directly through the link.
- To move the whole character, select the empty/collection instance and move it — the rig rides along.
- If you change a character in the master file, re-run the library builder and every episode updates on next open:

```
blender.exe --background characters/characters.blend --python library/make_library.py
```



## The episodes (`episodes/`)

`ep01.blend` and `ep02.blend` are **fully animated and render-ready**: assets appended from the library, characters placed and keyframed (walk cycles, sit poses, gestures), facial shape keys animated (blinks, smiles, sad, talking mouths), Bujji's tail wag, the jeep drive-in, camera shots with jump cuts and slow push-ins, plus sun/sky lighting. Scene **timeline markers** name every shot (S1_valley, S2_bench_wide, …) matching `story/STORYBOARD.md`.

- Each episode is ~35–40 s at 30 fps, 1080×1920 (9:16), already set in Output properties.
- To render: open the file on the render laptop, set `Output → Output Path`, and render the animation (EEVEE recommended for speed; ~2–5 min/min of footage on a mid laptop).
- VO/audio is added in the video edit (CapCut/Premiere), not in Blender.

Rebuild or tweak an episode (change a camera, a pose, colors — anything, then rerun):

```
blender.exe --background --factory-startup --python episodes/build_ep01.py -- --out episodes/ep01.blend
```

Add `--qc` to also render small preview stills into `previews/`.

## Rendering on the other laptop

0. **⚠ Use Blender 5.x** (built and tested in 5.2.2). Opening these files in Blender 4.x or 3.x *will* break the characters (particle hair, materials and shape keys from 5.x don't survive older versions). Get the same version from blender.org — it's a free ~300 MB download.
1. Open `characters.blend` in Blender 4.2+ (built in 5.2 — open it there first, `File → Save` if the other machine has an older version).
2. For reels: `Output → Resolution` is already set to **1080×1920 @ 30 fps**.
3. Engine: episode files default to **Cycles** (the lighting is tuned for it — richer, more natural color). If renders are too slow, switch to EEVEE in `Render Properties`, and drop `Light Threshold` to 0.05 to keep shadows clean.
4. **Quality features & render cost:** the cast uses real **particle-hair strands** (with a mesh base for the silhouette), **subsurface-scattered skin**, and **woven fabric shaders**. These need roughly 2–3× the render time of flat colors. If renders are too slow on the laptop: in the character collections, turn down `rendered_child_count` on each `_Hair` particle system (30 → 10) and reduce Subsurface Weight to 0 — instantly cheaper, slightly less rich.
5. Don't render whole episodes in one file — one scene file per episode, linking characters (`File → Link` → drag from `characters.blend`) keeps files light on RAM.

## Rebuilding / editing characters

Everything is procedural. To regenerate from scratch:

```
blender.exe --background --factory-startup --python characters/build_characters.py -- --out characters/characters.blend
blender.exe --background characters/characters.blend --python characters/build_scans.py
```

The second step replaces the three **adults** (Ravi, Latha, Ammamma) with photoreal
RenderPeople scan characters (free rigged samples, stored in `assets/scans/`).
They are re-rigged to the same bone names (`thigh.L`, `upper_arm.L`, …) so every
episode animation works unchanged. **Aru, Dev and Bujji stay procedural** — no
free kid/dog scans exist. Skip the second command if you want the fully
stylized cast back.

### Adding the kids (RenderPeople, paid)

RenderPeople sells children only as **posed** static scans (no rigged kids
exist anywhere) — `build_scans.py` auto-rigs a standing posed scan with our
skeleton, so they still walk/sit in episodes:

1. Buy 2 × "Posed People New Gen" from the Children topic (~€39 each, pick
   natural standing poses; all formats included → download FBX):
   https://renderpeople.com/3d-people/ (filter: Children)
2. Drop the FBX (+ its textures) into `assets/scans/aru/` and `assets/scans/dev/`
3. Uncomment the two `POSED_SPECS` lines at the top of `build_scans.py`
4. Rerun: `blender.exe --background characters/characters.blend --python characters/build_scans.py`
   then `make_library.py` and the three episode builds

Optional upgrades: rigged senior woman for Ammamma (~€79, Rigged filter →
"Bestager" topic); Bujji the dog — RenderPeople has no animals, he stays stylized.

To change a character (colors, hair, clothes), edit the `specs` list at the bottom of `build_characters.py` — e.g. change `shirt_c=(0.68, 0.12, 0.10)` for Aru's shirt color, or `hair_style="curls"` to `"cap"`, `"bun"`, `"long"`, `"short"`.

## Visual style (how the vibrant look is achieved)

- **Color management:** every episode renders with the `Standard` view transform + `Medium High Contrast` look — that's what makes the colors pop (default AgX mutes everything).
- **Skies:** stylized gradient skies (vivid blue zenith → warm horizon; golden horizon for Ep 2), built in `episode_lib.world_light()`.
- **Light:** warm sun lamps, plus a subtle volumetric mist for valley depth (Ep 1 uses more than Ep 2).
- **Palette:** saturated grass/terracotta/fabric colors in `build_environment.py`, brighter clothing in `build_characters.py` — tweak the hex-like RGB tuples at the top of those scripts and rebuild to retheme.
- **Clouds:** soft emissive blobs via `episode_lib.add_clouds()` — per-episode seed controls their placement.

## Location blockouts (what each asset gives you)

- **Hilltop** — grass plateau, wooden bench facing the valley, tree, stone cairn, misty backdrop hills. Camera shoots from inland toward −Y to get the valley behind your characters.
- **Chowk** — village square on grass with dirt crossroads: big banyan tree with stone platform and aerial roots, teashop stall with awning + bench + table, bus stop shelter, 4 houses with terracotta pyramid roofs, lamp post, well.
- **DevHouse** — cream house with porch and terracotta roof, freshly-painted compound wall with gate, walkway, luggage boxes by the door (Ep 2), tree and bushes.
- **Path** — 40 m winding stone-slab path between grass banks, 3 trees, bushes, wooden fence, milestone, hill rising toward the village end.
- All locations have a `_Root` empty — select it to move/rotate/scale the whole set.
- Blockout quality: meant to be shot against as-is for early episodes, and upgraded piece by piece later (better grass, roof tiles, textures) without changing layout or cameras.

## Next steps

- [x] Environment blockout: hilltop, village square, Dev's house, stone path
- [x] Props: bench, banyan (in Chowk), red ball, seven stones, jeep, paper boats
- [ ] Record Aru's VO for Ep 1 first — animation goes faster when timed to voice
