"""
AMUHUDU - Photoreal scan characters (RenderPeople free rigged samples)
======================================================================
Replaces the procedural adults with photoreal scanned humans while keeping
full episode-pipeline compatibility. Run AFTER build_characters.py:

    blender.exe --background characters/characters.blend --python build_scans.py

Per character:
  1. import the RP rigged FBX (T-pose, cm-ish scale handled via world size)
  2. pose T -> relaxed A-pose (arms down, soft elbows) and BAKE the pose into
     the meshes (armature modifier apply) + armature_apply so rest == A-pose
  3. rebuild the armature in the Amuhudu convention (roll 0, bones named
     hips/spine/chest/neck/head, thigh/shin/foot, upper_arm/forearm/hand with
     .L/.R) from the baked joint positions -- so episode_lib set_pose/walk/sit
     angles behave exactly like on the procedural rigs
  4. re-skin the scan meshes with automatic weights, eyes/teeth/tongue/hair
     pinned fully to the head bone
  5. scale to the cast height, pack textures, save

Cast (free RenderPeople samples -- free commercial use):
  Ravi    <- rp_eric_rigged_001    (1.67 m)
  Latha   <- rp_claudia_rigged_002 (1.57 m)
  Ammamma <- rp_carla_rigged_001   (1.57 m)
Aru/Dev/Bujji stay procedural (no free kid/dog scans exist).
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "scans"))

SPECS = [
    ("Ravi",    os.path.join(SCAN_DIR, "eric",    "rp_eric_rigged_001_zup_t.fbx"),    1.67, 2.4),
    ("Latha",   os.path.join(SCAN_DIR, "claudia", "rp_claudia_rigged_002_zup_t.fbx"), 1.57, 0.8),
    ("Ammamma", os.path.join(SCAN_DIR, "carla",   "rp_carla_rigged_001_zup_t.fbx"),   1.57, -0.8),
]

# POSED scan characters (RenderPeople sells kids posed-only, no rig).
# Drop a purchased posed-kid FBX into assets/scans/<name>/ and add a line:
#   ("Aru", "assets/scans/aru/<rp_kid_file>.fbx", 1.25, -4.0),
POSED_SPECS = [
    # ("Aru",  os.path.join(SCAN_DIR, "aru", "kid1.fbx"), 1.25, -4.0),
    # ("Dev",  os.path.join(SCAN_DIR, "dev", "kid2.fbx"), 1.25, -2.4),
]

HEAD_PIN = ("eye", "teeth", "tongue", "gums", "lash", "brow", "hair")


def find_collection(name):
    return bpy.data.collections.get(name)


def purge(coll_names):
    scene = bpy.context.scene
    for cn in coll_names:
        c = bpy.data.collections.get(cn)
        if c:
            for cc in list(scene.collection.children):
                if cc.name == cn:
                    scene.collection.children.unlink(cc)
            bpy.data.collections.remove(c)
    try:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    except RuntimeError:
        pass


def import_scan(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def world_z_extent(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for o in objs:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        mw = ev.matrix_world
        zs += [(mw @ v.co).z for v in ev.to_mesh().vertices]
        ev.to_mesh_clear()
    return (min(zs), max(zs)) if zs else (0.0, 1.0)


def scale_to_height(arm, meshes, target):
    z0, z1 = world_z_extent(meshes)
    f = target / max(z1 - z0, 1e-6)
    objs = [arm] + meshes
    for o in objs:                      # unparent (keep world transform)
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in objs:
        o.scale = tuple(s * f for s in o.scale)   # multiply: FBX arm holds cm->m scale
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for o in meshes:                    # re-parent (keep world transform)
        o.parent = arm
        o.matrix_parent_inverse = arm.matrix_world.inverted()


def pose_matrix(pb):
    return pb.matrix.copy()


def tpose_to_apose(arm):
    """Arms down + soft elbows, baked: pose -> apply modifiers -> armature_apply."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
    for side, sgn in (('l', 1), ('r', -1)):
        ua = arm.pose.bones.get(f"upperarm_{side}")
        la = arm.pose.bones.get(f"lowerarm_{side}")
        if not (ua and la):
            continue
        sh = pose_matrix(ua).translation
        M_down = (Matrix.Translation(sh) @ Matrix.Rotation(sgn * math.radians(79), 4, 'Y')
                  @ Matrix.Translation(-sh))
        ua.matrix = M_down @ pose_matrix(ua)
        bpy.context.view_layer.update()
        el = pose_matrix(la).translation
        M_el = (Matrix.Translation(el) @ Matrix.Rotation(math.radians(-24), 4, 'X')
                @ Matrix.Translation(-el))
        la.matrix = M_el @ pose_matrix(la)
        hd = arm.pose.bones.get(f"hand_{side}")
        if hd:
            bpy.context.view_layer.update()
            wr = pose_matrix(hd).translation
            M_wr = (Matrix.Translation(wr) @ Matrix.Rotation(math.radians(-14), 4, 'X')
                    @ Matrix.Translation(-wr))
            hd.matrix = M_wr @ pose_matrix(hd)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if not any(mod.type == 'ARMATURE' and mod.object == arm for mod in o.modifiers):
            continue
        for mod in list(o.modifiers):
            if mod.type == 'ARMATURE' and mod.object == arm:
                bpy.ops.object.select_all(action='DESELECT')
                o.select_set(True)
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=mod.name)
                break
    bpy.context.view_layer.objects.active = arm
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
    bpy.ops.object.mode_set(mode='OBJECT')


