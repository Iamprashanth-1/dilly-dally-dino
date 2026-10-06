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
SKIN  = {"Aru": (0.42, 0.24, 0.13), "Dev": (0.52, 0.31, 0.17),
         "Ammamma": (0.46, 0.27, 0.15), "Latha": (0.50, 0.30, 0.16),
         "Ravi": (0.44, 0.25, 0.14)}
HAIR  = (0.025, 0.015, 0.012)
SILVER = (0.72, 0.72, 0.70)

def set_input(bsdf, name, val):
    if name in bsdf.inputs:
        try:
            bsdf.inputs[name].default_value = val
        except Exception:
            pass

def skin_m(c):
    m = M("Skin_" + c, SKIN[c], rough=0.42, sss=0.22)
    b = m.node_tree.nodes["Principled BSDF"]
    set_input(b, "Subsurface Radius", (1.0, 0.35, 0.25))
    set_input(b, "Subsurface Scale", 0.012)
    return m

def hair_m(c):  return M("Hair_" + c, SILVER if c == "Ammamma" else HAIR, rough=0.35)

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
    set_input(b, "Roughness", 0.35)
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
def mouth_m():  return M("Mouth", (0.28, 0.07, 0.07), rough=0.35)
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
        bpy.ops.object.shade_smooth()
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
        bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

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
            f = 1.0 + 0.32 * (z / hr)          # narrower jaw
            v.co.x *= f; v.co.y *= f
            if v.co.y < -hr * 0.42 and -hr * 0.52 < z < -hr * 0.06:
                v.co.y -= 0.014                 # chin
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

    eye_e = hr * 0.27
    for side in ('L', 'R'):
        sx = 1 if side == 'L' else -1
        E = Vector((sx * hr * 0.34, -hr * 0.78, head_c.z + hr * 0.02))
        parts.append(ball(f"{cid}_Eye_{side}", eye_e, E, scale=(1, 0.85, 1),
                          mat=eye_white(), coll=coll, segs=24, rings=14))
        parts.append(ball(f"{cid}_Iris_{side}", eye_e * 0.58, E + Vector((0, -eye_e * 0.60, 0)),
                          scale=(1, 0.5, 1), mat=iris_m(), coll=coll))
        parts.append(ball(f"{cid}_Pupil_{side}", eye_e * 0.27, E + Vector((0, -eye_e * 0.92, 0)),
                          scale=(1, 0.45, 1), mat=pupil_m(), coll=coll))
        # catchlight — the sparkle that makes eyes feel alive
        parts.append(ball(f"{cid}_Glint_{side}", eye_e * 0.14,
                          E + Vector((-sx * eye_e * 0.22, -eye_e * 1.02, eye_e * 0.22)),
                          mat=M("Glint", (1, 1, 1), rough=0.1), coll=coll, segs=10, rings=6))
        # upper lid — soft skin fold resting on the top of the eye
        lid = ball(f"{cid}_Lid_{side}", eye_e * 1.10,
                   E + Vector((0, -eye_e * 0.26, eye_e * 0.62)),
                   scale=(1.05, 0.5, 0.55), mat=skin_mat, coll=coll, segs=20, rings=10)
        bm = bmesh.new(); bm.from_mesh(lid.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-5], context='VERTS')
        bm.to_mesh(lid.data); bm.free()
        solid = lid.modifiers.new("Solidify", 'SOLIDIFY'); solid.thickness = 0.004; solid.offset = 0
        apply_mods(lid)
        shape_offset(lid, "Blink", lambda c, e=eye_e: Vector((0, 0, -e * 1.15)))
        parts.append(lid)
        # soft rounded brow
        br = ball(f"{cid}_Brow_{side}", hr * 0.13,
                  (sx * hr * 0.36, -hr * 0.88, head_c.z + hr * 0.36),
                  scale=(1.5, 0.4, 0.4), mat=brow_m(), coll=coll, segs=14, rings=8)
        br.rotation_euler = (0, sx * 0.18, 0)
        _apply_scale(br)
        shape_offset(br, "Brow.Raise", lambda c: Vector((0, 0, hr * 0.08)))
        parts.append(br)

    nose = ball(f"{cid}_Nose", hr * 0.085, (0, -hr * 0.95, head_c.z - hr * 0.20),
                scale=(0.85, 1.0, 0.85), mat=skin_mat, coll=coll, segs=16, rings=10)
    soft(nose, 1)
    parts.append(nose)

    mouth = ball(f"{cid}_Mouth", hr * 0.13, (0, -hr * 0.80, head_c.z - hr * 0.55),
                 scale=(1.15, 0.32, 0.42), mat=mouth_m(), coll=coll, segs=18, rings=10)
    soft(mouth, 1)
    w = hr * 0.12
    shape_offset(mouth, "Smile", lambda c: Vector((0.04 * hr * (1 if c.x > 0 else -1), 0.03 * hr, 0.04 * hr)) if abs(c.x) > w else Vector((0, 0, 0)))
    shape_offset(mouth, "Sad",   lambda c: Vector((0.03 * hr * (1 if c.x > 0 else -1), 0.015 * hr, -0.04 * hr)) if abs(c.x) > w else Vector((0, 0, 0)))
    shape_offset(mouth, "Open",  lambda c: Vector((0, 0, c.z * 1.4)))
    parts.append(mouth)

    for side in ('L', 'R'):
        sx = 1 if side == 'L' else -1
        ear = ball(f"{cid}_Ear_{side}", hr * 0.15, (sx * hr * 0.96, -hr * 0.02, head_c.z),
                   scale=(0.35, 0.7, 1.0), mat=skin_mat, coll=coll)
        soft(ear, 1)
        parts.append(ear)

    hm = hair_mat or hair_m(cid)
    parts += build_hair(cid, hr, head_c, hm, coll, hair_style, skin_mat)

    if glasses:
        for side in ('L', 'R'):
            sx = 1 if side == 'L' else -1
            E = Vector((sx * hr * 0.36, -hr * 0.92, head_c.z + hr * 0.02))
            t = torus(f"{cid}_Spec_{side}", hr * 0.15, hr * 0.016, E, rot=(math.pi / 2, 0, 0),
                      mat=M("SpecFrame", (0.08, 0.08, 0.08), rough=0.3), coll=coll)
            t.scale = (1, 1, 0.9); _apply_scale(t)
            parts.append(t)
        parts.append(box(f"{cid}_SpecBridge", (hr * 0.16, hr * 0.015, hr * 0.014),
                         (0, -hr * 0.94, head_c.z + hr * 0.05), mat=M("SpecFrame", (0.08, 0.08, 0.08), rough=0.3), coll=coll))

    return parts

