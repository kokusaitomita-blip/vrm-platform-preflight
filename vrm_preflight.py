bl_info = {
    "name": "VRM Platform Preflight",
    "author": "Preflight Lab",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "category": "Object",
    "description": "Check an avatar against platform VRM limits (triangle-counted) before upload.",
}

import bpy
import json
import os

# cluster profile (VRM 1.0), confirmed against cluster official help (JP) on 2026-11-06.
# - Triangle counting: cluster does not publish its counting method; VRoid Hub's
#   official FAQ defines polygon counts as total triangles across primitives,
#   so this tool counts triangulated triangles.
# - Texture total pixels (12,000,000 per JP help; EN help says 12,582,912) is a
#   display-compression trigger, not an upload limit -> WARN, strict value used.
# - Total bone count 200 appears only in the EN help -> reference check (WARN).
PROFILES = {
    "CLUSTER_VRM1": {
        "label": "cluster (VRM 1.0)",
        "max_triangles": 72000,
        "max_materials": 25,
        "max_mesh_objects": 25,  # submeshes
        "max_nodes": 1000,
        "max_texture_side": 8192,
        "texture_pixel_warn": 12000000,
        "bone_reference": 200,
        "max_file_mb": 100,
        "allowed_image_formats": {"PNG", "JPEG"},
    },
}


def _evaluated_mesh(obj, depsgraph):
    ev = obj.evaluated_get(depsgraph)
    return ev.to_mesh()


def count_triangles(objects, depsgraph):
    """Return (triangle_count, polygon_count) using triangulated counting."""
    tris = 0
    polys = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = _evaluated_mesh(obj, depsgraph)
        mesh.calc_loop_triangles()
        tris += len(mesh.loop_triangles)
        polys += len(mesh.polygons)
        obj.evaluated_get(depsgraph).to_mesh_clear()
    return tris, polys


def count_bones(objects):
    return sum(len(o.data.bones) for o in objects if o.type == "ARMATURE")


def mesh_objects(objects):
    return [o for o in objects if o.type == "MESH"]


def used_materials(objects):
    mats = set()
    for obj in mesh_objects(objects):
        for slot in obj.data.materials:
            if slot is not None:
                mats.add(slot.name)
    return mats


def used_images(objects):
    images = {}
    mat_names = used_materials(objects)
    for mat in bpy.data.materials:
        if mat.name not in mat_names or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image is not None:
                images[node.image.name] = node.image
    return images


def texture_stats(objects):
    total = 0
    max_side = 0
    bad_formats = []
    for img in used_images(objects).values():
        total += img.size[0] * img.size[1]
        max_side = max(max_side, img.size[0], img.size[1])
        # Generated/packed images have no delivery format yet; only judge
        # images that come from real files.
        if img.source == "FILE":
            fmt = (img.file_format or "").upper()
            if fmt not in ("PNG", "JPEG"):
                bad_formats.append((img.name, fmt))
    return total, max_side, bad_formats


def run_checks(objects, profile, depsgraph):
    """Core check logic. Returns result dicts with PASS/FAIL/WARN/SKIP."""
    tris, polys = count_triangles(objects, depsgraph)
    bones = count_bones(objects)
    mats = used_materials(objects)
    tex_px, tex_side, bad_formats = texture_stats(objects)
    n_mesh = len(mesh_objects(objects))
    n_nodes = len(objects)

    if bpy.data.filepath and os.path.exists(bpy.data.filepath):
        file_mb = round(os.path.getsize(bpy.data.filepath) / (1024 * 1024), 2)
    else:
        file_mb = None

    results = []

    def add(cid, label, value, limit, status=None, display=None):
        if status is None:
            status = "SKIP" if value is None else ("PASS" if value <= limit else "FAIL")
        results.append({
            "id": cid, "label": label, "value": value, "limit": limit,
            "status": status, "display": str(value) if display is None else display,
        })

    add("triangles", "Triangles (triangulated count)", tris, profile["max_triangles"])
    add("polygons_info", "Polygons (Blender display count, info)", polys, 10**18)
    add("bones_ref", "Bones (reference: EN help only)", bones, profile["bone_reference"],
        status="PASS" if bones <= profile["bone_reference"] else "WARN")
    add("materials", "Materials", len(mats), profile["max_materials"])
    add("submeshes", "Mesh objects (submeshes)", n_mesh, profile["max_mesh_objects"])
    add("nodes", "Nodes (objects)", n_nodes, profile["max_nodes"])
    add("texture_side", "Texture max side (px)", tex_side, profile["max_texture_side"])
    add("texture_pixels", "Texture pixels total (compression trigger)", tex_px,
        profile["texture_pixel_warn"],
        status="PASS" if tex_px <= profile["texture_pixel_warn"] else "WARN")
    add("texture_formats", "Texture formats PNG/JPEG only", len(bad_formats), 0,
        status="PASS" if not bad_formats else "FAIL",
        display="ok" if not bad_formats else ",".join(f"{n}:{f}" for n, f in bad_formats))
    add("file_size", "File size MB (saved .blend, reference)", file_mb, profile["max_file_mb"],
        display="not saved" if file_mb is None else str(file_mb))
    return results


class OBJECT_OT_vrm_preflight(bpy.types.Operator):
    """Run platform preflight checks on all objects in the scene"""

    bl_idname = "object.vrm_preflight"
    bl_label = "Run VRM Platform Preflight"
    bl_options = {"REGISTER"}

    profile_key: bpy.props.EnumProperty(
        name="Profile",
        items=[(k, v["label"], "") for k, v in PROFILES.items()],
        default="CLUSTER_VRM1",
    )

    def execute(self, context):
        profile = PROFILES[self.profile_key]
        depsgraph = context.evaluated_depsgraph_get()
        results = run_checks(list(context.scene.objects), profile, depsgraph)
        context.scene["vrm_preflight_results"] = json.dumps(results)
        context.scene["vrm_preflight_profile"] = profile["label"]
        failed = warned = 0
        for r in results:
            print(f"[{r['status']}] {r['label']}: {r['display']} / limit {r['limit']}")
            failed += r["status"] == "FAIL"
            warned += r["status"] == "WARN"
        if failed:
            self.report({"ERROR"}, f"Preflight: {failed} FAILED, {warned} warning(s)")
        elif warned:
            self.report({"WARNING"}, f"Preflight: passed with {warned} warning(s)")
        else:
            self.report({"INFO"}, "Preflight: all checks passed")
        return {"FINISHED"}


class VIEW3D_PT_vrm_preflight(bpy.types.Panel):
    """Results panel in the 3D Viewport sidebar (N panel)."""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM Preflight"
    bl_label = "VRM Platform Preflight"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.vrm_preflight", text="Run Preflight (cluster VRM 1.0)")
        raw = context.scene.get("vrm_preflight_results")
        if not raw:
            layout.label(text="No results yet. Run the preflight.", icon="INFO")
            return
        results = json.loads(raw)
        icons = {"PASS": "CHECKMARK", "FAIL": "ERROR", "WARN": "LOOP_BACK", "SKIP": "QUESTION"}
        for r in results:
            row = layout.row()
            row.label(text=f"{r['label']}: {r['display']} / {r['limit']}",
                      icon=icons.get(r["status"], "DOT"))


_classes = (OBJECT_OT_vrm_preflight, VIEW3D_PT_vrm_preflight)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
