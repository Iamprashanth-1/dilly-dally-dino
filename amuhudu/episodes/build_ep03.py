"""
AMUHUDU - EP 3 "Seven Stones" (~40s)
Shots follow story/STORYBOARD.md. Run:
    blender.exe --background --factory-startup --python build_ep03.py -- --out ep03.blend --qc
"""
import bpy, sys, os, math
from mathutils import Vector
from math import radians, sin, pi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from episode_lib import *  # noqa

sc = fresh("EP03", 40)
world_light(sky_strength=0.6, sun_deg=(46, 0, -60), energy=1.55,
            sun_color=(1.0, 0.9, 0.75), mist=0.0010,
            zenith=(0.18, 0.46, 0.86), horizon=(0.90, 0.94, 0.92))
add_clouds(seed=31, n=6, spread=48, height=(18, 27))
cam = add_camera(lens=35)

# ---- assets -------------------------------------------------------------
_, chowk = link("Chowk.blend", "LOC_Chowk")
place(chowk, (0, 0, 0))
link("Aru.blend", "CHAR_Aru")
link("Dev.blend", "CHAR_Dev")
link("Bujji.blend", "CHAR_Bujji")
link("Ammamma.blend", "CHAR_Ammamma")
_, stones_root = link("SevenStones.blend", "PROP_SevenStones")
_, ball_root = link("RedBall.blend", "PROP_RedBall")
place(stones_root, (0, 0, 0))
place(ball_root, (0, 0, 0))

aru, dev, bujji, amma = rig_of("Aru"), rig_of("Dev"), rig_of("Bujji"), rig_of("Ammamma")
ball = bpy.data.objects["PROP_RedBall_Ball"]
stones = [bpy.data.objects[f"PROP_SevenStones_Stone_{i}"] for i in range(7)]

# banyan platform centre ≈ (-7, 1.5), top z ≈ 0.22. Stack site on the platform:
STACK = Vector((-5.8, 0.2, 0.22))

# ---- hold positions ------------------------------------------------------
put(aru, 1, (-4.5, -1.3, 0), rot_z=-38)      # a few steps from the stack, facing it
put(dev, 1, (-6.3, 2.6, 0), rot_z=200)       # hiding behind the banyan trunk
put(bujji, 1, (3.2, -2.5, 0), rot_z=205)     # dozing far right until S3
put(amma, 1, (-10.2, -3.4, 0), rot_z=60)     # west of the chowk until S5

for r in (aru, dev, bujji, amma):
    rest_pose(r, 1)

# stones: neat lagori pyramid on the platform (until the crash)
stack_layout = [(-0.14, 0.02, 0), (0.14, 0.02, 0), (0, -0.13, 0),
                (0.07, 0.13, 0), (-0.07, 0.13, 0), (0, 0.02, 0.095), (0, 0.02, 0.19)]
for i, (dx, dy, dz) in enumerate(stack_layout):
    stones[i].location = (STACK.x + dx, STACK.y + dy, STACK.z + 0.05 + dz)
    stones[i].rotation_euler = (0, 0, random_rot := 0.4 * i)
    stones[i].keyframe_insert('location', frame=1)
    stones[i].keyframe_insert('rotation_euler', frame=1)

# ---- S1: Aru plays alone (f1-200) ----------------------------------------
shot(cam, "S1_alone", 1, 200,
     (-2.9, -4.0, 1.5), (-5.8, 0.3, 0.55), (-3.3, -3.4, 1.35), (-5.9, 0.3, 0.55), lens=32)
# throws the ball at the stack, misses, walks to restack
ball.keyframe_insert('location', frame=1)  # placeholder replaced below
ball.location = (-4.2, -1.1, 0.35)          # held at Aru's chest
ball.keyframe_insert('location', frame=60)
ball.location = (-5.6, 0.4, 0.5)            # arc
ball.keyframe_insert('location', frame=75)
ball.location = (-6.1, 0.9, 0.42)           # hits stack top… (miss: bounces off)
ball.keyframe_insert('location', frame=82)
ball.location = (-6.8, 2.4, 0.2)
ball.keyframe_insert('location', frame=100)
ball.location = (-6.6, 2.8, 0.11)
ball.keyframe_insert('location', frame=112)
key_face("Aru", "Mouth", "Open", 78, 0.8)   # "hup!" throw grunt
key_face("Aru", "Mouth", "Open", 95, 0.0)
set_pose(aru, 60, {'upper_arm.R': (-120, 0, -20)})   # throw wind-up
set_pose(aru, 78, {'upper_arm.R': (40, 0, -10), 'spine': (14, 0, 0)})
set_pose(aru, 110, {'upper_arm.R': (0, 0, 0), 'spine': (0, 0, 0)})
blink("Aru", 40)
blink("Aru", 150)
head_turn(aru, 90, -25)                     # watches the ball fly off
head_turn(aru, 130, 0)

# ---- S2: Dev watches from the banyan (f201-380) ---------------------------
shot(cam, "S2_dev_watches", 201, 380,
     (-5.2, 4.6, 1.55), (-5.4, -1.2, 0.8), (-4.9, 4.2, 1.5), (-5.6, -1.0, 0.8), lens=34)