def scalp_emitter(cid, hr, head_c, coll, skin_mat, hair_mat):
    """Scalp shell (skin, slot 0) that hair strands (hair mat, slot 1) grow from."""
    e = ball(f"{cid}_Scalp", hr * 1.0, head_c, scale=(1.01, 0.96, 1.03),
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
                if v.co.z < hr * 0.10 or (v.co.y < -hr * 0.28 and v.co.z < hr * 0.62)]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(cap.data); bm.free()
        sm = cap.modifiers.new("Subsurf", 'SUBSURF'); sm.levels = sm.render_levels = 1
        solid = cap.modifiers.new("Solidify", 'SOLIDIFY'); solid.thickness = hr * 0.14; solid.offset = -1.0
        apply_mods(cap)
        parts.append(cap)

        if style == "curls":
            for i in range(56):
                th = random.uniform(0, 2 * math.pi)
                ph = random.uniform(0.25, 1.15)
                p = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
                if p.y < -0.25 and p.z < 0.55:
                    continue
                loc = head_c + Vector((p.x * hr * 1.08, p.y * hr * 1.0, p.z * hr * 1.12))
                curl = ball(f"{cid}_Curl_{i:02d}", random.uniform(hr * 0.15, hr * 0.24), loc,
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
                              head_c + Vector((sx * hr * 0.80, hr * 0.05, -hr * 1.25)),
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
    lengths = {"curls": 0.024, "cap": 0.02, "bun": 0.016, "long": 0.026, "short": 0.015}
    add_hair(cid, emitter, count=700, length=lengths.get(style, 0.02), curl=(style == "curls"))
    return parts

    return parts

# ---------------------------------------------------------------- human bodies
CHILD = dict(hr=0.155, head_c=Vector((0, 0, 1.095)),
             chest=Vector((0, 0, 0.755)), pelvis=Vector((0, 0, 0.545)),
             shoulder=Vector((0.155, 0, 0.895)), elbow=Vector((0.215, 0, 0.695)),
             wrist=Vector((0.245, 0, 0.515)), hand=Vector((0.265, 0, 0.455)),
             hip=Vector((0.075, 0, 0.505)), knee=Vector((0.085, 0, 0.30)),
             ankle=Vector((0.085, 0, 0.065)), toe=Vector((0.085, -0.125, 0.028)),
             neck_top=Vector((0, 0, 0.985)))
WF = dict(hr=0.105, head_c=Vector((0, 0, 1.355)),     # adult female
          chest=Vector((0, 0, 1.035)), pelvis=Vector((0, 0, 0.825)),
          shoulder=Vector((0.128, 0, 1.175)), elbow=Vector((0.198, 0, 0.975)),
          wrist=Vector((0.232, 0, 0.795)), hand=Vector((0.248, 0, 0.745)),
          hip=Vector((0.075, 0, 0.79)), knee=Vector((0.080, 0, 0.46)),
          ankle=Vector((0.080, 0, 0.07)), toe=Vector((0.080, -0.11, 0.026)),
          neck_top=Vector((0, 0, 1.265)))
WM = dict(hr=0.105, head_c=Vector((0, 0, 1.475)),     # adult male
          chest=Vector((0, 0, 1.135)), pelvis=Vector((0, 0, 0.905)),
          shoulder=Vector((0.142, 0, 1.275)), elbow=Vector((0.215, 0, 1.065)),
          wrist=Vector((0.250, 0, 0.875)), hand=Vector((0.268, 0, 0.823)),
          hip=Vector((0.080, 0, 0.865)), knee=Vector((0.085, 0, 0.50)),
          ankle=Vector((0.085, 0, 0.07)), toe=Vector((0.085, -0.115, 0.026)),
          neck_top=Vector((0, 0, 1.385)))

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

def _body_core(cid, P, skin_mat, coll):
    """torso, neck, arms, legs, hands, feet (skin)."""
    hr, c, pv = P['hr'], P['chest'], P['pelvis']
    s, e, w, hd = P['shoulder'], P['elbow'], P['wrist'], P['hand']
    hp, k, a, t = P['hip'], P['knee'], P['ankle'], P['toe']
    mid = lambda A, B: tuple((A[i] + B[i]) / 2 for i in range(3))
    parts = []
    chest = ball(f"{cid}_Chest", hr * 0.98, c, scale=(0.86, 0.62, 0.82), mat=skin_mat, coll=coll)
    soft(chest, 2)
    parts.append(chest)
    pelvis = ball(f"{cid}_Pelvis", hr * 0.95, pv, scale=(0.82, 0.60, 0.62), mat=skin_mat, coll=coll)
    soft(pelvis, 2)
    parts.append(pelvis)
    parts.append(tube(f"{cid}_Neck", (0, 0, c.z + 0.10), (0, 0, P['head_c'].z - hr * 0.55), hr * 0.28, hr * 0.30, mat=skin_mat, coll=coll))
    for side, sx in (('L', 1), ('R', -1)):
        ua = tube(f"{cid}_UpperArm_{side}", (sx * s.x, s.y, s.z), (sx * e.x, e.y, e.z), hr * 0.26, hr * 0.20, mat=skin_mat, coll=coll)
        soft(ua, 2)
        parts.append(ua)
        el = ball(f"{cid}_Elbow_{side}", hr * 0.17, (sx * e.x, e.y, e.z), mat=skin_mat, coll=coll, segs=16, rings=12)
        soft(el, 1)
        parts.append(el)
        fa = tube(f"{cid}_Forearm_{side}", (sx * e.x, e.y, e.z), (sx * w.x, w.y, w.z), hr * 0.20, hr * 0.155, mat=skin_mat, coll=coll)
        soft(fa, 2)
        parts.append(fa)
        hand = ball(f"{cid}_Hand_{side}", hr * 0.19, (sx * hd.x, hd.y, hd.z),
                    scale=(0.8, 0.5, 1.15), mat=skin_mat, coll=coll, segs=16, rings=12)
        soft(hand, 1)
        parts.append(hand)
        thumb = ball(f"{cid}_Thumb_{side}", hr * 0.085,
                     (sx * hd.x - sx * hr * 0.13, hd.y - hr * 0.10, hd.z + hr * 0.04),
                     scale=(0.7, 0.7, 1.0), mat=skin_mat, coll=coll, segs=10, rings=8)
        soft(thumb, 1)
        parts.append(thumb)
        th = tube(f"{cid}_Thigh_{side}", (sx * hp.x, hp.y, hp.z), (sx * k.x, k.y, k.z), hr * 0.32, hr * 0.23, mat=skin_mat, coll=coll)
        soft(th, 2)
        parts.append(th)
        sh = tube(f"{cid}_Shin_{side}", (sx * k.x, k.y, k.z), (sx * a.x, a.y, a.z), hr * 0.22, hr * 0.145, mat=skin_mat, coll=coll)
        soft(sh, 2)
        parts.append(sh)
    return parts

def _shoes(cid, P, mat, coll):
    parts = []
    for side, sx in (('L', 1), ('R', -1)):
        a, t = P['ankle'], P['toe']
        shoe = box(f"{cid}_Shoe_{side}",
                   (P['hr'] * 0.44, abs(t.y) + P['hr'] * 0.32, P['hr'] * 0.30),
                   (sx * a.x, (a.y + t.y) / 2 + P['hr'] * 0.02, a.z * 0.45),
                   mat=mat, coll=coll, bevel_w=P['hr'] * 0.08)
        soft(shoe, 2)
        parts.append(shoe)
    return parts

def build_child(cid, coll, shirt_c, short_c, shoe_c, hair_style):
    P = CHILD
    sk = skin_m(cid)
    body = _body_core(cid, P, sk, coll)
    hr = P['hr']
    # t-shirt
    body.append(tube(f"{cid}_TShirt", (0, 0, P['pelvis'].z + 0.02), (0, 0, P['chest'].z + hr * 0.95),
                     hr * 1.02, hr * 0.95, mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.72, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.38), 0, s.z + (e.z - s.z) * 0.38))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x, s.y, s.z), p2, hr * 0.30, hr * 0.27,
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
    body.append(tube(f"{cid}_Blouse", (0, 0, P['pelvis'].z + 0.05), (0, 0, P['chest'].z + hr * 1.0),
                     hr * 1.12, hr * 1.04, mat=cloth_m(cid + "_blouse", blouse_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.72, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.5), 0, s.z + (e.z - s.z) * 0.5))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x, s.y, s.z), p2, hr * 0.34, hr * 0.30,
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
    body.append(tube(f"{cid}_Shirt", (0, 0, P['pelvis'].z - 0.02), (0, 0, P['chest'].z + hr * 0.95),
                     hr * 1.18, hr * 1.05, mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.74, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        s, e = P['shoulder'], P['elbow']
        p2 = Vector((sx * (s.x + (e.x - s.x) * 0.85), 0, s.z + (e.z - s.z) * 0.85))
        body.append(tube(f"{cid}_Sleeve_{side}", (sx * s.x, s.y, s.z), p2, hr * 0.32, hr * 0.27,
                         mat=cloth_m(cid + "_shirt", shirt_c), coll=coll))
    body.append(tube(f"{cid}_Pants", (0, 0, P['pelvis'].z - 0.12), (0, 0, P['pelvis'].z + 0.10),
                     hr * 1.08, hr * 1.02, mat=cloth_m(cid + "_pants", pants_c), coll=coll))
    bpy.context.view_layer.objects.active = body[-1]
    body[-1].scale = (1, 0.78, 1); _apply_scale(body[-1])
    for side, sx in (('L', 1), ('R', -1)):
        hp, a = P['hip'], P['ankle']
        body.append(tube(f"{cid}_PantLeg_{side}", (sx * hp.x, hp.y, P['pelvis'].z - 0.14),
                         (sx * hp.x, hp.y, a.z + 0.02), hr * 0.48, hr * 0.34,
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
def assemble(cid, coll, body, face, bones):
    arm = make_armature(f"{cid}_Rig", bones, coll)
    skin(body, arm, list(bones.keys()), coll)
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
                                  shoe_c=(0.28, 0.16, 0.10), hair_style="bun", glasses=True,
                                  shawl_c=(0.62, 0.08, 0.10))),
        ("Latha",   'woman', dict(saree_c=(0.58, 0.08, 0.16), blouse_c=(0.58, 0.08, 0.16),
                                  shoe_c=(0.22, 0.13, 0.10), hair_style="long", shawl_c=(0.92, 0.66, 0.08))),
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
        arm = assemble(cid, coll, body, face, bones)
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

    heights = {"Aru": 1.25, "Dev": 1.25, "Ammamma": 1.50, "Latha": 1.50, "Ravi": 1.62, "Bujji": 0.55}
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
