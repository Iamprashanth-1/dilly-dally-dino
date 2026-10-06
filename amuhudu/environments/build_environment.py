"""
AMUHUDU - Environment Blockout Builder
======================================
Builds the four series locations plus reusable story props as simple,
low-poly blockouts (cheap to render on a laptop):

  LOC_Hilltop    Aru's hilltop point (bench, tree, valley backdrop)
  LOC_Chowk      Village square (banyan, teashop, bus stop, houses)
  LOC_DevHouse   The new family's house (porch, compound wall, jeep)
  LOC_Path       Winding stone path between village and Dev's house
  PROP_RedBall, PROP_SevenStones, PROP_Bench, PROP_Jeep, PROP_PaperBoat

Run:
    blender.exe --background --factory-startup --python build_environment.py -- --out environment.blend --thumbs
"""
import bpy, bmesh, math, os, argparse, sys
from mathutils import Vector

# ---------------------------------------------------------------- helpers
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects,
                  bpy.data.lights, bpy.data.cameras, bpy.data.curves):
        for item in list(block):
            if item.users == 0:
                block.remove(item)

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

_mat_cache = {}
def M(name, color, rough=0.8):
    if name in _mat_cache:
        return _mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    _mat_cache[name] = m
    return m

GRASS   = lambda: mottle(M("Grass", (0.24, 0.48, 0.10), 0.9),
                         (0.16, 0.36, 0.07), (0.34, 0.58, 0.15), scale=0.32, bump=0.4)
GRASS2  = lambda: mottle(M("Grass_Dark", (0.14, 0.36, 0.08), 0.9),
                         (0.10, 0.28, 0.06), (0.22, 0.46, 0.12), scale=0.5, bump=0.4)
DIRT    = lambda: mottle(M("Dirt", (0.50, 0.32, 0.15), 0.95),
                         (0.38, 0.24, 0.11), (0.58, 0.40, 0.20), scale=0.9, bump=0.35)
STONE   = lambda: mottle(M("Stone", (0.62, 0.58, 0.52), 0.85),
                         (0.52, 0.48, 0.42), (0.70, 0.66, 0.60), scale=2.5, bump=0.3)
STONE2  = lambda: mottle(M("Stone_Dark", (0.44, 0.41, 0.37), 0.9),
                         (0.36, 0.33, 0.30), (0.52, 0.49, 0.44), scale=2.5, bump=0.3)
WOOD    = lambda: mottle(M("Wood", (0.44, 0.26, 0.10), 0.8),
                         (0.36, 0.20, 0.08), (0.52, 0.32, 0.14), scale=6.0, bump=0.25)
WOOD_L  = lambda: mottle(M("Wood_Light", (0.68, 0.46, 0.20), 0.8),
                         (0.58, 0.38, 0.15), (0.76, 0.54, 0.26), scale=6.0, bump=0.25)
LEAF    = lambda: mottle(M("Leaf", (0.16, 0.48, 0.08), 0.85),
                         (0.10, 0.38, 0.05), (0.24, 0.58, 0.12), scale=3.0, bump=0.45)
LEAF2   = lambda: mottle(M("Leaf_Light", (0.32, 0.60, 0.12), 0.85),
                         (0.24, 0.50, 0.09), (0.40, 0.68, 0.16), scale=3.0, bump=0.45)
TERRA   = lambda: mottle(M("Roof_Terracotta", (0.78, 0.26, 0.10), 0.72),
                         (0.66, 0.20, 0.07), (0.86, 0.34, 0.14), scale=8.0, bump=0.2)
CREAM   = lambda: mottle(M("Wall_Cream", (0.96, 0.87, 0.64), 0.85),
                         (0.88, 0.78, 0.55), (0.99, 0.92, 0.72), scale=1.8, bump=0.18)
BLUE_W  = lambda: mottle(M("Wall_Blue", (0.36, 0.70, 0.74), 0.85),
                         (0.28, 0.60, 0.64), (0.44, 0.78, 0.82), scale=1.8, bump=0.18)
