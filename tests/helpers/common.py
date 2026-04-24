"""Common helpers used by all phases."""
import json
import os
from pathlib import Path


def clean_scene():
    """Completely reset Blender scene (safer than read_factory_settings — keeps addons)."""
    import bpy
    # Remove all objects
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Purge orphan data
    try:
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    except Exception:
        pass


def ensure_out_dir(iter_n, base="/opt/mywork/xps_to_mmd/out"):
    p = Path(base) / f"iter-{iter_n}"
    p.mkdir(parents=True, exist_ok=True)
    (p / "screenshots").mkdir(exist_ok=True)
    return p


def jwrite(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def mdwrite(path, text):
    Path(path).write_text(text)


def find_armature(prefer=None):
    import bpy
    if prefer and prefer in bpy.data.objects and bpy.data.objects[prefer].type == 'ARMATURE':
        return bpy.data.objects[prefer]
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if not arms:
        return None
    return arms[0]


def set_active(obj):
    import bpy
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.mode != 'OBJECT' else None
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# MMD canonical bone names. After mmd_tools convert_to_mmd_model, left/right bones
# use `.L/.R` suffix form instead of 左/右 prefix. Accept both as valid.
CORE_MMD_BONES_CORE = [
    "全ての親", "センター", "グルーブ", "腰",
    "上半身", "上半身2", "上半身3", "首", "頭", "下半身",
]
CORE_MMD_BONES_SYMMETRIC = [
    "肩", "腕", "ひじ", "手首",
    "足", "ひざ", "足首",
]


def core_mmd_bones(armature_obj=None):
    """Return flat list of core MMD bone names.
    If armature given, check both 左/右 prefix AND .L/.R suffix forms — pick whichever exists.
    """
    result = list(CORE_MMD_BONES_CORE)
    if armature_obj is None:
        # fallback: prefer .L/.R form (post-convert)
        for b in CORE_MMD_BONES_SYMMETRIC:
            result.extend([f"{b}.L", f"{b}.R"])
        return result
    bones = armature_obj.data.bones
    for b in CORE_MMD_BONES_SYMMETRIC:
        for candidate in (f"{b}.L", f"左{b}"):
            if candidate in bones:
                result.append(candidate)
                break
        for candidate in (f"{b}.R", f"右{b}"):
            if candidate in bones:
                result.append(candidate)
                break
    return result


# Legacy (kept for any caller that expects this name)
CORE_MMD_BONES = CORE_MMD_BONES_CORE + [f"{b}.L" for b in CORE_MMD_BONES_SYMMETRIC] + [f"{b}.R" for b in CORE_MMD_BONES_SYMMETRIC]
