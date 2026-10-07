"""
AMUHUDU - Character Builder
===========================
Builds the full cast for the "Amuhudu" Instagram reel series as rigged,
material-ready Blender characters. Run headless:

    blender.exe --background --factory-startup --python build_characters.py -- --out characters.blend

Characters (each in its own collection, facing -Y, origin at ground, meters):
  CHAR_Aru      9yo village boy (protagonist)
  CHAR_Dev      9yo boy from the city
  CHAR_Ammamma  Aru's grandmother
  CHAR_Latha    Dev's mother
  CHAR_Ravi     Dev's father
  CHAR_Bujji    the village dog

No rendering happens here (except tiny QA thumbnails when --thumbs is passed).
"""
import bpy, bmesh, math, random, argparse, sys, os
from mathutils import Vector, Matrix

random.seed(11)

# ---------------------------------------------------------------- scene reset
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                  bpy.data.objects, bpy.data.images, bpy.data.curves, bpy.data.lights, bpy.data.cameras):
        for item in list(block):
            if item.users == 0:
                block.remove(item)

# ---------------------------------------------------------------- materials
_mat_cache = {}
def M(name, color, rough=0.6, sss=0.0):
    """Principled material, cached by name."""
    if name in _mat_cache:
        return _mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if sss > 0:
        for sock in ("Subsurface Weight", "Subsurface"):
            if sock in bsdf.inputs:
                bsdf.inputs[sock].default_value = sss
                break
    _mat_cache[name] = m
    return m

# palette --------------------------------------------------------------------
SKIN  = {"Aru": (0.38, 0.20, 0.11), "Dev": (0.47, 0.27, 0.15),
         "Ammamma": (0.42, 0.23, 0.12), "Latha": (0.46, 0.25, 0.13),
         "Ravi": (0.40, 0.21, 0.11)}
HAIR  = (0.045, 0.028, 0.020)
SILVER = (0.72, 0.72, 0.70)

def set_input(bsdf, name, val):
    if name in bsdf.inputs:
        try:
            bsdf.inputs[name].default_value = val
        except Exception:
            pass