MIST    = lambda: mottle(M("Hill_Mist", (0.24, 0.60, 0.50), 0.9),
                         (0.20, 0.52, 0.42), (0.34, 0.68, 0.56), scale=0.35, bump=0.15)
METAL   = lambda: M("Metal_Dark", (0.15, 0.15, 0.17), 0.5)
KHAKI   = lambda: mottle(M("Jeep_Khaki", (0.48, 0.48, 0.24), 0.6),
                         (0.40, 0.40, 0.18), (0.56, 0.56, 0.30), scale=5.0, bump=0.1)
TIRE    = lambda: M("Tire", (0.05, 0.05, 0.05), 0.7)
RED     = lambda: M("Red_Ball", (0.82, 0.08, 0.06), 0.32)
WHITE_P = lambda: M("Paper", (0.92, 0.90, 0.84), 0.8)
GLASS_M = lambda: M("Glass_Block", (0.50, 0.76, 0.82), 0.2)
DOOR_M  = lambda: mottle(M("Door", (0.36, 0.18, 0.08), 0.7),
                         (0.30, 0.14, 0.06), (0.44, 0.24, 0.11), scale=8.0, bump=0.15)
SHUTTER = lambda: mottle(M("Shutter", (0.16, 0.44, 0.58), 0.7),
                         (0.12, 0.36, 0.48), (0.22, 0.52, 0.66), scale=6.0, bump=0.12)
FABRIC  = lambda: mottle(M("Awning", (0.80, 0.30, 0.14), 0.85),
                         (0.70, 0.24, 0.10), (0.88, 0.38, 0.18), scale=12.0, bump=0.2)