walk(dev, 230, 258, (-6.3, 2.6), (-5.9, 2.75), rot_z=235, amp=18)   # peek out
put(dev, 259, (-5.9, 2.75, 0), rot_z=235)
# mimics Aru's throw silently
set_pose(dev, 300, {'upper_arm.R': (-120, 0, -20)})
set_pose(dev, 318, {'upper_arm.R': (40, 0, -10)})
set_pose(dev, 340, {'upper_arm.R': (0, 0, 0)})
blink("Dev", 260)
blink("Dev", 340)

# ---- S3: the throw, the crash, the laugh (f381-600) -----------------------
shot(cam, "S3_crash", 381, 600,
     (-1.8, -4.6, 1.15), (-6.2, 0.5, 0.45), (-2.2, -4.2, 1.25), (-6.2, 0.5, 0.5), lens=32)
# ball arc from Aru's hand to the stack
ball.location = (-4.35, -1.15, 0.4)
ball.keyframe_insert('location', frame=430)
ball.location = (-5.2, -0.2, 0.95)          # apex
ball.keyframe_insert('location', frame=448)
ball.location = (-6.08, 0.88, 0.35)         # IMPACT
ball.keyframe_insert('location', frame=455)
ball.location = (-6.9, 2.2, 0.3)            # bounces away
ball.keyframe_insert('location', frame=475)
ball.location = (-7.1, 2.6, 0.11)
ball.keyframe_insert('location', frame=490)
# Aru's throw + Dev steps out laughing
set_pose(aru, 432, {'upper_arm.R': (-125, 0, -20)})
set_pose(aru, 450, {'upper_arm.R': (45, 0, -10), 'spine': (15, 0, 0)})
set_pose(aru, 490, {'upper_arm.R': (0, 0, 0), 'spine': (0, 0, 0)})
walk(dev, 455, 495, (-5.9, 2.75), (-5.0, 0.2), rot_z=210, amp=25)
put(dev, 496, (-5.0, 0.2, 0), rot_z=215)
# stones burst at impact: each flies its own arc, lands scattered
scatter = [(-6.9, 1.9), (-5.4, 1.7), (-6.6, 0.2), (-5.2, 0.5),
           (-7.4, 0.6), (-5.8, 1.4), (-6.2, 2.0)]
for i, st in enumerate(stones):
    sx, sy = scatter[i]
    apex_z = STACK.z + 0.9 + 0.12 * i
    st.location = (STACK.x, STACK.y, STACK.z + 0.05 + stack_layout[i][2])
    st.keyframe_insert('location', frame=454)
    mid = ((STACK.x + sx) / 2, (STACK.y + sy) / 2, apex_z)
    st.location = mid
    st.rotation_euler = (radians(180 * 0.5), 0, 0.4 * i)
    st.keyframe_insert('location', frame=465)
    st.keyframe_insert('rotation_euler', frame=465)
    st.location = (sx, sy, 0.05)
    st.rotation_euler = (radians(180), 0, 0.6 * i)
    st.keyframe_insert('location', frame=478)
    st.keyframe_insert('rotation_euler', frame=478)
# Bujji hears the crash and charges in
dog_walk(bujji, 470, 540, (3.2, -2.5), (-3.2, -1.6), rot_z=200)
put(bujji, 541, (-3.2, -1.6, 0), rot_z=205)
wag(bujji, 545, 600)
# both boys laugh — mouths open, heads back
for f in (500, 520, 540, 560):
    key_face("Aru", "Mouth", "Open", f, 0.85)
    key_face("Aru", "Mouth", "Open", f + 8, 0.25)
    key_face("Dev", "Mouth", "Open", f + 4, 0.9)
    key_face("Dev", "Mouth", "Open", f + 12, 0.3)
key_face("Aru", "Mouth", "Smile", 495, 0.9)
key_face("Dev", "Mouth", "Smile", 500, 0.9)
set_pose(aru, 510, {'head': (0, -14, 0)})   # head back laughing
set_pose(aru, 580, {'head': (0, 0, 0)})
set_pose(dev, 515, {'head': (0, -12, 0)})
set_pose(dev, 580, {'head': (0, 0, 0)})
blink("Aru", 520)
blink("Dev", 535)

# ---- S4: montage — restack, catch, high-five (f601-900) -------------------
# cut A: restacking together
shot(cam, "S4_restack", 601, 690,
     (-3.9, -3.2, 1.0), (-5.9, 0.9, 0.45), (-3.7, -3.0, 1.05), (-5.9, 0.9, 0.45), lens=32)