def skin_m(c):
    m = M("Skin_" + c, SKIN[c], rough=0.50, sss=0.15)
    b = m.node_tree.nodes["Principled BSDF"]
    set_input(b, "Subsurface Radius", (1.0, 0.35, 0.25))
    set_input(b, "Subsurface Scale", 0.010)
    set_input(b, "Specular IOR Level", 0.3)
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 180.0
    n1.inputs["Detail"].default_value = 4.0
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.015
    nt.links.new(tex.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def hair_m(c):
    m = M("Hair_" + c, SILVER if c == "Ammamma" else HAIR, rough=0.55)
    set_input(m.node_tree.nodes["Principled BSDF"], "Specular IOR Level", 0.2)
    return m

def hair_curve_mat(c):
    """Melanin-based material for particle hair (strand shading)."""
    name = "HairCurves_" + c
    if name in _mat_cache:
        return _mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    silver = (c == "Ammamma")
    set_input(b, "Melanin", 0.05 if silver else 0.72)
    set_input(b, "Melanin Redness", 0.45)
    set_input(b, "Roughness", 0.55)
    set_input(b, "Specular IOR Level", 0.2)
    set_input(b, "Base Color", (*(SILVER if silver else HAIR), 1.0))
    _mat_cache[name] = m
    return m

def weave_fabric(m, scale=350.0, bump=0.12, sheen=0.3):
    """Add a procedural weave bump + sheen to a cloth material."""
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    set_input(b, "Sheen Weight", sheen)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3.0
    bump_n = nt.nodes.new("ShaderNodeBump")
    bump_n.inputs["Strength"].default_value = bump
    nt.links.new(noise.outputs["Fac"], bump_n.inputs["Height"])
    nt.links.new(bump_n.outputs["Normal"], b.inputs["Normal"])
    return m
def eye_white(): return M("EyeWhite", (0.92, 0.92, 0.90), rough=0.15)
def iris_m():   return M("Iris", (0.13, 0.06, 0.03), rough=0.15)
def pupil_m():  return M("Pupil", (0.01, 0.01, 0.01), rough=0.1)
def brow_m():   return M("Brow", HAIR, rough=0.4)
def mouth_m():  return M("Mouth", (0.42, 0.18, 0.15), rough=0.4)
def cloth_m(n, c):
    return weave_fabric(M("Cloth_" + n, c, rough=0.78), scale=380.0, bump=0.12)
def shoe_m(n, c):  return weave_fabric(M("Shoe_" + n, c, rough=0.55), scale=250.0, bump=0.08, sheen=0.0)

# ---------------------------------------------------------------- mesh helpers
def _apply_scale(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def _link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj

def ball(name, r, loc, scale=(1, 1, 1), mat=None, coll=None, segs=24, rings=16, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=rings)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    _apply_scale(o)
    if smooth:
        _smooth(o)
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def box(name, size, loc, rot=(0, 0, 0), mat=None, coll=None, bevel_w=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    _apply_scale(o)
    if bevel_w > 0:
        bevel = o.modifiers.new("Bevel", 'BEVEL')
        bevel.width = bevel_w
        bevel.segments = 2
        apply_mods(o)
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def tube(name, p1, p2, r1, r2, mat=None, coll=None, segs=16, smooth=True):
    """Tapered tube between two points. p1 -> bottom radius r1, p2 -> r2."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    length = d.length
    rot = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_cone_add(vertices=segs, radius1=r1, radius2=r2,
                                    depth=1.0, location=(p1 + p2) / 2, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (1, 1, length)
    _apply_scale(o)
    if smooth:
        _smooth(o)
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def loft_limb(name, p1, p2, prof, mat, coll, segs=20, rings=22):
    """Continuous tapered limb mesh lofted along p1->p2 (no joint seams).
    prof(t) -> radius at t in [0,1]; end caps hidden inside torso/hand/shoe."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    q = d.to_track_quat('Z', 'Y').to_matrix()
    bm = bmesh.new()
    prev = first = None
    for i in range(rings + 1):
        t = i / rings
        r = prof(t)
        c = p1 + d * t
        ring = [bm.verts.new(c + q @ Vector((math.cos(2 * math.pi * j / segs) * r,
                                             math.sin(2 * math.pi * j / segs) * r, 0)))
                for j in range(segs)]
        if prev:
            for j in range(segs):
                bm.faces.new((prev[j], prev[(j + 1) % segs], ring[(j + 1) % segs], ring[j]))
        else:
            first = ring
        prev = ring
    bm.faces.new(first[::-1])
    bm.faces.new(prev)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    _link(o, coll)
    o.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    _smooth(o)
    return o

def _prof(pts, bulges=()):
    """Radius profile: piecewise-linear (t, r) control points + gaussian
    bulges (amp, at, width) for deltoid/calf shapes."""
    def f(t):
        r = pts[-1][1]
        for (t0, r0), (t1, r1) in zip(pts, pts[1:]):
            if t <= t1:
                r = r0 + (r1 - r0) * ((t - t0) / max(t1 - t0, 1e-9))
                break
        for amp, at, w in bulges:
            r += amp * math.exp(-((t - at) / w) ** 2)
        return max(r, 1e-4)
    return f

def _smooth(obj, angle_deg=50):
    """Smooth shading with an angle limit (keeps rims/caps crisp)."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(angle_deg))
    except Exception:
        bpy.ops.object.shade_smooth()

def torus(name, R, r, loc, rot=(0, 0, 0), mat=None, coll=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def apply_mods(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except RuntimeError:
            obj.modifiers.remove(mod)

def soft(obj, lvl=2):
    """Round out a shape with subdivision + smooth shading."""
    m = obj.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = m.render_levels = lvl
    apply_mods(obj)
    bpy.ops.object.shade_smooth()

def thicken(obj, t=0.012, lvl=1):
    """Give cloth real thickness (inward, so the silhouette is unchanged)."""
    s = obj.modifiers.new("Solidify", 'SOLIDIFY')
    s.thickness = t
    s.offset = -1
    if lvl > 0:
        m = obj.modifiers.new("Subsurf", 'SUBSURF')
        m.levels = m.render_levels = lvl
    apply_mods(obj)
    bpy.ops.object.shade_smooth()

def shape_offset(obj, key_name, fn):
    """Add a shape key that moves verts by fn(co)->Vector (local coords)."""
    obj.shape_key_add(name='Basis')
    key = obj.shape_key_add(name=key_name)
    key.value = 0.0   # Blender 5.x creates new keys at value 1.0 — force rest
    for v in key.data:
        v.co = v.co + fn(v.co)
    key.slider_min = -1.0
    return key

# ---------------------------------------------------------------- rig helpers
def make_armature(name, bones, coll):
    """bones: {name: (head:Vector, tail:Vector, parent:str|None)}"""
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    _link(obj, coll)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname, (head, tail, parent) in bones.items():
        eb = arm.edit_bones.new(bname)
        eb.head, eb.tail = head, tail
        eb.parent = arm.edit_bones.get(parent) if parent else None
        if parent and bname.endswith(('.L', '.R')) and parent.endswith(('.L', '.R')):
            pass
        eb.roll = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj

def bone_groups(bones):
    return list(bones.keys())

def manual_skin(obj, bone_names):
    """Fallback skinning: nearest-bone weights."""
    arm_obj = obj.parent
    arm = arm_obj.data
    bones = [arm.bones[b] for b in bone_names]
    segs = []
    mw = arm_obj.matrix_world
    for b in bones:
        h = mw @ Vector(b.head_local); t = mw @ Vector(b.tail_local)
        segs.append((b.name, h, t))
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    groups = {n: obj.vertex_groups.new(name=n) for n, _, _ in segs}
    mw_o = obj.matrix_world
    for v in obj.data.vertices:
        p = mw_o @ v.co
        best, bd = None, 1e9
        for name, h, t in segs:
            d = _pt_seg(p, h, t)
            if d < bd:
                bd, best = d, name
        groups[best].add([v.index], 1.0, 'REPLACE')

def _pt_seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length

def skin(objs, arm_obj, bone_names, coll):
    """Automatic weights with per-object fallback."""
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        arm_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        try:
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        except RuntimeError:
            o.parent = arm_obj
            manual_skin(o, bone_names)
        # ensure object stays in its own collection (parenting may keep it there)

def skin_head(obj, arm_obj):
    """Attach a small object fully to the 'head' bone."""
    grp = obj.vertex_groups.new(name='head')
    grp.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm_obj
    obj.parent = arm_obj

# ---------------------------------------------------------------- head factory
def build_head(cid, hr, head_c, skin_mat, coll, hair_style="cap", hair_mat=None, glasses=False):
    """Stylized head facing -Y. hr = head radius, head_c = head center (Vector)."""
    parts = []
    head = ball(f"{cid}_Head", hr, head_c, scale=(1.0, 0.92, 1.06), mat=skin_mat, coll=coll, segs=32, rings=20)

    # shape: round cranium, taper to a soft chin, flatten back of skull
    bm = bmesh.new(); bm.from_mesh(head.data)
    for v in bm.verts:
        z = v.co.z
        if z < 0:
            f = 1.0 + 0.13 * (z / hr)          # wide egg head, small chin
            v.co.x *= f; v.co.y *= f
            if v.co.y < -hr * 0.42 and -hr * 0.52 < z < -hr * 0.06:
                v.co.y -= 0.006                 # soft chin
        if z > hr * 0.15:                       # rounder cranium
            g = (z / hr)
            v.co.x *= 1.0 + 0.06 * g
            v.co.y *= 1.0 + 0.04 * g
        if v.co.y > hr * 0.55:                  # flatten back
            v.co.y = hr * 0.55 + (v.co.y - hr * 0.55) * 0.55
        if abs(z) < hr * 0.16 and v.co.y < -hr * 0.55:
            v.co.y -= 0.006                     # subtle muzzle plane
    bm.to_mesh(head.data); bm.free()
    soft(head, 2)
    parts.append(head)

    eye_r = hr * 0.235
    for side in ('L', 'R'):
        sx = 1 if side == 'L' else -1
        # eyeball front cap sits just proud of the face so the white reads
        # (old design was flush; smaller radius needs a touch more forward)
        E = Vector((sx * hr * 0.28, head_c.y - hr * 0.77, head_c.z + hr * 0.01))
        parts.append(ball(f"{cid}_Eye_{side}", eye_r, E, scale=(1, 0.85, 1),
                          mat=eye_white(), coll=coll, segs=26, rings=16))
        # Rain-style: big iris fills the eye opening (the "cute" signal)
        parts.append(ball(f"{cid}_Iris_{side}", eye_r * 0.62, E + Vector((0, -eye_r * 0.68, 0)),
                          scale=(1, 0.45, 1), mat=iris_m(), coll=coll, segs=20, rings=12))
        parts.append(ball(f"{cid}_Pupil_{side}", eye_r * 0.30, E + Vector((0, -eye_r * 0.86, 0)),
                          scale=(1, 0.40, 1), mat=pupil_m(), coll=coll, segs=16, rings=10))
        parts.append(ball(f"{cid}_Glint_{side}", eye_r * 0.11,
                          E + Vector((-sx * eye_r * 0.22, -eye_r * 0.88, eye_r * 0.22)),
                          mat=M("Glint", (1, 1, 1), rough=0.1), coll=coll, segs=10, rings=6))

        # upper lid: solid skin puff resting on top of the eyeball (no cut
        # shells — rims always shade badly). Blink slides it down over the eye.
        lid = ball(f"{cid}_Lid_{side}", eye_r * 0.72, E + Vector((0, -eye_r * 0.18, eye_r * 0.70)),
                   scale=(1.28, 0.85, 0.60), mat=skin_mat, coll=coll, segs=22, rings=12)
        shape_offset(lid, "Blink", lambda c, e=eye_r: Vector((0, -e * 0.10, -e * 1.15)))
        parts.append(lid)

        # brow: thick, low, hugging the lid puff (Rain-style)
        br = ball(f"{cid}_Brow_{side}", hr * 0.105,
                  (sx * hr * 0.28, head_c.y - hr * 0.87, head_c.z + hr * 0.245),
                  scale=(1.7, 0.30, 0.30), mat=brow_m(), coll=coll, segs=14, rings=8)
        br.rotation_euler = (0, sx * 0.14, sx * 0.10)
        _apply_scale(br)
        shape_offset(br, "Brow.Raise", lambda c: Vector((0, 0, hr * 0.08)))
        parts.append(br)

    nose = ball(f"{cid}_Nose", hr * 0.075, (0, head_c.y - hr * 0.90, head_c.z - hr * 0.18),
                scale=(0.85, 1.0, 0.85), mat=skin_mat, coll=coll, segs=16, rings=10)
    soft(nose, 1)
    parts.append(nose)

    mouth = ball(f"{cid}_Mouth", hr * 0.085, (0, head_c.y - hr * 0.88, head_c.z - hr * 0.58),
                 scale=(1.35, 0.24, 0.24), mat=mouth_m(), coll=coll, segs=18, rings=10)
    soft(mouth, 1)
    w = hr * 0.12
    bm2 = bmesh.new(); bm2.from_mesh(mouth.data)
    for v in bm2.verts:
        if abs(v.co.x) > w:                       # gentle rest smile baked in
            v.co.z += hr * 0.030
    bm2.to_mesh(mouth.data); bm2.free()
    w = hr * 0.12
    shape_offset(mouth, "Smile", lambda c: Vector((0.04 * hr * (1 if c.x > 0 else -1), 0.03 * hr, 0.04 * hr)) if abs(c.x) > w else Vector((0, 0, 0)))
    shape_offset(mouth, "Sad",   lambda c: Vector((0.03 * hr * (1 if c.x > 0 else -1), 0.015 * hr, -0.04 * hr)) if abs(c.x) > w else Vector((0, 0, 0)))
    shape_offset(mouth, "Open",  lambda c: Vector((0, 0, c.z * 1.4)))
    parts.append(mouth)

    for side in ('L', 'R'):
        sx = 1 if side == 'L' else -1
        ear = ball(f"{cid}_Ear_{side}", hr * 0.13, (sx * hr * 0.96, head_c.y - hr * 0.02, head_c.z),
                   scale=(0.32, 0.65, 0.95), mat=skin_mat, coll=coll)
        soft(ear, 1)
        parts.append(ear)

    hm = hair_mat or hair_m(cid)
    parts += build_hair(cid, hr, head_c, hm, coll, hair_style, skin_mat)

    if glasses:
        for side in ('L', 'R'):
            sx = 1 if side == 'L' else -1
            E = Vector((sx * hr * 0.28, head_c.y - hr * 1.00, head_c.z + hr * 0.01))
            t = torus(f"{cid}_Spec_{side}", hr * 0.19, hr * 0.016, E, rot=(math.pi / 2, 0, 0),
                      mat=M("SpecFrame", (0.08, 0.08, 0.08), rough=0.3), coll=coll)
            t.scale = (1, 1, 0.9); _apply_scale(t)
            parts.append(t)
            # temple bar from the rim back to the ear
            parts.append(box(f"{cid}_SpecArm_{side}", (hr * 0.60, hr * 0.016, hr * 0.014),
                             (sx * hr * 0.62, head_c.y - hr * 0.55, head_c.z + hr * 0.06),
                             mat=M("SpecFrame", (0.08, 0.08, 0.08), rough=0.3), coll=coll))
        parts.append(box(f"{cid}_SpecBridge", (hr * 0.24, hr * 0.015, hr * 0.014),
                         (0, head_c.y - hr * 1.00, head_c.z + hr * 0.08), mat=M("SpecFrame", (0.08, 0.08, 0.08), rough=0.3), coll=coll))

    return parts

def scalp_emitter(cid, hr, head_c, coll, skin_mat, hair_mat):
    """Scalp shell (skin, slot 0) that hair strands (hair mat, slot 1) grow from."""
    e = ball(f"{cid}_Scalp", hr * 0.97, head_c, scale=(0.99, 0.90, 1.00),
             mat=skin_mat, coll=coll, segs=24, rings=16)
    e.data.materials.append(hair_mat)
    bm = bmesh.new(); bm.from_mesh(e.data)
    # hair grows along vertex normals — keep only the top dome so strands
    # never stick out sideways around the ears
    kill = [v for v in bm.verts if v.co.z < hr * 0.48]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(e.data); bm.free()
    # density gradient: hair thins out toward the hairline and above the ears
    bm = bmesh.new(); bm.from_mesh(e.data)
    dens, lens = {}, {}
    for v in bm.verts:
        t = max(0.0, min(1.0, (v.co.z / hr - 0.48) / 0.45))   # 0 at rim, 1 on top
        dens[v.index] = t
        lens[v.index] = 0.45 + 0.55 * t                       # shorter strands near the rim
    bm.to_mesh(e.data); bm.free()
    vg = e.vertex_groups.new(name="density")
    vg2 = e.vertex_groups.new(name="lengthv")
    for i in dens:
        vg.add([i], dens[i], 'REPLACE')
        vg2.add([i], lens[i], 'REPLACE')
    return e

def add_hair(cid, emitter, count=900, length=0.045, curl=False):
    ps = emitter.modifiers.new(f"{cid}_Hair", 'PARTICLE_SYSTEM')
    st = ps.particle_system.settings
    st.type = 'HAIR'
    st.use_advanced_hair = True
    st.count = count
    st.hair_length = length
    st.hair_step = 4
    st.radius_scale = 0.004
    st.root_radius = 1.0
    st.tip_radius = 0.25
    st.child_type = 'INTERPOLATED'
    st.child_percent = 4
    st.rendered_child_count = 26
    st.child_radius = 0.014
    st.material = 2
    if curl:
        st.kink = 'CURL'
        st.kink_amplitude = 0.02
        st.kink_frequency = 4.0
        st.kink_shape = 0.2
    ps.particle_system.vertex_group_density = "density"
    ps.particle_system.vertex_group_length = "lengthv"
    # (the scalp shell stays visible as a hair-coloured base under the strands)
    return emitter

def build_hair(cid, hr, head_c, hm, coll, style, skin_mat=None):
    """Mesh hair for the silhouette + short particle strands for detail."""
    parts = []
    # --- mesh base (silhouette) ---
    if style in ("cap", "curls", "bun", "long", "short"):
        cap = ball(f"{cid}_HairCap", hr * 1.07, head_c, scale=(1.02, 0.98, 1.05), mat=hm, coll=coll, segs=28, rings=18)
        bm = bmesh.new(); bm.from_mesh(cap.data)
        kill = [v for v in bm.verts
                if v.co.z < hr * 0.10 or (v.co.y < -hr * 0.30 and v.co.z < hr * 0.70)]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(cap.data); bm.free()
        sm = cap.modifiers.new("Subsurf", 'SUBSURF'); sm.levels = sm.render_levels = 1
        solid = cap.modifiers.new("Solidify", 'SOLIDIFY'); solid.thickness = hr * 0.14; solid.offset = -1.0
        apply_mods(cap)
        parts.append(cap)

        if style == "curls":
            for i in range(55):
                th = random.uniform(0, 2 * math.pi)
                ph = random.uniform(0.22, 1.18)
                p = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
                if p.y < -0.25 and p.z < 0.55:
                    continue
                loc = head_c + Vector((p.x * hr * 1.05, p.y * hr * 0.96, p.z * hr * 1.08))
                curl = ball(f"{cid}_Curl_{i:02d}", random.uniform(hr * 0.13, hr * 0.21), loc,
                            mat=hm, coll=coll, segs=14, rings=10)
                soft(curl, 1)
                parts.append(curl)
        elif style == "bun":
            parts.append(ball(f"{cid}_Bun", hr * 0.42, head_c + Vector((0, hr * 0.72, hr * 0.62)),
                              mat=hm, coll=coll))
        elif style == "long":
            parts.append(ball(f"{cid}_HairBack", hr * 0.62, head_c + Vector((0, hr * 0.55, -hr * 1.15)),
                              scale=(1.15, 0.75, 1.8), mat=hm, coll=coll))
            for side in ('L', 'R'):
                sx = 1 if side == 'L' else -1
                strand = ball(f"{cid}_Strand_{side}", hr * 0.22,
                              head_c + Vector((sx * hr * 0.82, hr * 0.30, -hr * 1.25)),
                              scale=(0.55, 0.6, 3.4), mat=hm, coll=coll)
                soft(strand, 1)
                parts.append(strand)
        if style in ("cap", "short"):
            parts.append(ball(f"{cid}_Quiff", hr * 0.22,
                              head_c + Vector((0, -hr * 0.52, hr * 0.74)),
                              scale=(1.25, 0.65, 0.5), mat=hm, coll=coll, segs=14, rings=8))

    # --- particle strands (real-hair detail over the mesh base) ---
    emitter = scalp_emitter(cid, hr, head_c, coll, skin_mat or hm, hair_curve_mat(cid))
    parts.append(emitter)
    lengths = {"curls": 0.024, "cap": 0.02, "bun": 0.011, "long": 0.026, "short": 0.011}
    add_hair(cid, emitter, count=1500, length=lengths.get(style, 0.02), curl=(style == "curls"))
    return parts

    return parts

# ---------------------------------------------------------------- human bodies
CHILD = dict(hr=0.155, head_c=Vector((0, 0, 1.095)),
             chest=Vector((0, 0, 0.755)), pelvis=Vector((0, 0, 0.545)),
             shoulder=Vector((0.138, 0, 0.895)), elbow=Vector((0.205, -0.022, 0.695)),
             wrist=Vector((0.232, 0.015, 0.515)), hand=Vector((0.248, 0.020, 0.455)),
             hip=Vector((0.075, 0, 0.505)), knee=Vector((0.085, 0.016, 0.30)),
             ankle=Vector((0.085, -0.010, 0.065)), toe=Vector((0.085, -0.125, 0.028)),
             neck_top=Vector((0, 0, 0.985)))
WF = dict(hr=0.125, head_c=Vector((0, 0, 1.42)),     # adult female (bigger stylized head ~5.5 heads tall)
          chest=Vector((0, 0, 1.035)), pelvis=Vector((0, 0, 0.825)),
          shoulder=Vector((0.115, 0, 1.175)), elbow=Vector((0.190, -0.018, 0.975)),
          wrist=Vector((0.218, 0.014, 0.795)), hand=Vector((0.234, 0.018, 0.745)),
          hip=Vector((0.075, 0, 0.79)), knee=Vector((0.080, 0.014, 0.46)),
          ankle=Vector((0.080, -0.008, 0.07)), toe=Vector((0.080, -0.11, 0.026)),
          neck_top=Vector((0, 0, 1.28)))
WM = dict(hr=0.122, head_c=Vector((0, 0, 1.53)),     # adult male
          chest=Vector((0, 0, 1.135)), pelvis=Vector((0, 0, 0.905)),
          shoulder=Vector((0.128, 0, 1.275)), elbow=Vector((0.208, -0.020, 1.065)),
          wrist=Vector((0.236, 0.014, 0.875)), hand=Vector((0.254, 0.018, 0.823)),
          hip=Vector((0.080, 0, 0.865)), knee=Vector((0.085, 0.015, 0.50)),
          ankle=Vector((0.085, -0.008, 0.07)), toe=Vector((0.085, -0.115, 0.026)),
          neck_top=Vector((0, 0, 1.39)))

def human_bones(P):
    c, pv, s, e, w, hp, k, a, t = (P['chest'], P['pelvis'], P['shoulder'], P['elbow'],
                                   P['wrist'], P['hip'], P['knee'], P['ankle'], P['toe'])
    nz, hc = P['neck_top'].z, P['head_c'].z
    B = {
        'hips':   (pv + Vector((0, 0, -0.07)), Vector((0, 0, (pv.z + c.z) / 2)), None),
        'spine':  (Vector((0, 0, (pv.z + c.z) / 2)), c, 'hips'),
        'chest':  (c, Vector((0, 0, c.z + 0.11)), 'spine'),
        'neck':   (Vector((0, 0, c.z + 0.11)), Vector((0, 0, nz)), 'chest'),
        'head':   (Vector((0, 0, nz)), Vector((0, 0, hc + P['hr'] * 1.25)), 'neck'),
    }
    for side, sx in (('L', 1), ('R', -1)):
        B[f'shoulder.{side}'] = (Vector((sx * 0.025, 0, c.z + 0.10)), Vector((sx * s.x, s.y, s.z)), 'chest')
        B[f'upper_arm.{side}'] = (Vector((sx * s.x, s.y, s.z)), Vector((sx * e.x, e.y, e.z)), f'shoulder.{side}')
        B[f'forearm.{side}'] = (Vector((sx * e.x, e.y, e.z)), Vector((sx * w.x, w.y, w.z)), f'upper_arm.{side}')
        B[f'hand.{side}'] = (Vector((sx * w.x, w.y, w.z)), Vector((sx * w.x + sx * 0.02, w.y - 0.03, w.z - 0.06)), f'forearm.{side}')
        B[f'thigh.{side}'] = (Vector((sx * hp.x, hp.y, hp.z)), Vector((sx * k.x, k.y, k.z)), 'hips')
        B[f'shin.{side}'] = (Vector((sx * k.x, k.y, k.z)), Vector((sx * a.x, a.y, a.z)), f'thigh.{side}')
        B[f'foot.{side}'] = (Vector((sx * a.x, a.y, a.z)), Vector((sx * t.x, t.y, t.z + 0.01)), f'shin.{side}')
    return B

def limb_bulge(obj, p1, p2, bulge=0.15, at=0.5, width=0.35):
    """Shape a tapered tube with a natural muscle/calf bulge."""
    p1, p2 = Vector(p1), Vector(p2)
    ax = p2 - p1
    L = max(ax.length, 1e-6)
    ax.normalize()
    bm = bmesh.new(); bm.from_mesh(obj.data)
    for v in bm.verts:
        rel = v.co - p1
        along = rel.dot(ax)
        u = max(0.0, min(1.0, along / L))
        rad = rel - ax * along
        f = 1.0 + bulge * math.exp(-((u - at) / width) ** 2)
        v.co = p1 + ax * along + rad * f
    bm.to_mesh(obj.data); bm.free()

def join_objs(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def build_hand(cid, side, W, E, hr, k, mat, coll):
    """Clean stylized hand: palm + rounded finger block + thumb, one mesh.
    W = wrist pos, E = elbow pos."""
    sx = 1 if side == 'L' else -1
    W, E = Vector(W), Vector(E)
    parts = []
    parts.append(ball(f"{cid}_Palm_{side}", 0.042 * k, (W.x + sx * 0.004 * k, W.y + 0.010 * k, W.z - 0.040 * k),
                      scale=(0.60, 0.46, 0.92), mat=mat, coll=coll, segs=18, rings=12))
    parts.append(box(f"{cid}_Fingers_{side}", (0.052 * k, 0.038 * k, 0.060 * k),
                     (W.x + sx * 0.004 * k, W.y - 0.004 * k, W.z - 0.082 * k),
                     mat=mat, coll=coll, bevel_w=0.016 * k))
    parts.append(tube(f"{cid}_Thumb_{side}",
                      (W.x + sx * 0.026 * k, W.y + 0.014 * k, W.z - 0.026 * k),
                      (W.x + sx * 0.036 * k, W.y + 0.020 * k, W.z - 0.058 * k),
                      0.0135 * k, 0.0095 * k, mat=mat, coll=coll, segs=10))
    hand = join_objs(parts, f"{cid}_Hand_{side}")
    _smooth(hand, 40)
    return hand

def build_shoe(cid, side, A, hr, k, mat, coll):
    """Shaped shoe: rounded body + toe cap + sole, one joined mesh.
    A = ankle position, toe points -Y."""
    A = Vector(A)
    parts = []
    parts.append(box(f"{cid}_ShoeBody_{side}", (0.088 * k, 0.205 * k, 0.075 * k),
                     (A.x, A.y - 0.045 * k, 0.058 * k), mat=mat, coll=coll, bevel_w=0.026 * k))
    parts.append(ball(f"{cid}_Toe_{side}", 0.042 * k, (A.x, A.y - 0.125 * k, 0.038 * k),
                      scale=(0.95, 0.75, 0.62), mat=mat, coll=coll, segs=16, rings=10))
    parts.append(box(f"{cid}_Sole_{side}", (0.095 * k, 0.225 * k, 0.016 * k),
                     (A.x, A.y - 0.05 * k, 0.012 * k), mat=mat, coll=coll, bevel_w=0.008 * k))
    shoe = join_objs(parts, f"{cid}_Shoe_{side}")
    soft(shoe, 1)
    return shoe

def _body_core(cid, P, skin_mat, coll):
    """torso, neck+traps, bulged limbs, real hands (skin)."""
    hr, c, pv = P['hr'], P['chest'], P['pelvis']
    s, e, w, hd = P['shoulder'], P['elbow'], P['wrist'], P['hand']
    hp, k_, a, t = P['hip'], P['knee'], P['ankle'], P['toe']
    k = P['head_c'].z / 1.095          # body scale factor for hands
    parts = []
    chest = ball(f"{cid}_Chest", hr * 0.94, c, scale=(0.83, 0.54, 0.72), mat=skin_mat, coll=coll)
    soft(chest, 2)
    parts.append(chest)
    pelvis = ball(f"{cid}_Pelvis", hr * 0.95, pv, scale=(0.80, 0.58, 0.46), mat=skin_mat, coll=coll)
    soft(pelvis, 2)
    parts.append(pelvis)
    parts.append(tube(f"{cid}_Neck", (0, 0, c.z + 0.085), (0, 0, P['head_c'].z - hr * 0.72),
                      hr * 0.36, hr * 0.40, mat=skin_mat, coll=coll))

    for side, sx in (('L', 1), ('R', -1)):
        S, E, Wv = (Vector((sx * s.x, s.y, s.z)), Vector((sx * e.x, e.y, e.z)),
                    Vector((sx * w.x, w.y, w.z)))
        # one continuous arm: deltoid -> elbow -> wrist, no joint balls.
        # starts tucked down/in so the deltoid cap hides inside the shirt
        A0 = Vector((sx * s.x * 0.72, s.y, s.z - 0.05))
        ua = loft_limb(f"{cid}_UpperArm_{side}", A0, Wv,
                       _prof([(0, hr * 0.28), (0.30, hr * 0.185), (0.52, hr * 0.170),
                              (0.78, hr * 0.142), (1.0, hr * 0.122)],
                             bulges=((hr * 0.040, 0.46, 0.15), (hr * 0.035, 0.10, 0.20))),
                       skin_mat, coll)
        parts.append(ua)
        parts.append(build_hand(cid, side, Wv, E, hr, k, skin_mat, coll))
        H, K = Vector((sx * hp.x, hp.y, hp.z)), Vector((sx * k_.x, k_.y, k_.z))
        Av = Vector((sx * a.x, a.y, a.z))
        # one continuous leg: thigh -> knee -> calf -> ankle
        th = loft_limb(f"{cid}_Thigh_{side}", H, Av,
                       _prof([(0, hr * 0.325), (0.28, hr * 0.245), (0.50, hr * 0.198),
                              (0.70, hr * 0.200), (0.88, hr * 0.150), (1.0, hr * 0.122)],
                             bulges=((hr * 0.032, 0.65, 0.15),)),
                       skin_mat, coll)
        parts.append(th)
    return parts

def _shoes(cid, P, mat, coll):
    k = P['head_c'].z / 1.095
    parts = []
    for side, sx in (('L', 1), ('R', -1)):
        parts.append(build_shoe(cid, side, (sx * P['ankle'].x, P['ankle'].y, P['ankle'].z),
                                P['hr'], k, mat, coll))
    return parts

def build_child(cid, coll, shirt_c, short_c, shoe_c, hair_style):
    P = CHILD
    sk = skin_m(cid)
    body = _body_core(cid, P, sk, coll)
    hr = P['hr']
    # t-shirt (high top covers the shoulder joints; hem overlaps the shorts)
    body.append(tube(f"{cid}_TShirt", (0, 0, P['pelvis'].z - 0.03), (0, 0, P['chest'].z + hr * 1.30),
                     hr * 1.02, hr * 1.00, mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.72, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.55), 0, s.z + (e.z - s.z) * 0.55))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x * 0.62, s.y, s.z - 0.02), p2, hr * 0.30, hr * 0.27,
                         mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    # shorts
    body.append(tube(f"{cid}_Shorts", (0, 0, P['pelvis'].z - 0.10), (0, 0, P['pelvis'].z + 0.10),
                     hr * 0.98, hr * 0.95, mat=cloth_m(cid + "_shorts", short_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.78, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        hp = P['hip']
        body.append(tube(f"{cid}_ShortLeg_{side}", (sx * hp.x, hp.y, P['pelvis'].z - 0.12),
                         (sx * hp.x, hp.y, P['pelvis'].z - 0.26), hr * 0.44, hr * 0.38,
                         mat=cloth_m(cid + "_shorts", short_c), coll=coll))
    body += _shoes(cid, P, shoe_m(cid + "_shoe", shoe_c), coll)
    for o in body:
        if any(k in o.name for k in ("TShirt", "Sleeve", "Shorts", "ShortLeg", "Skirt",
                                     "Blouse", "Shirt", "Pants", "PantLeg", "Shawl")):
            thicken(o, 0.012, lvl=0)
    face = build_head(cid, hr, P['head_c'], sk, coll, hair_style=hair_style)
    return body, face, human_bones(P)

def build_woman(cid, coll, saree_c, blouse_c, shoe_c, hair_style, glasses=False, shawl_c=None):
    P = WF
    sk = skin_m(cid)
    body = _body_core(cid, P, sk, coll)
    hr = P['hr']
    body.append(tube(f"{cid}_Skirt", (0, 0, 0.075), (0, 0, P['pelvis'].z + 0.06),
                     hr * 1.55, hr * 1.08, mat=cloth_m(cid + "_saree", saree_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.8, 1); _apply_scale(body[-1])
    # woven gold border along the saree hem
    gold = M("Gold", (0.80, 0.62, 0.26), rough=0.35)
    set_input(gold.node_tree.nodes["Principled BSDF"], "Metallic", 1.0)
    body.append(tube(f"{cid}_SareeBorder", (0, 0, 0.075), (0, 0, 0.17),
                     hr * 1.58, hr * 1.50, mat=gold, coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.8, 1); _apply_scale(body[-1])
    body.append(tube(f"{cid}_Blouse", (0, 0, P['pelvis'].z + 0.05), (0, 0, P['chest'].z + hr * 1.62),
                     hr * 1.12, hr * 1.28, mat=cloth_m(cid + "_blouse", blouse_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.72, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.55), 0, s.z + (e.z - s.z) * 0.55))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x * 0.62, s.y, s.z - 0.02), p2, hr * 0.33, hr * 0.30,
                         mat=cloth_m(cid + "_blouse", blouse_c), coll=coll))
    if shawl_c is not None:
        midv = (P['shoulder'] + P['hip']) / 2
        dx, dz = P['hip'].x - P['shoulder'].x, P['hip'].z - P['shoulder'].z
        theta = math.atan2(-dx, -dz) + math.pi
        body.append(box(f"{cid}_Shawl", (hr * 0.75, hr * 0.20, hr * 3.6),
                        (midv.x * 0.9, 0.055, midv.z), rot=(0, theta, 0),
                        mat=cloth_m(cid + "_shawl", shawl_c), coll=coll, bevel_w=hr * 0.10))
    body += _shoes(cid, P, shoe_m(cid + "_shoe", shoe_c), coll)
    for o in body:
        if any(k in o.name for k in ("TShirt", "Sleeve", "Shorts", "ShortLeg", "Skirt",
                                     "Blouse", "Shirt", "Pants", "PantLeg", "Shawl")):
            thicken(o, 0.012, lvl=0)
    face = build_head(cid, hr, P['head_c'], sk, coll, hair_style=hair_style, glasses=glasses)
    return body, face, human_bones(P)

def build_man(cid, coll, shirt_c, pants_c, shoe_c, hair_style):
    P = WM
    sk = skin_m(cid)
    body = _body_core(cid, P, sk, coll)
    hr = P['hr']
    body.append(tube(f"{cid}_Shirt", (0, 0, P['pelvis'].z - 0.02), (0, 0, P['chest'].z + hr * 1.62),
                     hr * 1.18, hr * 1.30, mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.74, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.85), 0, s.z + (e.z - s.z) * 0.85))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x * 0.62, s.y, s.z - 0.02), p2, hr * 0.31, hr * 0.27,
                         mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    body.append(tube(f"{cid}_Pants", (0, 0, P['pelvis'].z - 0.12), (0, 0, P['pelvis'].z + 0.10),
                     hr * 1.18, hr * 1.00, mat=cloth_m(cid + "_pants", pants_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.78, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        hp, a = P['hip'], P['ankle']
        body.append(tube(f"{cid}_PantLeg_{side}", (sx * hp.x, hp.y, P['pelvis'].z + 0.02),
                         (sx * hp.x, hp.y, a.z + 0.02), hr * 0.52, hr * 0.34,
                         mat=cloth_m(cid + "_pants", pants_c), coll=coll))
    body += _shoes(cid, P, shoe_m(cid + "_shoe", shoe_c), coll)
    for o in body:
        if any(k in o.name for k in ("TShirt", "Sleeve", "Shorts", "ShortLeg", "Skirt",
                                     "Blouse", "Shirt", "Pants", "PantLeg", "Shawl")):
            thicken(o, 0.012, lvl=0)
    face = build_head(cid, hr, P['head_c'], sk, coll, hair_style=hair_style)
    return body, face, human_bones(P)

# ---------------------------------------------------------------- dog
def build_dog(cid, coll, fur_c, snout_c, collar_c):
    fk = M("Fur_" + cid, fur_c, rough=0.7)
    sn = M("Snout_" + cid, snout_c, rough=0.7)
    body = []
    body.append(ball(f"{cid}_Body", 0.11, (0, 0.05, 0.30), scale=(0.85, 1.9, 0.85), mat=fk, coll=coll))
    body.append(ball(f"{cid}_Chest", 0.095, (0, -0.17, 0.30), scale=(0.9, 1.0, 0.95), mat=fk, coll=coll))
    body.append(ball(f"{cid}_Rump", 0.09, (0, 0.22, 0.30), scale=(0.95, 1.0, 1.0), mat=fk, coll=coll))
    body.append(ball(f"{cid}_Head", 0.085, (0, -0.30, 0.43), mat=fk, coll=coll))
    body.append(ball(f"{cid}_Snout", 0.048, (0, -0.395, 0.395), scale=(0.8, 1.3, 0.65), mat=sn, coll=coll))
    body.append(ball(f"{cid}_Nose", 0.016, (0, -0.455, 0.415), mat=pupil_m(), coll=coll, segs=12, rings=8))
    face = []
    for side, sx in (('L', 1), ('R', -1)):
        face.append(ball(f"{cid}_Eye_{side}", 0.018, (sx * 0.038, -0.365, 0.455),
                         scale=(1, 0.6, 1), mat=pupil_m(), coll=coll, segs=10, rings=8))
        ear = ball(f"{cid}_Ear_{side}", 0.036, (sx * 0.055, -0.27, 0.52),
                   scale=(0.45, 0.7, 1.15), mat=fk, coll=coll, segs=12, rings=8)
        ear.rotation_euler = (math.radians(-15), 0, math.radians(sx * 20))
        _apply_scale(ear)
        face.append(ear)
    for i in range(4):
        face.append(ball(f"{cid}_Paw_{i}", 0.028,
                         ((-1 if i % 2 else 1) * 0.07, -0.16 if i < 2 else 0.19, 0.035),
                         scale=(0.9, 1.25, 0.75), mat=sn, coll=coll, segs=12, rings=8))
    tail = tube(f"{cid}_Tail", (0, 0.30, 0.34), (0, 0.40, 0.50), 0.028, 0.012, mat=fk, coll=coll)
    face.append(tail)
    body.append(torus(f"{cid}_Collar", 0.075, 0.012, (0, -0.245, 0.36), rot=(math.pi / 2, 0, 0),
                      mat=M("Collar", collar_c, rough=0.5), coll=coll))
    legs = []
    for i in range(4):
        x, y = (-1 if i % 2 else 1) * 0.07, (-0.16 if i < 2 else 0.19)
        legs.append(tube(f"{cid}_Leg_{i}", (x, y, 0.26), (x, y, 0.05), 0.028, 0.022, mat=fk, coll=coll))
    bones = {
        'spine':   (Vector((0, 0.26, 0.30)), Vector((0, -0.24, 0.34)), None),
        'head':    (Vector((0, -0.24, 0.34)), Vector((0, -0.38, 0.44)), 'spine'),
        'tail1':   (Vector((0, 0.24, 0.32)), Vector((0, 0.36, 0.44)), 'spine'),
        'tail2':   (Vector((0, 0.36, 0.44)), Vector((0, 0.41, 0.52)), 'tail1'),
        'legFL':   (Vector((0.07, -0.16, 0.27)), Vector((0.07, -0.16, 0.04)), 'spine'),
        'legFR':   (Vector((-0.07, -0.16, 0.27)), Vector((-0.07, -0.16, 0.04)), 'spine'),
        'legBL':   (Vector((0.07, 0.19, 0.27)), Vector((0.07, 0.19, 0.04)), 'spine'),
        'legBR':   (Vector((-0.07, 0.19, 0.27)), Vector((-0.07, 0.19, 0.04)), 'spine'),
    }
    return body, legs, face, bones

# ---------------------------------------------------------------- assemble char
def _stance(P, kid=False):
    """Bend the rest pose into a relaxed stance by moving the JOINT POSITIONS
    that both the meshes and the bones are built from — so rest pose == natural
    stance (armature modifier is identity at rest, so bone-only edits do
    nothing to the visible mesh). Elbows forward+out, wrists relaxed, slight
    A-stance legs, gentle upper-body slouch. Episode poses compose on top."""
    P = dict(P)
    pv = Vector((0, 0, P['pelvis'].z))
    sl = 0.10 if kid else 0.07                       # upper-body slouch
    slm = Matrix.Translation(pv) @ Matrix.Rotation(sl, 4, 'X') @ Matrix.Translation(-pv)
    for k in ('chest', 'neck_top', 'head_c'):
        P[k] = slm @ Vector(P[k])
    S = slm @ Vector(P['shoulder'])

    # arm chain: out -> elbow bend -> wrist relax (kids are bouncier)
    eb = 0.34 if kid else 0.27
    m_out = Matrix.Translation(S) @ Matrix.Rotation(-0.12, 4, 'Y') @ Matrix.Translation(-S)
    E = m_out @ Vector(P['elbow'])
    W0 = m_out @ Vector(P['wrist'])
    m_el = Matrix.Translation(E) @ (Matrix.Rotation(-eb, 4, 'X') @ Matrix.Rotation(-0.05, 4, 'Y')) @ Matrix.Translation(-E)
    W = m_el @ W0
    H = m_el @ Vector(P['hand'])
    H = (Matrix.Translation(W) @ Matrix.Rotation(-0.16, 4, 'X') @ Matrix.Translation(-W)) @ H
    P['shoulder'], P['elbow'], P['wrist'], P['hand'] = S, E, W, H

    # slight A-stance: feet angle out from the hips
    hp = Vector(P['hip'])
    m_leg = Matrix.Translation(hp) @ Matrix.Rotation(-0.045, 4, 'Y') @ Matrix.Translation(-hp)
    for k in ('knee', 'ankle', 'toe'):
        P[k] = m_leg @ Vector(P[k])
    return P

CHILD = _stance(CHILD, kid=True)
WF = _stance(WF)
WM = _stance(WM)

def assemble(cid, coll, body, face, bones, kid=False):
    arm = make_armature(f"{cid}_Rig", bones, coll)
    skin(body, arm, list(bones.keys()), coll)
    # head tilt baked into the face parts (they are all bound to the head bone)
    piv = Vector(bones['head'][0])
    Rm = (Matrix.Translation(piv) @ Matrix.Rotation(0.06, 4, 'Z') @
          Matrix.Rotation(0.035, 4, 'X') @ Matrix.Translation(-piv))
    for o in face:
        o.matrix_world = Rm @ o.matrix_world
    for o in face:
        skin_head(o, arm)
    return arm

# ---------------------------------------------------------------- main build
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="characters.blend")
    ap.add_argument("--thumbs", action="store_true")
    args = ap.parse_args(argv)

    clean_scene()
    scene = bpy.context.scene

    specs = [
        ("Aru",     'child', dict(shirt_c=(0.80, 0.10, 0.06), short_c=(0.08, 0.20, 0.45),
                                  shoe_c=(0.16, 0.12, 0.09), hair_style="curls")),
        ("Dev",     'child', dict(shirt_c=(0.98, 0.72, 0.05), short_c=(0.14, 0.14, 0.15),
                                  shoe_c=(0.85, 0.85, 0.88), hair_style="cap")),
        ("Ammamma", 'woman', dict(saree_c=(0.05, 0.44, 0.44), blouse_c=(0.05, 0.44, 0.44),
                                  shoe_c=(0.28, 0.16, 0.10), hair_style="bun", glasses=True)),
        ("Latha",   'woman', dict(saree_c=(0.58, 0.08, 0.16), blouse_c=(0.58, 0.08, 0.16),
                                  shoe_c=(0.22, 0.13, 0.10), hair_style="long")),
        ("Ravi",    'man',   dict(shirt_c=(0.38, 0.68, 0.90), pants_c=(0.22, 0.22, 0.30),
                                  shoe_c=(0.13, 0.10, 0.09), hair_style="short")),
    ]

    x = -4.0
    made = {}
    for cid, kind, kw in specs:
        coll = bpy.data.collections.new(f"CHAR_{cid}")
        scene.collection.children.link(coll)
        if kind == 'child':
            body, face, bones = build_child(cid, coll, **kw)
        elif kind == 'woman':
            body, face, bones = build_woman(cid, coll, **kw)
        else:
            body, face, bones = build_man(cid, coll, **kw)
        arm = assemble(cid, coll, body, face, bones, kid=(kind == 'child'))
        # move whole character to its x slot
        arm.location.x = x
        bpy.context.view_layer.update()
        made[cid] = x
        x += 1.6

    # dog
    coll = bpy.data.collections.new("CHAR_Bujji")
    scene.collection.children.link(coll)
    body, legs, face, bones = build_dog("Bujji", coll, (0.48, 0.32, 0.16), (0.68, 0.50, 0.30), (0.55, 0.10, 0.08))
    bones_out = dict(bones)
    arm = make_armature("Bujji_Rig", bones_out, coll)
    skin(body + legs, arm, list(bones_out.keys()), coll)
    head_bones = {'head', 'tail1', 'tail2'}
    for o in face:
        bn = 'head' if not o.name.startswith("Bujji_Tail") else 'tail1'
        grp = o.vertex_groups.new(name=bn)
        grp.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
        mod = o.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
        o.parent = arm
    arm.location.x = x + 0.4
    made["Bujji"] = x + 0.4

    # preview environment (ground + light + camera) in its own collection
    penv = bpy.data.collections.new("PREVIEW_Rig")
    scene.collection.children.link(penv)
    ground = bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.001))
    g = bpy.context.active_object; g.name = "PREVIEW_Ground"
    _link(g, penv)
    g.data.materials.append(M("Ground", (0.62, 0.58, 0.52), rough=0.9))
    sun = bpy.data.lights.new("PREVIEW_Sun", 'SUN'); sun.energy = 3.5; sun.angle = 0.3
    so = bpy.data.objects.new("PREVIEW_Sun", sun); _link(so, penv)
    so.rotation_euler = (math.radians(50), 0, math.radians(-30))
    world = bpy.data.worlds.new("World"); scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.75, 0.78, 0.82, 1); bg.inputs[1].default_value = 0.7
    cam = bpy.data.cameras.new("PREVIEW_Cam"); cam.lens = 55
    co = bpy.data.objects.new("PREVIEW_Cam", cam); _link(co, penv)
    scene.camera = co

    # render settings tuned for reels (vertical) — friend can change
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.fps = 30
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
        try:
            scene.render.engine = eng; break
        except TypeError:
            continue

    heights = {"Aru": 1.25, "Dev": 1.25, "Ammamma": 1.57, "Latha": 1.57, "Ravi": 1.67, "Bujji": 0.55}
    if args.thumbs:
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 32
        scene.render.resolution_x = 320; scene.render.resolution_y = 320
        out_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "..", "previews")
        os.makedirs(out_dir, exist_ok=True)
        for cid, cx in made.items():
            h = heights[cid]
            tgt = Vector((cx, 0, h * 0.55))
            loc = Vector((cx + 0.9, -2.2, h * 0.75))
            co.location = loc
            co.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(out_dir, f"{cid}.png")
            bpy.ops.render.render(write_still=True)
        # group shot
        loc = Vector((0, -6.5, 1.4)); tgt = Vector((0, 0, 0.7))
        co.location = loc
        co.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
        scene.render.resolution_x = 960; scene.render.resolution_y = 540
        scene.render.filepath = os.path.join(out_dir, "CAST_lineup.png")
        bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
    print("SAVED:", args.out)
    print("OBJECTS:", len(bpy.data.objects))

main()
