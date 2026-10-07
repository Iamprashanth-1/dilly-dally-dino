"""
AMUHUDU - Episode animation toolkit
===================================
Helpers to assemble animated, render-ready episode scenes from the asset
library: linking, camera shots, walk cycles, sit poses, facial shape keys,
dog tail wag, lighting and QC stills. Imported by build_epXX.py scripts.
"""
import bpy, math, os
from mathutils import Vector
from math import radians, sin, pi

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.normpath(os.path.join(HERE, "..", "library"))
PREVIEWS = os.path.normpath(os.path.join(HERE, "..", "previews"))
FPS = 30


def fresh(name, duration_s, fps=FPS):
    bpy.ops.wm.read_homefile(use_factory_startup=True)
    sc = bpy.context.scene
    sc.name = name
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920   # 9:16 reels
    sc.render.fps = fps
    sc.frame_start = 1
    sc.frame_end = int(duration_s * fps)
    sc.render.engine = 'CYCLES'   # matches QC previews; switch to EEVEE for speed
    # punchy, vibrant look for reels
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    try:
        sc.view_settings.look = 'Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = -0.08     # richer, deeper color instead of pastel wash
    return sc


def link(filename, coll_name):
    """Append an asset collection from library/ into the episode (local copies,
    so poses, animation and shape-key keys always save with the file).
    Returns (collection, root_empty|None)."""
    with bpy.data.libraries.load(os.path.join(LIB, filename), link=False) as (df, dt):
        dt.collections = [n for n in df.collections if n == coll_name]
    coll = bpy.data.collections[coll_name]
    bpy.context.scene.collection.children.link(coll)
    roots = [o for o in coll.all_objects if o.type == 'EMPTY' and o.name.endswith('_Root')]
    return coll, (roots[0] if roots else None)


def place(root, loc=(0, 0, 0), rot_z=0.0):
    root.location = loc
    root.rotation_euler = (0, 0, radians(rot_z))


def world_light(sky=(0.72, 0.80, 0.90), strength=0.8, sun_deg=(48, 0, -35), energy=4.0,
                sun_color=(1.0, 0.88, 0.72), mist=0.0, sky_strength=0.5,
                zenith=(0.18, 0.46, 0.86), horizon=(0.88, 0.94, 0.96)):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    # stylized gradient sky: vivid zenith fading to a warm horizon
    try:
        tex = nt.nodes.new("ShaderNodeTexCoord")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        e0 = ramp.color_ramp.elements[0]
        e1 = ramp.color_ramp.elements[1]
        e0.position, e1.position = 0.18, 0.62
        e0.color = (*horizon, 1)
        e1.color = (*zenith, 1)
        nt.links.new(tex.outputs["Generated"], ramp.inputs["Fac"])
        bg.inputs[1].default_value = 1.0
        bg.inputs[1].default_value = sky_strength
        nt.links.new(ramp.outputs["Color"], bg.inputs[0])
    except Exception:
        bg.inputs[0].default_value = (*tuple(sky), 1) if isinstance(sky, (tuple, list)) else (0.72, 0.80, 0.90, 1)
        bg.inputs[1].default_value = strength
    # soft volumetric haze for depth (cheap setting)
    if mist > 0:
        try:
            vol = nt.nodes.new("ShaderNodeVolumeScatter")
            vol.inputs["Color"].default_value = (0.85, 0.92, 1.0, 1)
            vol.inputs["Density"].default_value = mist
            vol.inputs["Anisotropy"].default_value = 0.3
            nt.links.new(vol.outputs["Volume"], bg.inputs["Volume"])
        except Exception:
            pass
    L = bpy.data.lights.new("Sun", 'SUN')
    L.energy = energy
    L.angle = radians(9)          # soft shadow edges = natural daylight
    L.color = sun_color
    o = bpy.data.objects.new("Sun", L)
    bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = tuple(radians(a) for a in sun_deg)
    return o

def add_clouds(coll=None, n=6, seed=7, spread=55, height=(16, 26), size=(3.5, 6.5)):
    """Soft white blob clouds drifting high in the sky."""
    import random
    random.seed(seed)
    sc = bpy.context.scene
    cc = coll or bpy.data.collections.new("CLOUDS")
    if coll is None:
        sc.collection.children.link(cc)
    mat = bpy.data.materials.new("Cloud")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1)
    b.inputs["Roughness"].default_value = 1.0
    try:
        b.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1)
        b.inputs["Emission Strength"].default_value = 0.35
    except Exception:
        pass
    for i in range(n):
        x = random.uniform(-spread, spread)
        y = random.uniform(-spread * 0.8, spread * 0.4)
        z = random.uniform(*height)
        for j in range(3):
            r = random.uniform(*size) * (1.0 if j == 0 else 0.6)
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=r, segments=16, ring_count=10,
                location=(x + random.uniform(-r, r) * 1.6,
                          y + random.uniform(-r, r) * 0.8,
                          z + random.uniform(-r, r) * 0.25))
            c = bpy.context.active_object
            c.name = f"Cloud_{i}_{j}"
            c.scale = (1.0, 0.75, 0.45)
            _apply_scale_local(c)
            c.data.materials.append(mat)
            for col in c.users_collection:
                col.objects.unlink(c)
            cc.objects.link(c)
    return cc