sit(aru, 605, (-4.9, 0.2, 0.42), rot_z=25)
sit(dev, 605, (-6.9, 0.3, 0.42), rot_z=-30)
# stones hop back to the stack (comedic fast re-stack)
for i, st in enumerate(stones):
    sx, sy = scatter[i]
    st.location = (sx, sy, 0.05)
    st.keyframe_insert('location', frame=620)
    st.location = (STACK.x, STACK.y, STACK.z + 0.3 + 0.1 * i)
    st.keyframe_insert('location', frame=640 + i * 6)
    st.location = (STACK.x + stack_layout[i][0], STACK.y + stack_layout[i][1],
                   STACK.z + 0.05 + stack_layout[i][2])
    st.rotation_euler = (0, 0, 0.4 * i)
    st.keyframe_insert('location', frame=648 + i * 6)
    st.keyframe_insert('rotation_euler', frame=648 + i * 6)
blink("Aru", 640)
blink("Dev", 660)

# cut B: Dev catches the returning ball
shot(cam, "S4_catch", 691, 790,
     (-7.2, -3.4, 1.15), (-4.9, -0.2, 0.85), (-7.0, -3.2, 1.2), (-5.0, -0.3, 0.85), lens=34)
ball.location = (-4.5, 1.6, 0.9)            # Aru lobs it
ball.keyframe_insert('location', frame=710)
ball.location = (-5.4, 0.3, 1.35)           # arc apex
ball.keyframe_insert('location', frame=730)
ball.location = (-5.9, 0.9, 0.5)            # Dev grabs it
ball.keyframe_insert('location', frame=742)
set_pose(dev, 735, {'upper_arm.L': (-110, 0, 25), 'upper_arm.R': (-110, 0, -25)})  # catch!
set_pose(dev, 755, {'upper_arm.L': (-70, 0, 20), 'upper_arm.R': (-70, 0, -20)})
set_pose(aru, 710, {'upper_arm.R': (-130, 0, -15)})
set_pose(aru, 728, {'upper_arm.R': (30, 0, -10)})
set_pose(aru, 750, {'upper_arm.R': (0, 0, 0)})
blink("Dev", 745)

# cut C: the high-five (miss, miss, CONTACT)
shot(cam, "S4_highfive", 791, 900,
     (-5.8, -3.6, 1.3), (-5.8, 0.15, 1.15), (-5.6, -3.4, 1.35), (-5.8, 0.15, 1.15), lens=30)
put(aru, 795, (-5.2, 0.0, 0), rot_z=-95)
put(dev, 795, (-6.4, 0.3, 0), rot_z=95)
for at, (a_deg, d_deg) in ((800, (-150, -150)), (835, (-150, -150)), (868, (-155, -155))):
    set_pose(aru, at, {'upper_arm.R': (a_deg, 0, -5), 'forearm.R': (-20, 0, 0)})
    set_pose(dev, at + 4, {'upper_arm.R': (d_deg, 0, -8), 'forearm.R': (-20, 0, 0)})
    set_pose(aru, at + 18, {'upper_arm.R': (0, 0, 0)})
    set_pose(dev, at + 22, {'upper_arm.R': (0, 0, 0)})
key_face("Aru", "Mouth", "Smile", 870, 0.9)
key_face("Dev", "Mouth", "Smile", 872, 0.9)
key_face("Aru", "Mouth", "Open", 876, 0.7)   # "yay!"
key_face("Aru", "Mouth", "Open", 890, 0.2)
wag(bujji, 791, 900)

# ---- S5: collapse + Ammamma saw everything (f901-1200) --------------------
shot(cam, "S5_collapse", 901, 1200,
     (-3.2, -4.0, 1.35), (-6.0, 0.3, 0.7), (-3.0, -3.8, 1.4), (-6.1, 0.4, 0.7), lens=30)
sit(aru, 910, (-5.6, -0.9, 0.42), rot_z=20, lean=8)
sit(dev, 910, (-6.6, -0.7, 0.42), rot_z=-15, lean=8)
dog_walk(bujji, 915, 960, (-3.2, -1.6), (-6.1, -0.4), rot_z=215)
put(bujji, 961, (-6.1, -0.4, 0), rot_z=210)
wag(bujji, 965, 1200)
# Ammamma walks past, sees them, smiles knowingly
walk(amma, 930, 1040, (-9.9, -0.6), (-8.1, 0.7), rot_z=115)
put(amma, 1041, (-8.1, 0.7, 0), rot_z=130)
head_turn(amma, 1060, 25)                    # looks at the boys
key_face("Ammamma", "Mouth", "Smile", 1065, 0.7)
blink("Ammamma", 1080)
for f in (930, 960, 990, 1020):              # giggling fits keep going
    key_face("Aru", "Mouth", "Open", f, 0.6)
    key_face("Aru", "Mouth", "Open", f + 10, 0.15)
    key_face("Dev", "Mouth", "Open", f + 5, 0.65)
    key_face("Dev", "Mouth", "Open", f + 15, 0.2)
key_face("Aru", "Mouth", "Smile", 910, 0.9)
key_face("Dev", "Mouth", "Smile", 910, 0.9)
blink("Aru", 940)
blink("Dev", 975)
blink("Aru", 1100)

attach_sound(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio", "ep3_mix.wav"))

if "--qc" in sys.argv:
    qc_stills([100, 300, 500, 650, 760, 870, 1000, 1150], "EP3")

out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "ep03.blend"
save(out)
