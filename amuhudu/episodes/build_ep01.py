"""
AMUHUDU - EP 1 "The Boy Who Talks to Hills" (~38s)
Shots follow story/STORYBOARD.md. Run:
    blender.exe --background --factory-startup --python build_ep01.py -- --out ep01.blend --qc
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from episode_lib import *  # noqa

sc = fresh("EP01", 38)
world_light(sun_deg=(52, 0, -30), energy=1.5,
            sun_color=(1.0, 0.95, 0.85), mist=0.0012,
            sky_strength=0.5)
add_clouds(seed=11, n=6, spread=45, height=(17, 26))
cam = add_camera(lens=35)

# ---- assets -------------------------------------------------------------
_, hill_root = link("Hilltop.blend", "LOC_Hilltop")
place(hill_root, (0, 0, 0))
_, path_root = link("Path.blend", "LOC_Path")
place(path_root, (80, 0, 0))          # cutaway location, off to the side
_, jeep_root = link("Jeep.blend", "PROP_Jeep")
jeep_root.rotation_euler = (0, 0, -1.5708)   # face +Y (drives away from camera)
link("Aru.blend", "CHAR_Aru")
link("Bujji.blend", "CHAR_Bujji")

aru = rig_of("Aru")
bujji = rig_of("Bujji")

# ---- hold positions before entrances ------------------------------------
sit(aru, 1, (0, -9.35, 1.19), rot_z=0.0)          # on the bench from frame 1
put(bujji, 1, (7.5, -9.0, 0.50), rot_z=0)         # off-screen right until S4

# ---- S1 valley flyover (f1-150) ------------------------------------------
shot(cam, "S1_valley", 1, 150,
     (-7, 12, 7.5), (0, -55, 5), (-2.5, 4, 3.8), (0, -55, 5), lens=30)

# ---- S2 bench wide, Aru talks to the hills (f151-380) ---------------------
shot(cam, "S2_bench_wide", 151, 380,
     (2.4, -14.8, 1.05), (0, -9.3, 1.35), (1.8, -13.4, 1.15), (0, -9.3, 1.4), lens=40)
for f in (170, 200, 230, 260, 290):               # storytelling gestures
    set_pose(aru, f, {'upper_arm.L': (-45, 0, 25), 'upper_arm.R': (-45, 0, -25),
                      'forearm.L': (-30, 0, 0), 'forearm.R': (-30, 0, 0)})
    set_pose(aru, f + 15, {'upper_arm.L': (-15, 0, 15), 'upper_arm.R': (-15, 0, -15)})
for f in (175, 205, 235, 265, 295):               # mouth flaps = talking
    key_face("Aru", "Mouth", "Open", f, 0.7)
    key_face("Aru", "Mouth", "Open", f + 10, 0.15)
blink("Aru", 250)
blink("Aru", 330)

# ---- S3 Aru CU: hopeful, then a sigh (f381-570) ---------------------------
shot(cam, "S3_aru_cu", 381, 570,
     (0.55, -11.1, 1.80), (0, -9.35, 1.76), (0.35, -10.55, 1.80), (0, -9.35, 1.76), lens=50)
key_face("Aru", "Mouth", "Smile", 381, 0.0)
key_face("Aru", "Mouth", "Smile", 430, 0.45)
key_face("Aru", "Mouth", "Smile", 520, 0.05)
key_face("Aru", "Mouth", "Sad", 381, 0.0)
key_face("Aru", "Mouth", "Sad", 545, 0.8)
key_face("Aru", "Brow_R", "Brow.Raise", 400, 1.0)
key_face("Aru", "Brow_R", "Brow.Raise", 520, -0.6)
key_face("Aru", "Brow_L", "Brow.Raise", 400, 1.0)
key_face("Aru", "Brow_L", "Brow.Raise", 520, -0.6)
blink("Aru", 420)
blink("Aru", 500)

# ---- S4 Bujji arrives (f571-760) ------------------------------------------
shot(cam, "S4_bujji", 571, 760,
     (4.4, -13.8, 1.35), (1.4, -9.1, 0.95), (3.6, -12.6, 1.45), (1.3, -9.1, 0.95), lens=40)
dog_walk(bujji, 585, 675, (7.5, -9.0), (1.2, -9.0), rot_z=0, z1=0.50, z2=0.59)
put(bujji, 676, (1.2, -9.0, 0.59), rot_z=0)
wag(bujji, 690, 760)
key_face("Aru", "Mouth", "Smile", 690, 0.6)       # happy to see him
set_pose(aru, 700, {'upper_arm.L': (-25, 0, 30)})  # reach down…
set_pose(aru, 730, {'upper_arm.L': (-55, 0, 22)})  # …pat
set_pose(aru, 760, {'upper_arm.L': (-15, 0, 15)})
blink("Aru", 640)
blink("Aru", 720)

# ---- S5 from behind: tiny boy, huge hills (f761-950) ----------------------
shot(cam, "S5_two_shot", 761, 950,
     (0, -3.2, 2.5), (0, -60, 2.2), (0.4, -2.6, 2.6), (0, -60, 2.2), lens=26)
wag(bujji, 761, 950)
blink("Aru", 880)

# ---- S6 cutaway: a jeep on the path (f951-1075) ---------------------------
shot(cam, "S6_jeep", 951, 1075,
     (83.0, -26.0, 2.6), (79.0, -12.0, 1.0), (82.4, -25.0, 2.4), (79.0, -12.0, 1.0), lens=35)
for f, (jx, jy) in ((951, (80.35, -20)), (1010, (78.3, -13)), (1075, (78.6, -6))):
    jeep_root.location = (jx, jy, 0)
    jeep_root.keyframe_insert('location', frame=f)

# ---- S7 Aru hears something (f1076-1140) ----------------------------------
shot(cam, "S7_turn", 1076, 1140,
     (0.6, -11.2, 1.80), (0, -9.35, 1.76), lens=50)
set_pose(aru, 1076, {'spine': (0, 0, 0), 'head': (0, 0, 0)})
key_face("Aru", "Mouth", "Sad", 1076, 0.3)
key_face("Aru", "Mouth", "Sad", 1100, 0.0)
head_turn(aru, 1090, 0)
head_turn(aru, 1110, 38)                          # toward the village
blink("Aru", 1100)

frames = args_qc = None
attach_sound(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio", "ep1_mix.wav"))

if "--qc" in sys.argv:
    qc_stills([80, 300, 500, 680, 880, 1020, 1120], "EP1")

out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "ep01.blend"
save(out)