def _apply_scale_local(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def add_camera(lens=35, fstop=5.6):
    c = bpy.data.cameras.new("Cam")
    c.lens = lens
    if fstop:
        c.dof.use_dof = True
        c.dof.aperture_fstop = fstop
        c.dof.aperture_blades = 6
    o = bpy.data.objects.new("Cam", c)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.scene.camera = o
    return o


def _look(cam, loc, tgt, f, lens=None):
    if lens:
        cam.data.lens = lens
        cam.data.keyframe_insert('lens', frame=f)
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if getattr(cam.data, 'dof', None) and cam.data.dof.use_dof:
        cam.data.dof.focus_distance = (Vector(tgt) - Vector(loc)).length
        cam.data.dof.keyframe_insert('focus_distance', frame=f)
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)


def shot(cam, name, f1, f2, loc1, tgt1, loc2=None, tgt2=None, lens=None):
    """Keyframe a shot: jump cut at f1 (two keys on same frame), move to loc2 by f2."""
    _look(cam, loc1, tgt1, f1, lens)
    _look(cam, loc2 if loc2 else loc1, tgt2 if tgt2 else tgt1, f2)
    bpy.context.scene.timeline_markers.new(name, frame=int(f1))
    print(f"  shot {name}: f{int(f1)}-{int(f2)}")


# ------------------------------------------------------------- characters
def rig_of(char):
    return bpy.data.objects[char + "_Rig"]


def key_face(char, part, key, f, val):
    o = bpy.data.objects.get(f"{char}_{part}")
    if o and o.data.shape_keys:
        kb = o.data.shape_keys.key_blocks.get(key)
        if kb:
            kb.value = val
            kb.keyframe_insert('value', frame=f)


def blink(char, f):
    for side in ('L', 'R'):
        key_face(char, f"Lid_{side}", "Blink", f - 5, 0.0)
        key_face(char, f"Lid_{side}", "Blink", f - 1, 1.0)
        key_face(char, f"Lid_{side}", "Blink", f + 4, 0.0)


def set_pose(rig, f, pose):
    """pose: {bone: (rx_deg, ry_deg, rz_deg[, loc_tuple])}"""
    for b, val in pose.items():
        pb = rig.pose.bones.get(b)
        if pb is None:
            continue
        if pb.rotation_mode != 'XYZ':
            pb.rotation_mode = 'XYZ'
        pb.rotation_euler = tuple(radians(a) for a in val[:3])
        pb.keyframe_insert('rotation_euler', frame=f)
        if len(val) > 3:
            pb.location = val[3]
            pb.keyframe_insert('location', frame=f)


def rest_pose(rig, f=1):
    """Key all bones to rest at frame f — prevents backward extrapolation
    of later pose keys into earlier frames."""
    for pb in rig.pose.bones:
        if pb.rotation_mode != 'XYZ':
            pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.keyframe_insert('rotation_euler', frame=f)

def put(rig, f, loc, rot_z=0.0):
    """Static placement keyframe (also used to hold a character off-stage)."""
    rig.location = loc
    rig.rotation_euler = (0, 0, radians(rot_z))
    rig.keyframe_insert('location', frame=f)
    rig.keyframe_insert('rotation_euler', frame=f)


