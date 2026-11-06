"""Automated tests for VRM Platform Preflight core logic."""
import bpy
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("vrm_preflight", os.path.join(HERE, "vrm_preflight.py"))
vp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vp)

failures = []


def check(name, cond, detail=""):
    print(f"[TEST] {name}: {'PASS' if cond else 'FAIL'} {detail}")
    if not cond:
        failures.append(name)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- Fixture 1: grid mesh 10x10 quads -> 100 polys, 200 triangles
bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10)
grid = bpy.context.active_object

# --- Fixture 2: single quad plane -> 1 poly, 2 triangles
bpy.ops.mesh.primitive_plane_add()
plane = bpy.context.active_object

# --- Fixture 3: armature with exactly 3 bones
arm_data = bpy.data.armatures.new("Arm")
arm_obj = bpy.data.objects.new("Arm", arm_data)
scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode="EDIT")
for i in range(3):
    bone = arm_data.edit_bones.new(f"Bone{i}")
    bone.head = (0, 0, i * 0.5)
    bone.tail = (0, 0, i * 0.5 + 0.4)
bpy.ops.object.mode_set(mode="OBJECT")

# --- Fixture 4: two materials; one carries a 1024x512 image texture
mat_a = bpy.data.materials.new("MatA")
mat_a.use_nodes = True
img = bpy.data.images.new("tex_a", width=1024, height=512)
tex_node = mat_a.node_tree.nodes.new("ShaderNodeTexImage")
tex_node.image = img
mat_b = bpy.data.materials.new("MatB")
grid.data.materials.append(mat_a)
plane.data.materials.append(mat_b)

objects = list(scene.objects)
depsgraph = bpy.context.evaluated_depsgraph_get()
profile = vp.PROFILES["CLUSTER_VRM1"]
results = {r["id"]: r for r in vp.run_checks(objects, profile, depsgraph)}

check("triangles_triangulated", results["triangles"]["value"] == 202, f"got {results['triangles']['value']}")
check("polygons_display_count", results["polygons_info"]["value"] == 101, f"got {results['polygons_info']['value']}")
check("triangles_exceed_polygons", results["triangles"]["value"] > results["polygons_info"]["value"],
      "the counting gap this product exists to surface")
check("bones", results["bones_ref"]["value"] == 3, f"got {results['bones_ref']['value']}")
check("materials", results["materials"]["value"] == 2, f"got {results['materials']['value']}")
check("texture_pixels", results["texture_pixels"]["value"] == 1024 * 512, f"got {results['texture_pixels']['value']}")
check("submeshes", results["submeshes"]["value"] == 2, f"got {results['submeshes']['value']}")
check("nodes", results["nodes"]["value"] == 3, f"got {results['nodes']['value']}")
check("texture_side", results["texture_side"]["value"] == 1024, f"got {results['texture_side']['value']}")
check("texture_formats_pass", results["texture_formats"]["status"] == "PASS")
check("default_profile_no_fail",
      all(r["status"] in ("PASS", "SKIP") for r in results.values()))

# --- Tight profile: limits below fixture values must FAIL/WARN on the right checks
tight = dict(profile, max_triangles=100, max_materials=1, max_mesh_objects=1,
             max_nodes=2, max_texture_side=512, texture_pixel_warn=1000, bone_reference=2)
results2 = {r["id"]: r for r in vp.run_checks(objects, tight, depsgraph)}
check("tight_triangles_fail", results2["triangles"]["status"] == "FAIL")
check("tight_bones_warn", results2["bones_ref"]["status"] == "WARN")
check("tight_materials_fail", results2["materials"]["status"] == "FAIL")
check("tight_submeshes_fail", results2["submeshes"]["status"] == "FAIL")
check("tight_nodes_fail", results2["nodes"]["status"] == "FAIL")
check("tight_texture_side_fail", results2["texture_side"]["status"] == "FAIL")
check("tight_texture_pixels_warn", results2["texture_pixels"]["status"] == "WARN")

# --- Operator path also works (registers classes on the module)
vp.register()
res = bpy.ops.object.vrm_preflight()
check("operator_runs", "FINISHED" in res)
import json as _json
stored = _json.loads(bpy.context.scene.get("vrm_preflight_results", "[]"))
check("results_stored_for_panel", len(stored) == 10, f"entries={len(stored)}")
check("panel_registered", hasattr(bpy.types, "VIEW3D_PT_vrm_preflight"))
vp.unregister()

print("[TEST] SUMMARY:", "ALL PASSED" if not failures else f"FAILURES: {failures}")