def mottle(m, col_a, col_b, scale=0.5, detail=4.0, bump=0.25):
    """Replace a flat color with natural two-tone noise variation + micro bump.
    Idempotent: materials are shared, so apply only once."""
    if m.get("mottled"):
        return m
    m["mottled"] = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = scale
    n1.inputs["Detail"].default_value = detail
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*col_a, 1)
    ramp.color_ramp.elements[1].color = (*col_b, 1)
    nt.links.new(tex.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if bump > 0:
        n2 = nt.nodes.new("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = scale * 60
        n2.inputs["Detail"].default_value = 6.0
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        nt.links.new(tex.outputs["Object"], n2.inputs["Vector"])
        nt.links.new(n2.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

def ball(name, r, loc, scale=(1, 1, 1), mat=None, coll=None, segs=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=rings)
    o = bpy.context.active_object; o.name = name
    o.scale = scale; _apply_scale(o)
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def box(name, size, loc, rot=(0, 0, 0), mat=None, coll=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.scale = size; _apply_scale(o)
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def cyl(name, r, depth, loc, rot=(0, 0, 0), mat=None, coll=None, verts=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def cone(name, r1, r2, depth, loc, rot=(0, 0, 0), verts=16, mat=None, coll=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

def plane(name, sx, sy, loc, rot=(0, 0, 0), mat=None, coll=None):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.scale = (sx, sy, 1); _apply_scale(o)
    if mat: o.data.materials.append(mat)
    if coll: _link(o, coll)
    return o

# ---------------------------------------------------------------- shared builders
def tree(name, coll, loc, h=3.0, trunk_r=0.16, canopy=2.2, leaf=None):
    leaf = leaf or LEAF()
    cyl(f"{name}_Trunk", trunk_r, h, (loc[0], loc[1], loc[2] + h / 2), mat=WOOD(), coll=coll)
    clumps = [(0, 0, 0.75, 1.0), (0.55, 0.2, 0.45, 0.7),
              (-0.5, -0.25, 0.5, 0.75), (0.1, -0.5, 0.35, 0.6),
              (-0.3, 0.4, 0.35, 0.55), (0.45, -0.35, 0.3, 0.5)]
    for i, (dx, dy, dz, s) in enumerate(clumps):
        ball(f"{name}_Canopy_{i}", canopy * s, (loc[0] + dx * canopy, loc[1] + dy * canopy,
             loc[2] + h + dz * canopy * 0.6), mat=leaf if i % 2 == 0 else LEAF2(), coll=coll)

def bush(name, coll, loc, r=0.5, mat=None):
    ball(name, r, (loc[0], loc[1], loc[2] + r * 0.55), scale=(1.25, 1.0, 0.8),
         mat=mat or GRASS2(), coll=coll)

def bench(name, coll, loc, rot=0.0):
    """Simple wooden bench, seat faces -Y before rotation."""
    def L(x, y, z):
        return (loc[0] + x * math.cos(rot) - y * math.sin(rot),
                loc[1] + x * math.sin(rot) + y * math.cos(rot),
                loc[2] + z)
    for sx in (-0.62, 0.62):
        box(f"{name}_Leg_{sx}", (0.08, 0.42, 0.40), L(sx, 0, 0.20), rot=(0, 0, rot), mat=WOOD(), coll=coll)
    box(f"{name}_Seat", (1.5, 0.46, 0.06), L(0, 0, 0.44), rot=(0, 0, rot), mat=WOOD_L(), coll=coll)
    box(f"{name}_Back", (1.5, 0.06, 0.38), L(0, 0.24, 0.68), rot=(math.radians(-8), 0, rot), mat=WOOD_L(), coll=coll)

def house(name, coll, loc, w=5, d=4, h=2.8, wall=None, rot=0.0):
    """Simple house with pyramid roof; door on -Y face before rotation."""
    wall = wall or CREAM()
    box(f"{name}_Walls", (w, d, h), (loc[0], loc[1], loc[2] + h / 2), rot=(0, 0, rot), mat=wall, coll=coll)
    rdiag = math.sqrt((w / 2) ** 2 + (d / 2) ** 2) * 1.12
    cone(f"{name}_Roof", rdiag, 0.05, 1.3, (loc[0], loc[1], loc[2] + h + 0.6), verts=4,
         rot=(0, 0, rot), mat=TERRA(), coll=coll)
    def L(x, y, z):
        return (loc[0] + x * math.cos(rot) - y * math.sin(rot),
                loc[1] + x * math.sin(rot) + y * math.cos(rot), loc[2] + z)
    box(f"{name}_Door", (0.7, 0.06, 1.6), L(0, -d / 2 - 0.02, 0.8), rot=(0, 0, rot), mat=DOOR_M(), coll=coll)
    for i, wx in enumerate((-w * 0.3, w * 0.3)):
        box(f"{name}_Window_{i}", (0.6, 0.05, 0.6), L(wx, -d / 2 - 0.02, 1.7), rot=(0, 0, rot), mat=GLASS_M(), coll=coll)
        box(f"{name}_Shutter_{i}", (0.72, 0.04, 0.72), L(wx, -d / 2 - 0.05, 1.7), rot=(0, 0, rot), mat=SHUTTER(), coll=coll)

# ---------------------------------------------------------------- LOC_Hilltop
def mound_z(x, y):
    """Surface height of the hilltop mound."""
    d2 = (x * x + (y - 2) ** 2) / (22 * 22)
    if d2 >= 1:
        return 0.0
    return -0.55 + 22 * 0.06 * math.sqrt(1 - d2)

def build_hilltop(coll):
    plane("LOC_Hilltop_Ground", 52, 52, (0, 0, 0), mat=GRASS(), coll=coll)
    # gentle mound plateau
    ball("LOC_Hilltop_Mound", 22, (0, 2, -0.55), scale=(1, 1, 0.06), mat=GRASS(), coll=coll, segs=32, rings=20)
    # valley backdrop — misty hill layers (put camera side = -Y)
    mist_far = M("Hill_Mist_Far", (0.48, 0.74, 0.70), 0.9)
    for i, (x, y, r, sz, m) in enumerate([
            (-18, -46, 26, 0.22, MIST()), (14, -52, 32, 0.26, MIST()),
            (-44, -38, 22, 0.18, MIST()), (46, -40, 24, 0.20, MIST()),
            (0, -78, 46, 0.30, mist_far)]):
        ball(f"LOC_Hilltop_BackdropHill_{i}", r, (x, y, r * sz * 0.45), scale=(1.3, 1, sz), mat=m, coll=coll, segs=24, rings=12)
    bz = mound_z(0, -9.5)
    bench("LOC_Hilltop_Bench", coll, (0, -9.5, bz))
    tz = mound_z(3.6, 1.5)
    tree("LOC_Hilltop_Tree", coll, (3.6, 1.5, tz), h=3.4, trunk_r=0.2, canopy=2.6)
    # stone cairn + grass tufts
    cx, cy = 2.2, 3.4
    cz = mound_z(cx, cy)
    for i in range(3):
        ball(f"LOC_Hilltop_Cairn_{i}", 0.18 - i * 0.04, (cx + i * 0.05, cy, cz + 0.05 + i * 0.2),
             scale=(1, 1, 0.6), mat=STONE(), coll=coll)
    for i, (x, y) in enumerate([(-4, -5), (-6, 2), (5, -4), (6, 3), (-2, 6), (1, -7)]):
        cone(f"LOC_Hilltop_Tuft_{i}", 0.16, 0.02, 0.45, (x, y, mound_z(x, y) + 0.02), verts=6, mat=GRASS2(), coll=coll)

# ---------------------------------------------------------------- LOC_Chowk
def build_chowk(coll):
    plane("LOC_Chowk_Ground", 40, 40, (0, 0, 0), mat=GRASS(), coll=coll)
    plane("LOC_Chowk_GrassEdge", 40, 40, (0, 0, -0.01), mat=GRASS(), coll=coll)
    # dirt crossroads slightly raised
    plane("LOC_Chowk_RoadNS", 4.5, 40, (0, 0, 0.005), mat=DIRT(), coll=coll)
    plane("LOC_Chowk_RoadEW", 40, 4.5, (0, 0, 0.006), mat=DIRT(), coll=coll)

    # --- banyan tree (the hero tree)
    bx, by = -7, 1.5
    cyl("LOC_Chowk_BanyanTrunk", 0.55, 4.2, (bx, by, 2.1), mat=WOOD(), coll=coll)
    for i in range(6):
        a = i * math.pi / 3
        rx, ry = bx + 1.1 * math.cos(a), by + 1.1 * math.sin(a)
        cyl(f"LOC_Chowk_BanyanRoot_{i}", 0.09, 2.6, (rx, ry, 1.3), mat=WOOD(), coll=coll, verts=8)
    cyl("LOC_Chowk_BanyanPlatform", 2.3, 0.22, (bx, by, 0.11), mat=STONE(), coll=coll)
    for i, (dx, dy, s) in enumerate([(0, 0, 5.2), (2.6, 1.2, 3.4), (-2.4, 1.0, 3.2),
                                     (0.8, -2.2, 3.0), (-0.8, 2.4, 2.8)]):
        ball(f"LOC_Chowk_BanyanCanopy_{i}", s, (bx + dx, by + dy, 5.4 + dy * 0.2),
             scale=(1.15, 1.15, 0.75), mat=LEAF() if i % 2 else LEAF2(), coll=coll)

    # --- teashop stall
    tx, ty = 6.5, -5
    box("LOC_Chowk_TeaWalls", (4.2, 2.6, 2.3), (tx, ty, 1.15), mat=BLUE_W(), coll=coll)
    box("LOC_Chowk_TeaRoof", (4.8, 3.2, 0.12), (tx, ty, 2.42), rot=(math.radians(6), 0, 0), mat=TERRA(), coll=coll)
    box("LOC_Chowk_TeaAwning", (4.6, 1.6, 0.06), (tx, ty - 2.0, 2.15), rot=(math.radians(14), 0, 0), mat=FABRIC(), coll=coll)
    for sx in (-2.0, 2.0):
        box(f"LOC_Chowk_TeaPost_{sx}", (0.09, 0.09, 2.2), (tx + sx, ty - 2.6, 1.1), mat=WOOD(), coll=coll)
    box("LOC_Chowk_TeaCounter", (3.2, 0.5, 0.9), (tx, ty - 1.5, 0.55), mat=WOOD_L(), coll=coll)
    box("LOC_Chowk_TeaSign", (1.8, 0.08, 0.5), (tx, ty - 1.4, 2.0), mat=FABRIC(), coll=coll)
    bench("LOC_Chowk_TeaBench", coll, (tx - 0.2, ty - 4.2, 0), rot=math.pi)
    box("LOC_Chowk_TeaTable", (0.8, 0.8, 0.06), (tx - 0.2, ty - 3.0, 0.55), mat=WOOD_L(), coll=coll)
    cyl("LOC_Chowk_TeaTableLeg", 0.06, 0.55, (tx - 0.2, ty - 3.0, 0.28), mat=WOOD(), coll=coll, verts=8)

    # --- bus stop
    sx0, sy0 = -3.5, -13
    for px in (-1.4, 0, 1.4):
        box(f"LOC_Chowk_BusPost_{px}", (0.12, 0.12, 2.3), (sx0 + px, sy0, 1.15), mat=METAL(), coll=coll)
    box("LOC_Chowk_BusRoof", (3.6, 1.8, 0.1), (sx0, sy0, 2.35), rot=(math.radians(8), 0, 0), mat=METAL(), coll=coll)
    box("LOC_Chowk_BusBackWall", (3.4, 0.1, 1.1), (sx0, sy0 + 0.75, 1.75), mat=SHUTTER(), coll=coll)
    bench("LOC_Chowk_BusBench", coll, (sx0, sy0 + 0.35, 0), rot=math.pi)

    # --- houses around the square
    house("LOC_Chowk_House1", coll, (-13, 7, 0), w=5, d=4, rot=0)
    house("LOC_Chowk_House2", coll, (12.5, 7, 0), w=5.5, d=4, wall=BLUE_W(), rot=0)
    house("LOC_Chowk_House3", coll, (0, 14, 0), w=6, d=4.5, wall=BLUE_W(), rot=math.pi)
    house("LOC_Chowk_House4", coll, (-14, -6, 0), w=4.5, d=4, rot=math.pi / 2)

    # --- lamp post + well
    cyl("LOC_Chowk_LampPole", 0.07, 3.4, (2, 9, 1.7), mat=METAL(), coll=coll, verts=8)
    box("LOC_Chowk_LampHead", (0.35, 0.35, 0.3), (2, 9, 3.5), mat=METAL(), coll=coll)
    ball("LOC_Chowk_LampBulb", 0.09, (2, 9, 3.42), mat=M("Bulb", (1.0, 0.85, 0.55), 0.3), coll=coll)
    cyl("LOC_Chowk_Well", 0.85, 0.8, (-2.5, 9.5, 0.4), mat=STONE(), coll=coll)
    cyl("LOC_Chowk_WellInner", 0.65, 0.82, (-2.5, 9.5, 0.38), mat=M("WellWater", (0.10, 0.18, 0.16), 0.15), coll=coll)

# ---------------------------------------------------------------- LOC_DevHouse
def build_devhouse(coll):
    plane("LOC_DevHouse_Ground", 36, 44, (0, -4, 0), mat=GRASS(), coll=coll)
    hx, hy = 0, 2.0
    house("LOC_DevHouse_House", coll, (hx, hy, 0), w=7, d=5.5, h=3.2, wall=CREAM())
    # porch
    plane("LOC_DevHouse_Porch", 3.6, 2.0, (hx, hy - 3.6, 0.06), mat=STONE(), coll=coll)
    for px in (-1.5, 1.5):
        box(f"LOC_DevHouse_PorchPost_{px}", (0.14, 0.14, 2.6), (hx + px, hy - 4.4, 1.3), mat=WOOD_L(), coll=coll)
    box("LOC_DevHouse_PorchRoof", (3.8, 2.2, 0.1), (hx, hy - 3.8, 2.7), rot=(math.radians(7), 0, 0), mat=TERRA(), coll=coll)
    box("LOC_DevHouse_Step1", (1.6, 0.5, 0.18), (hx, hy - 3.15, 0.09), mat=STONE(), coll=coll)
    # freshly-painted compound wall + gate
    for (wx, wy, ww, wd) in [(0, -7.4, 15, 0.25), (0, 9.4, 15, 0.25),
                             (-7.4, 1, 0.25, 17), (7.4, 1, 0.25, 17)]:
        box(f"LOC_DevHouse_Wall_{wx}_{wy}", (ww, wd, 0.65), (wx, wy, 0.33), mat=M("Wall_Grey", (0.72, 0.70, 0.66), 0.85), coll=coll)
    for gx in (-1.1, 1.1):
        box(f"LOC_DevHouse_GatePost_{gx}", (0.3, 0.3, 1.1), (gx, -7.4, 0.55), mat=CREAM(), coll=coll)
    plane("LOC_DevHouse_Walkway", 1.6, 3.2, (hx, hy - 5.4, 0.02), mat=STONE(), coll=coll)
    # city luggage by the door (Ep2)
    for i, (lx, lz, s) in enumerate([(hx + 2.6, 0.25, 1.0), (hx + 3.4, 0.22, 0.85), (hx + 2.9, 0.62, 0.7)]):
        box(f"LOC_DevHouse_Luggage_{i}", (0.7 * s, 0.4 * s, 0.5 * s), (lx, hy - 3.1, lz), rot=(0, 0, 0.2 * i),
            mat=M("Luggage", (0.45, 0.32, 0.18), 0.7), coll=coll)
    bush("LOC_DevHouse_Bush1", coll, (hx - 4.2, hy - 4.6, 0), 0.55)
    bush("LOC_DevHouse_Bush2", coll, (hx + 4.8, hy - 3.2, 0), 0.45)
    tree("LOC_DevHouse_Tree", coll, (hx - 5.5, hy + 3.5, 0), h=3.2, trunk_r=0.18, canopy=2.2)

def build_jeep(name, coll, loc, rot=0.0):
    """Arrival jeep blockout, facing -X before rotation."""
    def L(x, y, z):
        return (loc[0] + x * math.cos(rot) - y * math.sin(rot),
                loc[1] + x * math.sin(rot) + y * math.cos(rot), loc[2] + z)
    box(f"{name}_Body", (3.3, 1.55, 0.85), L(0, 0, 0.72), rot=(0, 0, rot), mat=KHAKI(), coll=coll)
    box(f"{name}_Cabin", (1.7, 1.5, 0.85), L(0.55, 0, 1.55), rot=(0, 0, rot), mat=KHAKI(), coll=coll)
    box(f"{name}_Windshield", (0.06, 1.4, 0.7), L(-0.42, 0, 1.6), rot=(math.radians(-12), 0, rot), mat=GLASS_M(), coll=coll)
    box(f"{name}_Roof", (1.9, 1.6, 0.1), L(0.55, 0, 2.0), rot=(0, 0, rot), mat=METAL(), coll=coll)
    for wx in (-1.05, 1.05):
        for wy in (-0.82, 0.82):
            cyl(f"{name}_Wheel_{wx}_{wy}", 0.38, 0.24, L(wx, wy, 0.38), rot=(0, math.pi / 2, rot), mat=TIRE(), coll=coll)
    for hy in (-0.55, 0.55):
        ball(f"{name}_Headlight_{hy}", 0.09, L(-1.66, hy, 0.85), mat=M("Headlight", (0.95, 0.92, 0.75), 0.3), coll=coll)

# ---------------------------------------------------------------- LOC_Path
def build_path(coll):
    plane("LOC_Path_Ground", 18, 90, (0, 0, 0), mat=GRASS(), coll=coll)
    # terrain rise toward village end (+Y)
    ball("LOC_Path_HillEnd", 14, (0, 21, -3.2), scale=(1, 1.2, 0.42), mat=GRASS(), coll=coll, segs=24, rings=14)
    # winding stone path: slabs along a sine curve
    for i in range(19):
        y = -19 + i * 2.1
        x = 2.4 * math.sin(y / 6.5)
        cyl(f"LOC_Path_Slab_{i:02d}", 0.55 + 0.12 * math.sin(i * 2.1), 0.07,
            (x, y, 0.035), mat=STONE() if i % 2 else STONE2(), coll=coll, verts=9)
    # trees + bushes alternating
    tree("LOC_Path_Tree1", coll, (-4.5, -12, 0), h=3.6, trunk_r=0.2, canopy=2.4)
    tree("LOC_Path_Tree2", coll, (4.8, -2, 0), h=3.0, trunk_r=0.17, canopy=2.0)
    tree("LOC_Path_Tree3", coll, (-4.2, 8, 0), h=3.3, trunk_r=0.19, canopy=2.2)
    for i, (x, y, r) in enumerate([(4.6, -16, 0.5), (-4.8, -3, 0.55), (4.4, 6, 0.5),
                                   (-4.6, 14, 0.6), (4.5, 13, 0.45), (-4.4, -18, 0.5)]):
        bush(f"LOC_Path_Bush_{i}", coll, (x, y, 0), r)
    # wooden fence along +X side
    for i in range(9):
        y = -17 + i * 3.6
        x = 2.4 * math.sin(y / 6.5) + 3.4
        box(f"LOC_Path_FencePost_{i}", (0.09, 0.09, 0.85), (x, y, 0.42), mat=WOOD(), coll=coll)
    for k, dy in enumerate((-0.18, 0.18)):
        for seg in range(8):
            y1, y2 = -17 + seg * 3.6, -17 + (seg + 1) * 3.6
            x1 = 2.4 * math.sin(y1 / 6.5) + 3.4
            x2 = 2.4 * math.sin(y2 / 6.5) + 3.4
            mid = ((x1 + x2) / 2, (y1 + y2) / 2, 0.42 + (0.3 if k else 0.0) + dy)
            ang = math.atan2(y2 - y1, x2 - x1)
            box(f"LOC_Path_Rail_{k}_{seg}", (math.dist((x1, y1), (x2, y2)), 0.05, 0.09),
                mid, rot=(0, 0, ang), mat=WOOD_L(), coll=coll)
    # milestone at the bend
    box("LOC_Path_Milestone", (0.3, 0.5, 0.55), (2.4 * math.sin(2 / 6.5) - 1.4, 2, 0.27),
        rot=(0, math.radians(-6), 0.4), mat=M("Milestone", (0.78, 0.76, 0.70), 0.85), coll=coll)

# ---------------------------------------------------------------- props
def build_prop_ball(coll):
    ball("PROP_RedBall_Ball", 0.11, (0, 0, 0.11), mat=RED(), coll=coll, segs=24, rings=16)

def build_prop_sevenstones(coll):
    spots = [(-0.14, 0), (0.14, 0), (0, 0.14), (0, -0.14), (0, 0), (0, 0), (0, 0)]
    zs = [0, 0, 0, 0, 0.09, 0.09, 0.18]
    layout = [(-0.14, 0.02, 0), (0.14, 0.02, 0), (0, -0.13, 0), (0.07, 0.13, 0), (-0.07, 0.13, 0), (0, 0.02, 0.095), (0, 0.02, 0.19)]
    for i, (x, y, z) in enumerate(layout):
        ball(f"PROP_SevenStones_Stone_{i}", 0.13, (x, y, z + 0.05), scale=(1.1, 1.1, 0.4),
             mat=STONE() if i % 2 else STONE2(), coll=coll, segs=14, rings=8)

def build_prop_paperboat(coll):
    box("PROP_PaperBoat_Hull", (0.34, 0.16, 0.07), (0, 0, 0.035), mat=WHITE_P(), coll=coll)
    box("PROP_PaperBoat_Nose", (0.1, 0.16, 0.07), (-0.2, 0, 0.045), rot=(0, math.radians(20), 0), mat=WHITE_P(), coll=coll)
    cone("PROP_PaperBoat_Sail", 0.05, 0.05, 0.16, (0.02, 0, 0.12), verts=3, rot=(0, math.pi / 2, 0), mat=WHITE_P(), coll=coll)

# ---------------------------------------------------------------- assembly
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="environment.blend")
    ap.add_argument("--thumbs", action="store_true")
    args = ap.parse_args(argv)
    clean_scene()
    scene = bpy.context.scene

    builders = [
        ("LOC_Hilltop",  build_hilltop,  (0, 0)),
        ("LOC_Chowk",    build_chowk,    (70, 0)),
        ("LOC_DevHouse", build_devhouse, (140, 0)),
        ("LOC_Path",     build_path,     (210, 0)),
        ("PROP_RedBall",    build_prop_ball, (250, 6)),
        ("PROP_SevenStones", build_prop_sevenstones, (250, 0)),
        ("PROP_Bench",      lambda c: bench("PROP_Bench_Bench", c, (0, 0, 0)), (250, -6)),
        ("PROP_Jeep",       lambda c: build_jeep("PROP_Jeep_Jeep", c, (0, 0, 0)), (250, -14)),
        ("PROP_PaperBoat",  build_prop_paperboat, (250, 12)),
    ]
    roots = {}
    for coll_name, fn, (ox, oy) in builders:
        coll = bpy.data.collections.new(coll_name)
        scene.collection.children.link(coll)
        fn(coll)
        # root empty so the whole location moves as one when instanced
        root = bpy.data.objects.new(coll_name + "_Root", None)
        root.empty_display_size = 1.0
        _link(root, coll)
        root.location = (ox, oy, 0)
        for o in list(coll.objects):
            if o is root:
                continue
            # identity parent inverse: children were built around the origin,
            # so they follow the root empty into the layout cell
            o.parent = root
        roots[coll_name] = (ox, oy)

    # preview rig for QA thumbs
    penv = bpy.data.collections.new("PREVIEW_Rig")
    scene.collection.children.link(penv)
    sun = bpy.data.lights.new("PREVIEW_Sun", 'SUN'); sun.energy = 4; sun.angle = 0.35
    so = bpy.data.objects.new("PREVIEW_Sun", sun); _link(so, penv)
    so.rotation_euler = (math.radians(48), 0, math.radians(-35))
    world = bpy.data.worlds.new("World"); scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.72, 0.78, 0.85, 1); bg.inputs[1].default_value = 0.8
    cam = bpy.data.cameras.new("PREVIEW_Cam"); cam.lens = 35
    co = bpy.data.objects.new("PREVIEW_Cam", cam); _link(co, penv)
    scene.camera = co
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24

    heights = {"LOC_Hilltop": 3.0, "LOC_Chowk": 6.0, "LOC_DevHouse": 6.0, "LOC_Path": 5.0,
               "PROP_RedBall": 0.5, "PROP_SevenStones": 0.6, "PROP_Bench": 1.0,
               "PROP_Jeep": 2.4, "PROP_PaperBoat": 0.4}
    if args.thumbs:
        scene.render.resolution_x = 320; scene.render.resolution_y = 200
        out_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "..", "previews")
        os.makedirs(out_dir, exist_ok=True)
        for cname, (ox, oy) in roots.items():
            h = heights.get(cname, 2.0)
            tgt = Vector((ox, oy, h * 0.4))
            loc = Vector((ox, oy - 26, h * 2.2 + 3))
            if cname == "LOC_Hilltop":   # shoot from inland so the valley backdrop faces camera
                loc = Vector((ox, oy + 20, 9)); tgt = Vector((ox, oy - 8, 1.0))
            if cname == "LOC_Path":      # look up the slope
                loc = Vector((ox, oy - 20, 6)); tgt = Vector((ox, oy + 4, 1.5))
            if cname.startswith("PROP"):
                loc = Vector((ox, oy - 3.2, h + 0.8))
            co.location = loc
            co.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(out_dir, f"{cname}.png")
            bpy.ops.render.render(write_still=True)
        # remove QA rig before saving master
        for o in list(penv.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(penv)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
    print("SAVED:", args.out, "| OBJECTS:", len(bpy.data.objects))

main()
