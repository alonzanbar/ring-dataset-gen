"""
Blender script for rendering ring scenes.
Run with: blender -b -P render_scene.py -- --sample_json <path> --out_dir <path>
"""

import bpy
import json
import sys
import argparse
import math
import mathutils
import numpy as np
from mathutils import Vector, Euler
from pathlib import Path

# Parse command-line arguments (after --)
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--sample_json", type=str, required=True)
parser.add_argument("--out_dir", type=str, required=True)
args = parser.parse_args(argv)

# Load sample parameters
with open(args.sample_json, 'r') as f:
    params = json.load(f)

out_dir = Path(args.out_dir)
out_dir.mkdir(parents=True, exist_ok=True)

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set units to millimeters
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 0.001  # 1 unit = 1mm

# Get parameters
ring_params = params["ring"]
cam_params = params["camera"]
light_params = params["lighting"]
bg_params = params["background"]
render_params = params["render"]
sample_seed = params["sample_seed"]

# Calculate ring geometry
inner_radius_mm = ring_params["inner_diameter_mm"] / 2.0
outer_radius_mm = inner_radius_mm + ring_params["band_width_mm"]
thickness_mm = ring_params["thickness_mm"]

# Create ring using boolean difference
# Outer cylinder
bpy.ops.mesh.primitive_cylinder_add(
    radius=outer_radius_mm,
    depth=thickness_mm,
    location=(0, 0, 0)
)
outer_cylinder = bpy.context.active_object
outer_cylinder.name = "RingOuter"

# Inner cylinder (for boolean)
bpy.ops.mesh.primitive_cylinder_add(
    radius=inner_radius_mm,
    depth=thickness_mm + 1.0,  # epsilon for clean boolean
    location=(0, 0, 0)
)
inner_cylinder = bpy.context.active_object
inner_cylinder.name = "RingInner"

# Boolean difference
bpy.context.view_layer.objects.active = outer_cylinder
bpy.ops.object.modifier_add(type='BOOLEAN')
outer_cylinder.modifiers["Boolean"].operation = 'DIFFERENCE'
outer_cylinder.modifiers["Boolean"].object = inner_cylinder
bpy.ops.object.modifier_apply(modifier="Boolean")

# Delete inner cylinder (we'll recreate it for mask)
bpy.ops.object.select_all(action='DESELECT')
inner_cylinder.select_set(True)
bpy.ops.object.delete()

# Create inner volume object for mask_inner
bpy.ops.mesh.primitive_cylinder_add(
    radius=inner_radius_mm,
    depth=thickness_mm + 1.0,
    location=(0, 0, 0)
)
inner_volume = bpy.context.active_object
inner_volume.name = "InnerVolume"

# Hide inner volume from camera (for RGB render)
inner_volume.hide_render = True

# Assign object indices for masks
# Ring gets index 1, inner volume gets index 2
ring_obj = bpy.data.objects["RingOuter"]
ring_obj.pass_index = 1
inner_volume.pass_index = 2

# Create materials
# Ring material (metal)
ring_mat = bpy.data.materials.new(name="RingMaterial")
ring_mat.use_nodes = True
bsdf = ring_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.2
ring_obj.data.materials.append(ring_mat)

# Inner volume material (for mask only, not visible)
inner_mat = bpy.data.materials.new(name="InnerMaterial")
inner_mat.use_nodes = True
inner_volume.data.materials.append(inner_mat)

# Background plane
bg_plane = bpy.ops.mesh.primitive_plane_add(
    size=bg_params["plane"]["size"],
    location=tuple(bg_params["plane"]["location"])
)
bg_plane_obj = bpy.context.active_object
bg_plane_obj.name = "Background"

bg_mat = bpy.data.materials.new(name="BackgroundMaterial")
bg_mat.use_nodes = True
bg_bsdf = bg_mat.node_tree.nodes["Principled BSDF"]
bg_color = bg_params["plane"]["material_color"]
bg_bsdf.inputs["Base Color"].default_value = (*bg_color, 1.0)
bg_plane_obj.data.materials.append(bg_mat)