def snapshot_joints(arm):
    """World-space joint positions from the baked rest pose."""
    mw = arm.matrix_world
    J = {}
    for pb in arm.pose.bones:
        J[pb.name] = mw @ pb.bone.head_local
        J[pb.name + "__tail"] = mw @ pb.bone.tail_local
    return J


def build_amuhudu_armature(name, J, coll):
    def v(k):
        return J[k]
    B = {
        'hips':  (v("hip") + Vector((0, 0, -0.05)), (v("hip") + v("spine_01")) / 2, None),
        'spine': ((v("hip") + v("spine_01")) / 2, v("spine_02"), 'hips'),
        'chest': (v("spine_02"), v("spine_03"), 'spine'),
        'neck':  (v("spine_03"), v("neck"), 'chest'),
        'head':  (v("neck"), v("head__tail") + (v("head__tail") - v("neck")) * 0.25, 'neck'),
    }
    for S, s in (('.L', 'l'), ('.R', 'r')):
        B[f'thigh{S}'] = (v(f"upperleg_{s}"), v(f"lowerleg_{s}"), 'hips')
        B[f'shin{S}'] = (v(f"lowerleg_{s}"), v(f"foot_{s}"), f'thigh{S}')
        B[f'foot{S}'] = (v(f"foot_{s}"), v(f"ball_{s}"), f'shin{S}')
        B[f'upper_arm{S}'] = (v(f"upperarm_{s}"), v(f"lowerarm_{s}"), 'chest')
        B[f'forearm{S}'] = (v(f"lowerarm_{s}"), v(f"hand_{s}"), f'upper_arm{S}')
        B[f'hand{S}'] = (v(f"hand_{s}"), v(f"hand_{s}__tail"), f'forearm{S}')
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    coll.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname, (head, tail, parent) in B.items():
        eb = arm.edit_bones.new(bname)
        eb.head, eb.tail = head, tail
        eb.parent = arm.edit_bones.get(parent) if parent else None
        eb.roll = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def pin_to_head(obj, arm):
    grp = obj.vertex_groups.new(name='head')
    grp.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    obj.parent = arm


