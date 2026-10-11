# Scène de test : un nœud torique doré brillant sur un socle, rendu Cycles (CPU).
# Usage : blender -b --factory-startup -P scene.py
import bpy
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rendu.png")

# Repartir d'une scène vide
bpy.ops.wm.read_factory_settings(use_empty=True)

# Nœud torique (trèfle, p=2 q=3) : courbe fermée avec bevel pour l'épaisseur
R, r, p, q, N = 1.2, 0.28, 2, 3, 300
curve_data = bpy.data.curves.new("NoeudCourbe", type="CURVE")
curve_data.dimensions = "3D"
curve_data.resolution_u = 16
curve_data.bevel_depth = r
curve_data.bevel_resolution = 12
curve_data.use_fill_caps = True
spline = curve_data.splines.new("POLY")
spline.points.add(N - 1)
for i in range(N):
    t = 2 * math.pi * i / N
    rho = R + 0.5 * math.cos(q * t)
    x = rho * math.cos(p * t)
    y = rho * math.sin(p * t)
    z = 0.5 * math.sin(q * t)
    spline.points[i].co = (x, y, z, 1)
spline.use_cyclic_u = True
knot = bpy.data.objects.new("Noeud", curve_data)
bpy.context.collection.objects.link(knot)
knot.location = (0, 0, 1.2)
bpy.context.view_layer.objects.active = knot
knot.select_set(True)

mat_or = bpy.data.materials.new("Or")
mat_or.use_nodes = True
bsdf = mat_or.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (1.0, 0.72, 0.28, 1.0)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.18
knot.data.materials.append(mat_or)

# Socle arrondi sombre
bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=0.25, location=(0, 0, 0.125))
socle = bpy.context.active_object
socle.name = "Socle"
bpy.ops.object.shade_smooth()
mat_socle = bpy.data.materials.new("Socle")
mat_socle.use_nodes = True
b2 = mat_socle.node_tree.nodes["Principled BSDF"]
b2.inputs["Base Color"].default_value = (0.012, 0.014, 0.025, 1.0)
b2.inputs["Roughness"].default_value = 0.22
socle.data.materials.append(mat_socle)

# Lumières : clé chaude + contre-jour bleuté
bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
key = bpy.context.active_object
key.data.energy = 900
key.data.size = 3
key.data.color = (1.0, 0.9, 0.8)
key.rotation_euler = (math.radians(55), 0, math.radians(45))

bpy.ops.object.light_add(type="AREA", location=(-3, 3, 2.5))
rim = bpy.context.active_object
rim.data.energy = 400
rim.data.size = 2
rim.data.color = (0.5, 0.7, 1.0)
rim.rotation_euler = (math.radians(70), 0, math.radians(-135))

# Caméra
bpy.ops.object.camera_add(location=(6.5, -6.5, 4.2))
cam = bpy.context.active_object
# Viser le centre du nœud
from mathutils import Vector
cible = Vector((0, 0, 1.4))
cam.rotation_euler = (cible - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam

# Fond sombre dégradé (world)
world = bpy.data.worlds.new("Monde")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.02, 0.02, 0.04, 1.0)

# Rendu
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 128
scene.cycles.use_denoising = False
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.filepath = OUT
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("Rendu écrit :", OUT)