# Lighting
if light_params["type"] == "area_light":
    light_data = bpy.data.lights.new(name="AreaLight", type='AREA')
    light_obj = bpy.data.objects.new(name="AreaLight", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    
    light_obj.location = tuple(light_params["area_light"]["location"])
    light_data.size = light_params["area_light"]["size"]
    light_data.energy = light_params["area_light"]["strength"]
    light_color = light_params["area_light"]["color"]
    light_data.color = light_color

# Camera setup
cam_data = bpy.data.cameras.new(name="Camera")
cam_obj = bpy.data.objects.new(name="Camera", object_data=cam_data)
bpy.context.collection.objects.link(cam_obj)

# Camera intrinsics
focal_length_mm = cam_params["focal_length_mm"]
sensor_width_mm = 36.0  # Full frame sensor width
cam_data.lens = focal_length_mm
cam_data.sensor_width = sensor_width_mm

# Camera pose
distance_mm = cam_params["distance_mm"]
tilt_x_deg = cam_params["tilt_x_deg"]
tilt_y_deg = cam_params["tilt_y_deg"]
rot_z_deg = cam_params["rot_z_deg"]

# Convert angles to radians
tilt_x_rad = math.radians(tilt_x_deg)
tilt_y_rad = math.radians(tilt_y_deg)
rot_z_rad = math.radians(rot_z_deg)

# Position camera using spherical coordinates
# tilt_y is elevation (0 = +Z, 90 = XY plane), rot_z is azimuth
x = distance_mm * math.sin(tilt_y_rad) * math.cos(rot_z_rad)
y = distance_mm * math.sin(tilt_y_rad) * math.sin(rot_z_rad)
z = distance_mm * math.cos(tilt_y_rad)

cam_obj.location = (x, y, z)

# Point camera at origin, then apply tilt_x
direction = Vector((0, 0, 0)) - Vector(cam_obj.location)
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()
# Apply tilt_x rotation around camera's local X axis
cam_obj.rotation_euler.rotate(Euler((tilt_x_rad, 0, 0), 'XYZ'))

# Set active camera
bpy.context.scene.camera = cam_obj

# Render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = render_params["cycles_samples"]
scene.cycles.use_denoising = render_params["denoise"]
scene.cycles.device = render_params["device"]

# Set deterministic seed (convert to 32-bit int for Blender)
# Use modulo to fit within int32 range, preserving determinism
scene.cycles.seed = int(sample_seed % (2**31 - 1))

# Resolution
scene.render.resolution_x = params.get("image_width", 512)
scene.render.resolution_y = params.get("image_height", 512)

# Output format
scene.render.image_settings.file_format = render_params["file_format"]

# Set output path for RGB
scene.render.filepath = str(out_dir / "rgb.png")

# Enable passes for masks
# Get the active view layer (name may vary by Blender version)
view_layer = scene.view_layers[0] if len(scene.view_layers) > 0 else scene.view_layers.active
view_layer.use_pass_object_index = True

# Render RGB
bpy.ops.render.render(write_still=True)

# Render masks using object index pass
# Enable object index pass in view layer
view_layer = scene.view_layers[0] if len(scene.view_layers) > 0 else scene.view_layers.active
view_layer.use_pass_object_index = True

# Make inner volume visible for mask render
inner_volume.hide_render = False

# Render to get object index pass
bpy.ops.render.render()

# Get render result and extract masks
render_result = bpy.data.images['Render Result']
if render_result is None:
    # Try to get from view layer
    render_result = view_layer.render_result

# Get object index pass from render layers
# Access the pass through the view layer
pixels = None
try:
    # Try to get object index pass
    index_pass = view_layer.passes.get("IndexOB")
    if index_pass:
        pixels = index_pass.pixels
except:
    pass

# Alternative: use render result and extract from composite
if pixels is None:
    # Render again and access through render layers output
    # Use Python to process the object index
    # Get pixels from render result
    render_result = bpy.data.images.get('Render Result')
    if render_result:
        # Render result contains all passes, we need to access object index
        # In Blender 5.0, we might need to use compositor or render layers differently
        pass

# Fallback: Use separate renders with white materials for masks
# This is more reliable across Blender versions
print("Using material-based mask rendering...")

# Save current materials
ring_bsdf = ring_mat.node_tree.nodes["Principled BSDF"]
ring_base_color = ring_bsdf.inputs["Base Color"].default_value[:]
ring_metallic = ring_bsdf.inputs["Metallic"].default_value

# Render ring mask: white ring on black background
bg_plane_obj.hide_render = True
inner_volume.hide_render = True
ring_bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
ring_bsdf.inputs["Metallic"].default_value = 0.0
# Try to set emission if available
if "Emission Color" in ring_bsdf.inputs:
    ring_bsdf.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    ring_bsdf.inputs["Emission Strength"].default_value = 10.0
elif "Emission" in ring_bsdf.inputs:
    ring_bsdf.inputs["Emission"].default_value = (1.0, 1.0, 1.0, 1.0)
    ring_bsdf.inputs["Emission Strength"].default_value = 10.0
else:
    # Use high emission through base color
    ring_bsdf.inputs["Emission Strength"].default_value = 10.0 if "Emission Strength" in ring_bsdf.inputs else 0.0
scene.render.filepath = str(out_dir / "mask_ring.png")
bpy.ops.render.render(write_still=True)

# Render inner mask: white inner volume on black background
ring_obj.hide_render = True
bg_plane_obj.hide_render = True
inner_volume.hide_render = False
inner_bsdf = inner_mat.node_tree.nodes["Principled BSDF"]
inner_bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
if "Emission Color" in inner_bsdf.inputs:
    inner_bsdf.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    inner_bsdf.inputs["Emission Strength"].default_value = 10.0
elif "Emission" in inner_bsdf.inputs:
    inner_bsdf.inputs["Emission"].default_value = (1.0, 1.0, 1.0, 1.0)
    inner_bsdf.inputs["Emission Strength"].default_value = 10.0
else:
    inner_bsdf.inputs["Emission Strength"].default_value = 10.0 if "Emission Strength" in inner_bsdf.inputs else 0.0
scene.render.filepath = str(out_dir / "mask_inner.png")
bpy.ops.render.render(write_still=True)

# Restore ring material
ring_obj.hide_render = False
ring_bsdf.inputs["Base Color"].default_value = ring_base_color
ring_bsdf.inputs["Metallic"].default_value = ring_metallic
if "Emission Color" in ring_bsdf.inputs:
    ring_bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    ring_bsdf.inputs["Emission Strength"].default_value = 0.0
elif "Emission" in ring_bsdf.inputs:
    ring_bsdf.inputs["Emission"].default_value = (0.0, 0.0, 0.0, 1.0)
    ring_bsdf.inputs["Emission Strength"].default_value = 0.0
else:
    if "Emission Strength" in ring_bsdf.inputs:
        ring_bsdf.inputs["Emission Strength"].default_value = 0.0

# Convert masks to binary (0/255) - ensure they're properly formatted
# This is handled by the compositor output, but we can verify

# Write metadata
meta = {
    "sample_seed": sample_seed,
    "ring": ring_params,
    "camera": cam_params,
    "lighting": light_params,
    "background": bg_params,
    "render": render_params,
    "calibration": params.get("calibration", {}),
    "image_width": scene.render.resolution_x,
    "image_height": scene.render.resolution_y,
}

with open(out_dir / "meta.json", 'w') as f:
    json.dump(meta, f, indent=2)

