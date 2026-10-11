# Pets pour Roblox : trois modèles stylisés faits de formes simples.
# Chaque pet est construit aux pieds de l'origine (z=0), à l'échelle "studs"
# (1 unité Blender = 1 stud), puis exporté en FBX dans exports/.
# Un aperçu est rendu dans preview.png.
# Usage : blender -b --factory-startup -P pets.py
import bpy
import math
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "exports")
os.makedirs(EXPORT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(nom, rgb, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return m


def forme(kind, loc, scale, rot=(0, 0, 0), material=None, nom=None):
    """Crée une primitive, applique ses transformations et l'ajoute à la liste."""
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=loc)
    elif kind == "cylindre":
        bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1, location=loc)
    elif kind == "cone":
        bpy.ops.mesh.primitive_cone_add(radius1=1, depth=1, vertices=4, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    o.rotation_euler = rot
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if kind == "sphere":
        bpy.ops.object.shade_smooth()
    if material:
        o.data.materials.append(material)
    if nom:
        o.name = nom
    return o


def exporter(nom, objets):
    """Exporte les objets d'un pet en FBX (Y up, échelle 1 = studs)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objets[0]
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT, nom + ".fbx"),
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        axis_forward="-Z",
        axis_up="Y",
        object_types={"MESH"},
        bake_space_transform=False,
        path_mode="COPY",
        embed_textures=False,
    )


# ---------- Pet 1 : Chat orange ----------
def construire_chat():
    orange = mat("Orange", (1.0, 0.5, 0.1), rough=0.45)
    blanc = mat("Blanc", (0.95, 0.95, 0.95), rough=0.4)
    noir = mat("Noir", (0.02, 0.02, 0.02), rough=0.3)
    return [
        forme("sphere", (0, 0, 0.6), (0.6, 0.5, 0.55), material=orange, nom="Corps"),
        forme("sphere", (0, -0.5, 1.45), (0.42, 0.4, 0.4), material=orange, nom="Tete"),
        forme("cone", (-0.22, -0.5, 1.9), (0.18, 0.14, 0.4), material=orange, nom="OreilleG"),
        forme("cone", (0.22, -0.5, 1.9), (0.18, 0.14, 0.4), material=orange, nom="OreilleD"),
        forme("cylindre", (-0.3, -0.2, 0.25), (0.1, 0.1, 0.25), material=orange, nom="PatteAvG"),
        forme("cylindre", (0.3, -0.2, 0.25), (0.1, 0.1, 0.25), material=orange, nom="PatteAvD"),
        forme("cylindre", (-0.3, 0.3, 0.25), (0.1, 0.1, 0.25), material=orange, nom="PatteArG"),
        forme("cylindre", (0.3, 0.3, 0.25), (0.1, 0.1, 0.25), material=orange, nom="PatteArD"),
        forme("cylindre", (0.6, 0.5, 0.75), (0.08, 0.08, 0.45), rot=(0, math.radians(60), 0), material=orange, nom="Queue"),
        forme("sphere", (-0.17, -0.88, 1.5), (0.08, 0.08, 0.08), material=blanc, nom="OeilG"),
        forme("sphere", (0.17, -0.88, 1.5), (0.08, 0.08, 0.08), material=blanc, nom="OeilD"),
        forme("sphere", (-0.17, -0.93, 1.5), (0.04, 0.04, 0.04), material=noir, nom="PupilleG"),
        forme("sphere", (0.17, -0.93, 1.5), (0.04, 0.04, 0.04), material=noir, nom="PupilleD"),
    ]


# ---------- Pet 2 : Slime vert ----------
def construire_slime():
    vert = mat("Vert", (0.2, 0.9, 0.35), rough=0.12)
    blanc = mat("Blanc", (0.95, 0.95, 0.95), rough=0.3)
    noir = mat("Noir", (0.02, 0.02, 0.02), rough=0.3)
    return [
        forme("sphere", (0, 0, 0.6), (0.9, 0.9, 0.6), material=vert, nom="Corps"),
        forme("sphere", (-0.3, -0.75, 0.85), (0.2, 0.2, 0.2), material=blanc, nom="OeilG"),
        forme("sphere", (0.3, -0.75, 0.85), (0.2, 0.2, 0.2), material=blanc, nom="OeilD"),
        forme("sphere", (-0.3, -0.93, 0.85), (0.1, 0.1, 0.1), material=noir, nom="PupilleG"),
        forme("sphere", (0.3, -0.93, 0.85), (0.1, 0.1, 0.1), material=noir, nom="PupilleD"),
    ]


# ---------- Pet 3 : Cristal violet (octaèdre flottant) ----------
def construire_cristal():
    violet = mat("Violet", (0.6, 0.2, 1.0), rough=0.05, emit=3.0)
    return [
        forme("cone", (0, 0, 1.5), (0.6, 0.6, 1.0), rot=(0, 0, math.radians(45)), material=violet, nom="Haut"),
        forme("cone", (0, 0, 0.5), (0.6, 0.6, 1.0), rot=(math.radians(180), 0, math.radians(45)), material=violet, nom="Bas"),
    ]


pets = {
    "chat": construire_chat(),
    "slime": construire_slime(),
    "cristal": construire_cristal(),
}

# Export FBX de chaque pet (au centre de l'origine)
for nom, objets in pets.items():
    exporter(nom, objets)
    print("Exporté :", nom)

# ---------- Aperçu : les trois pets côte à côte ----------
decalages = {"chat": -3.0, "slime": 0.0, "cristal": 3.0}
for nom, objets in pets.items():
    for o in objets:
        o.location.x += decalages[nom]

sol = forme("cylindre", (0, 0, -0.05), (6, 3, 0.05), material=mat("Sol", (0.05, 0.05, 0.08), rough=0.4), nom="Sol")

bpy.ops.object.light_add(type="AREA", location=(4, -5, 6))
cle = bpy.context.active_object
cle.data.energy = 1200
cle.data.size = 5

bpy.ops.object.light_add(type="AREA", location=(-5, 4, 4))
contre = bpy.context.active_object
contre.data.energy = 500
contre.data.size = 3
contre.data.color = (0.6, 0.7, 1.0)

bpy.ops.object.camera_add(location=(0, -12, 4.5))
cam = bpy.context.active_object
cam.data.lens = 50
cible = Vector((0, 0, 1.2))
cam.rotation_euler = (cible - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.scene.camera = cam

monde = bpy.data.worlds.new("Monde")
monde.use_nodes = True
monde.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.03, 0.05, 1.0)
bpy.context.scene.world = monde

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 64
scene.cycles.use_denoising = False
scene.render.resolution_x = 1280
scene.render.resolution_y = 540
scene.render.filepath = os.path.join(HERE, "preview.png")
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("Aperçu écrit :", scene.render.filepath)