def convert(spec):
    cname, fbx, target_h, slot_x = spec
    purge([f"CHAR_{cname}"])
    coll = bpy.data.collections.new(f"CHAR_{cname}")
    bpy.context.scene.collection.children.link(coll)

    objs = import_scan(fbx)
    arm = next(o for o in objs if o.type == 'ARMATURE')
    meshes = [o for o in objs if o.type == 'MESH']
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)

    scale_to_height(arm, meshes, target_h)
    tpose_to_apose(arm)
    J = snapshot_joints(arm)

    bpy.data.objects.remove(arm, do_unlink=True)
    new_arm = build_amuhudu_armature(f"{cname}_Rig", J, coll)

    for o in meshes:
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        for mod in list(o.modifiers):
            if mod.type == 'ARMATURE':
                o.modifiers.remove(mod)
        o.parent = None
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    new_arm.select_set(True)
    bpy.context.view_layer.objects.active = new_arm
    pin = [o for o in meshes if any(k in o.name.lower() for k in HEAD_PIN)]
    auto = [o for o in meshes if o not in pin]
    for o in pin:
        pin_to_head(o, new_arm)
    if auto:
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    new_arm.location.x = slot_x                     # cast lineup slot
    bpy.context.view_layer.update()
    print(f"SCAN OK: {cname} meshes={len(meshes)} (auto {len(auto)}, head-pinned {len(pin)})")
    return new_arm


def scale_meshes_to_height(meshes, target):
    z0, z1 = world_z_extent(meshes)
    f = target / max(z1 - z0, 1e-6)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.scale = tuple(s * f for s in o.scale)
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def build_kid_armature(name, H, coll):
    """Our-convention A-pose armature sized to a standing scan of height H.
    Landmark fractions follow real anatomy (from the Eric scan measurements)."""
    def P(x, z, y=0.0):
        return Vector((x * H, y * H, z * H))
    B = {
        'hips':  (P(0, .47), P(0, .56), None),
        'spine': (P(0, .56), P(0, .68), 'hips'),
        'chest': (P(0, .68), P(0, .78), 'spine'),
        'neck':  (P(0, .78), P(0, .845), 'chest'),
        'head':  (P(0, .845), P(0, 1.02), 'neck'),
    }
    for S, s in (('.L', 1), ('.R', -1)):
        B[f'thigh{S}'] = (P(.055 * s, .50), P(.06 * s, .27), 'hips')
        B[f'shin{S}'] = (P(.06 * s, .27), P(.06 * s, .045), f'thigh{S}')
        B[f'foot{S}'] = (P(.06 * s, .045), P(.06 * s, .02, -.09), f'shin{S}')
        B[f'upper_arm{S}'] = (P(.10 * s, .81), P(.155 * s, .63), 'chest')
        B[f'forearm{S}'] = (P(.155 * s, .63), P(.185 * s, .46), f'upper_arm{S}')
        B[f'hand{S}'] = (P(.185 * s, .46), P(.20 * s, .40), f'forearm{S}')
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    coll.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bname, (head, tail, parent) in B.items():
        eb = arm.edit_bones.new(bname)
        eb.head, eb.tail = head, tail
        eb.parent = arm.edit_bones.get(parent) if parent else None
        eb.roll = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def convert_posed(spec):
    """Posed-scan character (RenderPeople kids are posed-only): import, scale,
    auto-rig with our A-pose skeleton, automatic weights."""
    cname, fbx, target_h, slot_x = spec
    purge([f"CHAR_{cname}"])
    coll = bpy.data.collections.new(f"CHAR_{cname}")
    bpy.context.scene.collection.children.link(coll)
    objs = import_scan(fbx)
    meshes = [o for o in objs if o.type == 'MESH']
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    scale_meshes_to_height(meshes, target_h)
    arm = build_kid_armature(f"{cname}_Rig", target_h, coll)
    for o in meshes:
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    arm.location.x = slot_x
    bpy.context.view_layer.update()
    print(f"POSED SCAN OK: {cname} meshes={len(meshes)} height={target_h}")
    return arm


def main():
    bpy.ops.file.pack_all()
    for spec in SPECS:
        convert(spec)
    for spec in POSED_SPECS:
        convert_posed(spec)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    print("SCANS SAVED")


if __name__ == "__main__":
    main()