def walk(rig, f1, f2, p1, p2, rot_z=0.0, cycle=20, amp=28):
    """Human/dog walk: steps + arm swing + body bob, linear travel p1->p2."""
    p1 = tuple(p1) + (0.0,) * (3 - len(p1))
    p2 = tuple(p2) + (0.0,) * (3 - len(p2))
    n = max(1, int(f2 - f1))
    for f in range(int(f1), int(f2) + 1):
        t = (f - f1) / n
        ph = (f - f1) / cycle * 2 * pi
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        z = p1[2] + (p2[2] - p1[2]) * t + 0.02 * abs(sin((f - f1) / cycle * 2 * pi))
        rig.location = (x, y, z)
        rig.rotation_euler = (0, 0, radians(rot_z))
        rig.keyframe_insert('location', frame=f)
        rig.keyframe_insert('rotation_euler', frame=f)
        s = sin(ph)
        set_pose(rig, f, {
            'thigh.L': (amp * s, 0, 0), 'thigh.R': (-amp * s, 0, 0),
            'shin.L': (max(0, 45 * sin(ph + 0.9)), 0, 0),
            'shin.R': (max(0, 45 * sin(ph + pi + 0.9)), 0, 0),
            'foot.L': (-15 * max(0, sin(ph + 1.8)), 0, 0),
            'foot.R': (-15 * max(0, sin(ph + pi + 1.8)), 0, 0),
            'upper_arm.L': (-18 * s, 0, 8), 'upper_arm.R': (18 * s, 0, -8),
            'forearm.L': (max(0, -20 * s), 0, 0), 'forearm.R': (max(0, 20 * s), 0, 0),
        })


def dog_walk(rig, f1, f2, p1, p2, rot_z=0.0, cycle=12, amp=30, z1=0.0, z2=0.0):
    p1 = tuple(p1) + (0.0,) * (3 - len(p1))
    p2 = tuple(p2) + (0.0,) * (3 - len(p2))
    n = max(1, int(f2 - f1))
    for f in range(int(f1), int(f2) + 1):
        t = (f - f1) / n
        ph = (f - f1) / cycle * 2 * pi
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        rig.location = (x, y, z1 + (z2 - z1) * t)
        rig.rotation_euler = (0, 0, radians(rot_z))
        rig.keyframe_insert('location', frame=f)
        rig.keyframe_insert('rotation_euler', frame=f)
        s = sin(ph)
        set_pose(rig, f, {
            'legFL': (amp * s, 0, 0), 'legFR': (-amp * s, 0, 0),
            'legBL': (-amp * s, 0, 0), 'legBR': (amp * s, 0, 0),
        })


def sit(rig, f, seat, rot_z=0.0, lean=0.0):
    """Seat a human on a bench/step. seat = (x, y, seat_top_z)."""
    rig.location = (seat[0], seat[1], seat[2] - 0.52)
    rig.rotation_euler = (0, 0, radians(rot_z))
    rig.keyframe_insert('location', frame=f)
    rig.keyframe_insert('rotation_euler', frame=f)
    set_pose(rig, f, {
        'thigh.L': (-70, 0, -6), 'thigh.R': (-70, 0, 6),
        'shin.L': (62, 0, 0), 'shin.R': (62, 0, 0),
        'foot.L': (-8, 0, 0), 'foot.R': (-8, 0, 0),
        'upper_arm.L': (4 + lean, 0, 12), 'upper_arm.R': (4 + lean, 0, -12),
        'forearm.L': (-10, 0, 0), 'forearm.R': (-10, 0, 0),
        'spine': (6 + lean, 0, 0),
    })


def wag(rig, f1, f2, amp=35, cycle=10):
    for f in range(int(f1), int(f2) + 1, 2):
        ph = (f - f1) / cycle * 2 * pi
        set_pose(rig, f, {'tail1': (0, 0, amp * sin(ph)), 'tail2': (0, 0, amp * 0.6 * sin(ph + 0.8))})


def head_turn(rig, f, deg):
    """Yaw the head left/right (head bones are vertical -> rotate about local Y)."""
    set_pose(rig, f, {'head': (0, deg, 0)})


# ------------------------------------------------------------- QC stills
def qc_stills(frames, tag, w=320, h=568):
    sc = bpy.context.scene
    saved = (sc.render.engine, sc.render.resolution_x, sc.render.resolution_y)
    sc.render.engine = 'CYCLES'
    if hasattr(sc, 'cycles'):
        sc.cycles.device = 'CPU'
        sc.cycles.samples = 24
    sc.render.resolution_x, sc.render.resolution_y = w, h
    for f in frames:
        sc.frame_set(int(f))
        sc.render.filepath = os.path.join(PREVIEWS, f"{tag}_f{int(f):04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  QC {tag} f{int(f)}")
    sc.render.engine, sc.render.resolution_x, sc.render.resolution_y = saved


def attach_sound(path, start=0.0, volume=1.0):
    """Add the mixed soundtrack as a VSE guide strip (frame 0)."""
    sc = bpy.context.scene
    if not sc.sequence_editor:
        sc.sequence_editor_create()
    strip = sc.sequence_editor.strips.new_sound(
        name=os.path.splitext(os.path.basename(path))[0],
        filepath=os.path.abspath(path),
        channel=1,
        frame_start=int(start * FPS) + 1)
    strip.volume = volume
    print(f"  soundtrack: {os.path.basename(path)}")

def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))
    print("SAVED:", path)
