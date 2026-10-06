"""
AMUHUDU - EP 2 "The New Family" (~35s)
Shots follow story/STORYBOARD.md. Run:
    blender.exe --background --factory-startup --python build_ep02.py -- --out ep02.blend --qc
"""
import bpy, sys, os
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from episode_lib import *  # noqa

sc = fresh("EP02", 35)
world_light(sun_deg=(42, 0, -140), energy=1.75,  # golden afternoon
            sun_color=(1.0, 0.82, 0.60), mist=0.0008, sky_strength=0.62,
            zenith=(0.20, 0.48, 0.82), horizon=(1.0, 0.76, 0.48))
add_clouds(seed=23, n=5, spread=50, height=(18, 27))
cam = add_camera(lens=35)

# ---- assets -------------------------------------------------------------
_, house_root = link("DevHouse.blend", "LOC_DevHouse")
place(house_root, (0, 0, 0))
_, path_root = link("Path.blend", "LOC_Path")
place(path_root, (0, -58, -0.02), rot_z=180)   # path runs south, hill-end away from house
_, jeep_root = link("Jeep.blend", "PROP_Jeep")
place(jeep_root, (5.2, -5.6, 0), rot_z=0)   # parked facing the gate (-X)
link("Aru.blend", "CHAR_Aru")
link("Bujji.blend", "CHAR_Bujji")
link("Dev.blend", "CHAR_Dev")
link("Ravi.blend", "CHAR_Ravi")
link("Latha.blend", "CHAR_Latha")

ravi, latha, dev = rig_of("Ravi"), rig_of("Latha"), rig_of("Dev")
aru, bujji = rig_of("Aru"), rig_of("Bujji")

# ---- holds / entrances ---------------------------------------------------
put(ravi, 1, (4.0, -4.4, 0), rot_z=230)      # by the jeep, walks to door in S1
put(latha, 1, (-2.4, -6.8, 0), rot_z=180)    # west of the gate, pointing at the hills
put(dev, 1, (5.7, -4.3, 0), rot_z=180)       # hiding behind the jeep
put(aru, 1, (0, -58, 0), rot_z=180)          # far down the path until S3
put(bujji, 1, (0.9, -58, 0), rot_z=180)

# Latha points at the hills
set_pose(latha, 60, {'upper_arm.L': (-70, 0, -25), 'forearm.L': (-15, 0, 0)})

# ---- S1 arrival wide: Ravi carries a box in (f1-210) ----------------------
shot(cam, "S1_arrival", 1, 210,
     (9.5, -15, 2.8), (2, -3, 1.2), (8.6, -13.5, 2.6), (2, -3, 1.2), lens=32)
walk(ravi, 20, 150, (4.0, -4.4), (0.8, -2.0), rot_z=230)
set_pose(ravi, 1, {'upper_arm.L': (-70, 0, -35), 'upper_arm.R': (-70, 0, 35),
                   'forearm.L': (-55, 0, 0), 'forearm.R': (-55, 0, 0)})   # carrying a box
put(ravi, 151, (0.8, -2.0, 0), rot_z=230)
blink("Latha", 120)

# ---- S2 Dev peeks from behind the jeep (f211-390) -------------------------
shot(cam, "S2_dev_peek", 211, 390,
     (9.0, -11.8, 1.15), (4.6, -6.9, 0.85), (8.4, -11.0, 1.2), (4.6, -6.9, 0.85), lens=40)
walk(dev, 240, 268, (5.7, -4.3), (3.4, -6.9), rot_z=250, amp=20)
walk(dev, 268, 300, (3.4, -6.9), (4.7, -7.1), rot_z=180, amp=20)
put(dev, 301, (4.7, -7.1, 0), rot_z=200)      # leans out, looking west
blink("Dev", 330)

# ---- S3 Aru & Bujji come up the path (f391-540) ---------------------------
shot(cam, "S3_approach", 391, 540,
     (2.5, -52, 1.6), (0.5, -20, 1.0), (2.5, -50, 1.6), (0.5, -20, 1.0), lens=35)
walk(aru, 400, 540, (0, -58), (0.4, -10.2), rot_z=180)
dog_walk(bujji, 400, 540, (0.9, -58), (1.1, -10.6), rot_z=180)
put(aru, 541, (0.4, -10.2, 0), rot_z=180)
put(bujji, 541, (1.1, -10.6, 0), rot_z=180)
blink("Aru", 470)
blink("Aru", 530)

# ---- S4 the runaway lid (f541-660) ----------------------------------------
shot(cam, "S4_lid", 541, 660,
     (2.6, -12.2, 0.45), (0.2, -6.5, 0.2), (2.4, -12.0, 0.5), (0.2, -6.7, 0.2), lens=40)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.2, -1.6, 0.04))
lid = bpy.context.active_object
lid.name = "Lid"
lid.scale = (0.5, 0.5, 0.05)
lid.data.materials.append(bpy.data.materials.new("LidWood"))
lid.data.materials[0].use_nodes = True
lid.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.34, 0.18, 1)
n = 12
for i in range(n + 1):
    t = i / n
    f = 560 + t * 50
    lid.location = (0.2 + 0.3 * t, -1.6 - 8.0 * t, 0.04 + 0.10 * math.sin(t * math.pi))
    lid.rotation_euler = (math.radians(720 * t), 0, 0.3 * t)
    lid.keyframe_insert('location', frame=int(f))
    lid.keyframe_insert('rotation_euler', frame=int(f))
head_turn(aru, 615, 0)
set_pose(aru, 630, {'spine': (25, 0, 0), 'head': (18, 0, 0)})   # looks down at the lid
blink("Aru", 590)

set_pose(aru, 661, {'spine': (0, 0, 0), 'head': (0, 0, 0)})   # stand back up
# ---- S5 feet -> tilt up: the freeze (f661-750) ----------------------------
shot(cam, "S5_freeze", 661, 750,
     (2.6, -11.8, 0.5), (0.5, -9.3, 0.3), (2.6, -11.6, 1.5), (0.5, -9.0, 1.05), lens=40)

# ---- S6 eye contact CUs (f751-870) ----------------------------------------
shot(cam, "S6_dev_cu", 751, 808, (2.6, -9.8, 1.25), (0.8, -7.7, 1.12), lens=50)
set_pose(dev, 780, {'upper_arm.R': (-95, 0, -40), 'forearm.R': (-20, 0, 0)})  # shy wave
set_pose(dev, 800, {'upper_arm.R': (-70, 0, -35)})
shot(cam, "S6_aru_cu", 809, 870, (1.4, -8.8, 1.15), (0.4, -10.2, 1.10), lens=50)
key_face("Aru", "Mouth", "Smile", 809, 0.0)
key_face("Aru", "Mouth", "Smile", 845, 0.5)
blink("Dev", 770)
blink("Aru", 830)

# ---- S7 end wide: a season arrives (f871-1050) ----------------------------
shot(cam, "S7_end", 871, 1050,
     (3.2, -13.2, 1.2), (0.6, -9.4, 0.85), (2.8, -12.6, 1.3), (0.6, -9.4, 0.85), lens=35)
wag(bujji, 880, 1050)
key_face("Aru", "Mouth", "Smile", 880, 0.5)
blink("Aru", 950)
blink("Dev", 990)

attach_sound(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "audio", "ep2_mix.wav"))

if "--qc" in sys.argv:
    qc_stills([120, 300, 480, 600, 720, 790, 840, 980], "EP2")

out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "ep02.blend"
save(out)
