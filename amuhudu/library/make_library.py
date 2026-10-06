"""
AMUHUDU - Asset Library Builder
===============================
Splits a master .blend (characters.blend or environment.blend) into one
reusable asset file per collection. Collections named CHAR_*, LOC_*, PROP_*
and PREVIEW_* are discovered automatically, marked as Blender Assets and
filed under the Amuhudu catalog (Characters / Environments / Props / Starter).

Run once per master:
    blender.exe --background characters/characters.blend --python make_library.py
    blender.exe --background environments/environment.blend --python make_library.py
"""
import bpy, os, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = bpy.data.filepath

# fixed catalog uuids so both masters merge into one catalog tree
CAT_ROOT = "8f4d2a10-5c1e-4b7a-9d3e-2a6f1c0b9e01"
CATS = {
    "CHAR":    ("Characters",   "a1c3e5f7-0b2d-4c6e-8a90-b1d2f3a4c5e6"),
    "LOC":     ("Environments", "b2d4f6a8-1c3e-5d7f-9b02-c3e4f5a6b7d8"),
    "PROP":    ("Props",        "c3e5a7b9-2d4f-6a8b-0c13-d4f5a6b7c8e9"),
    "PREVIEW": ("Starter",      "d4f6b8c0-3e5a-7b9d-1c24-e5a6b7c8d9f0"),
}
ROOT_NAME = "Amuhudu"

def catalog_file():
    lines = ["VERSION 1", ""]
    lines.append(f"{CAT_ROOT}:LOCAL::{ROOT_NAME}")
    for prefix, (path, uid) in CATS.items():
        lines.append(f"{uid}:LOCAL:{CAT_ROOT}:{ROOT_NAME}/{path}")
    with open(os.path.join(HERE, "blender_assets.cats.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")

def build_library():
    saved = []
    scene = bpy.context.scene
    top = [c.name for c in scene.collection.children]
    for coll_name in top:
        prefix = coll_name.split("_", 1)[0]
        if prefix not in CATS:
            continue
        cat_path, cat_uuid = CATS[prefix]
        filename = coll_name.split("_", 1)[1] + ".blend"

        bpy.ops.wm.open_mainfile(filepath=MASTER)
        scene = bpy.context.scene
        keep = bpy.data.collections.get(coll_name)
        if keep is None:
            print("MISSING:", coll_name); continue
        for c in list(scene.collection.children):
            if c.name != coll_name:
                scene.collection.children.unlink(c)
        try:
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        except RuntimeError:
            pass
        keep.asset_mark()
        keep.asset_data.catalog_id = cat_uuid
        keep.asset_data.description = f"{coll_name} — Amuhudu series asset ({cat_path})"
        try:
            keep.asset_generate_preview()
        except Exception as e:
            print("preview skip:", coll_name, e)
        out_path = os.path.join(HERE, filename)
        bpy.ops.wm.save_as_mainfile(filepath=out_path, compress=False)
        saved.append(filename)
        print("SAVED ASSET:", out_path)

    catalog_file()
    print("DONE:", len(saved), "assets from", os.path.basename(MASTER))

build_library()
