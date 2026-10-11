# Pets Roblox, style "chibi" : Chat, Bébé dragon, Slime royal.
#
# Les corps sont des formes fusionnées (remesh voxel + lissage) pour un rendu
# organique d'un seul tenant. 1 unité Blender = 1 stud, pieds à z=0, le pet
# regarde vers -Y.
#
# Sorties :
#   exports/<pet>.fbx   un maillage par pet (couleurs de sommets + matériaux)
#   icones/<pet>.png    icône 512x512 sur fond transparent (UI du jeu)
#   preview.png         photo de groupe
#
# Usage : blender -b --factory-startup -P pets.py
#         RAPIDE=1 blender -b --factory-startup -P pets.py   (rendu brouillon)
import bpy
import math
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "exports")
ICONES = os.path.join(HERE, "icones")
os.makedirs(EXPORT, exist_ok=True)
os.makedirs(ICONES, exist_ok=True)
RAPIDE = os.environ.get("RAPIDE") == "1"
TRIS_CORPS = 3500  # budget de triangles du corps principal de chaque pet

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection


# ---------------------------------------------------------------- matériaux
def mat(nom, rgb, props=None):
    m = bpy.data.materials.new(nom)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1.0)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    for k, v in (props or {}).items():
        if k in b.inputs:
            b.inputs[k].default_value = (*v, 1.0) if k.endswith("Color") else v
    m["rgb"] = rgb
    return m


def brillant(nom, rgb):
    return mat(nom, rgb, {"Roughness": 0.25, "Coat Weight": 0.6, "Coat Roughness": 0.08})


def fourrure(nom, rgb):
    return mat(nom, rgb, {"Roughness": 0.55, "Sheen Weight": 0.6, "Sheen Roughness": 0.4,
                          "Subsurface Weight": 0.15, "Subsurface Scale": 0.05})


NOIR_YEUX = mat("NoirYeux", (0.015, 0.015, 0.03), {"Roughness": 0.05, "Coat Weight": 1.0,
                                                   "Coat Roughness": 0.02})
REFLET = mat("Reflet", (1.0, 1.0, 1.0), {"Emission Color": (1.0, 1.0, 1.0),
                                         "Emission Strength": 4.0})
ROSE = mat("Rose", (1.0, 0.42, 0.55), {"Roughness": 0.7})
BOUCHE = mat("Bouche", (0.18, 0.03, 0.06), {"Roughness": 0.4})
OR = mat("Or", (1.0, 0.72, 0.22), {"Metallic": 1.0, "Roughness": 0.18})


# ---------------------------------------------------------------- géométrie
def sphere(loc, scale, seg=20, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=seg, ring_count=rings, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return o


def cone(loc, r1, r2, depth, axe=(0, 0, 1)):
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r1, radius2=r2, depth=depth, location=loc)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(axe).normalized())
    return o


def tube(points, rayons):
    """Tube lisse (spline NURBS) dont l'épaisseur suit `rayons`."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.resolution_u = 6
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for pt, co, r in zip(sp.points, points, rayons):
        pt.co = (*co, 1.0)
        pt.radius = r
    sp.order_u = 3
    sp.use_endpoint_u = True
    o = bpy.data.objects.new("tube", cu)
    coll.objects.link(o)
    return o


def bake(o):
    """Remplace `o` par un maillage avec modificateurs et transformations appliqués."""
    bpy.context.view_layer.update()
    nom = o.name
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_world)
    bpy.data.objects.remove(o)
    new = bpy.data.objects.new(nom, me)
    coll.objects.link(new)
    return new


def joindre(objs, nom):
    objs = [bake(o) for o in objs]
    if len(objs) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
    o = objs[0]
    o.name = nom
    return o


def lisser(o):
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))


def habiller(o, materiau):
    o.data.materials.clear()
    o.data.materials.append(materiau)
    lisser(o)
    return o


def piece(objs, nom, materiau):
    return habiller(joindre(objs, nom), materiau)


def organique(objs, nom, materiau, voxel=0.025, lissage=6, tris=TRIS_CORPS):
    """Fusionne des formes en une seule surface douce (remesh voxel + lissage)."""
    o = joindre(objs, nom)
    r = o.modifiers.new("remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    s = o.modifiers.new("lisse", "SMOOTH")
    s.factor = 0.6
    s.iterations = lissage
    o = bake(o)
    nb = sum(len(p.vertices) - 2 for p in o.data.polygons)
    if nb > tris:
        d = o.modifiers.new("allege", "DECIMATE")
        d.ratio = tris / nb
        o = bake(o)
    o.name = nom
    return habiller(o, materiau)


def sur_ellipsoide(c, rayons, d):
    """Point et normale sur un ellipsoïde (centre c, demi-axes rayons) dans la direction d."""
    d = Vector(d).normalized()
    p = Vector(c) + Vector((rayons[0] * d.x, rayons[1] * d.y, rayons[2] * d.z))
    n = Vector((d.x / rayons[0], d.y / rayons[1], d.z / rayons[2])).normalized()
    return p, n


def pastille(c, rayons, d, taille, enfonce):
    """Ellipsoïde aplati posé à la surface (yeux, joues...), orienté selon la normale."""
    p, n = sur_ellipsoide(c, rayons, d)
    q = n.to_track_quat("Z", "Y")
    pos = p - n * enfonce
    o = sphere(pos, taille)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = q
    return o, pos, q


def yeux(c, rayons, dirs, taille):
    noirs, reflets = [], []
    for d in dirs:
        o, pos, q = pastille(c, rayons, d, taille, enfonce=0.03)
        noirs.append(o)
        m = q.to_matrix()
        # gros reflet en haut, petit reflet en bas (même côté pour les deux yeux)
        for fx, fy, r in ((0.32, 0.36, 0.30), (-0.30, -0.34, 0.15)):
            hp = pos + m @ Vector((fx * taille[0], fy * taille[1], taille[2] * 0.85))
            h = sphere(hp, (r * taille[0], r * taille[0], r * taille[0] * 0.5), seg=10, rings=6)
            h.rotation_mode = "QUATERNION"
            h.rotation_quaternion = q
            reflets.append(h)
    return [piece(noirs, "Yeux", NOIR_YEUX), piece(reflets, "Reflets", REFLET)]


def joues(c, rayons, dirs, taille=(0.14, 0.085, 0.03)):
    return piece([pastille(c, rayons, d, taille, 0.018)[0] for d in dirs], "Joues", ROSE)


def y_surface(c, rayons, x, z, sortie=0.005):
    """Y de la face avant d'un ellipsoïde au point (x, z)."""
    k = 1 - ((x - c[0]) / rayons[0]) ** 2 - ((z - c[2]) / rayons[2]) ** 2
    return c[1] - rayons[1] * math.sqrt(max(k, 0.0)) - sortie


# ---------------------------------------------------------------- Chat
def construire_chat():
    orange = fourrure("Orange", (1.0, 0.32, 0.03))
    creme = fourrure("Creme", (1.0, 0.9, 0.75))
    tete_c, tete_r = (0, 0, 1.35), (1.0, 0.9, 0.85)
    corps_c, corps_r = (0, 0.15, 0.5), (0.6, 0.55, 0.5)

    corps = organique([
        sphere(tete_c, tete_r),
        sphere(corps_c, corps_r),
        sphere((-0.32, -0.3, 0.15), (0.2, 0.24, 0.16)),
        sphere((0.32, -0.3, 0.15), (0.2, 0.24, 0.16)),
        sphere((-0.45, 0.35, 0.17), (0.22, 0.26, 0.18)),
        sphere((0.45, 0.35, 0.17), (0.22, 0.26, 0.18)),
        cone((-0.58, 0.05, 2.05), 0.42, 0.05, 0.8, axe=(-0.45, 0, 1)),
        cone((0.58, 0.05, 2.05), 0.42, 0.05, 0.8, axe=(0.45, 0, 1)),
        tube([(0, 0.55, 0.35), (0, 1.0, 0.45), (0.05, 1.15, 0.9), (0.3, 1.0, 1.3), (0.5, 0.8, 1.35)],
             [0.16, 0.14, 0.12, 0.1, 0.07]),
    ], "Corps", orange)

    museau_c = [(-0.13, -0.8, 1.12), (0.13, -0.8, 1.12)]
    museau_r = (0.2, 0.15, 0.15)
    museau = piece([sphere(c, museau_r) for c in museau_c]
                   + [pastille(corps_c, corps_r, (0, -1, 0.1), (0.34, 0.32, 0.08), 0.05)[0]]
                   + [cone((s * 0.56, -0.24, 2.0), 0.27, 0.03, 0.58, axe=(s * 0.45, 0, 1)) for s in (-1, 1)],
                   "Creme", creme)
    # aplatir l'intérieur des oreilles vers l'avant
    for v in museau.data.vertices:
        if v.co.z > 1.65:
            v.co.y = min(v.co.y, -0.2) - 0.02 * (v.co.z - 1.65)

    def y_museau(x, z):
        return min(y_surface(c, museau_r, x, z) for c in museau_c)

    nez = piece([sphere((0, y_museau(0, 1.21) + 0.02, 1.21), (0.085, 0.05, 0.06))], "Nez", ROSE)
    pts = [(x, 0, z) for x, z in ((-0.15, 1.03), (-0.075, 0.985), (0, 1.03), (0.075, 0.985), (0.15, 1.03))]
    pts = [(x, y_museau(x, z), z) for x, _, z in pts]
    bouche = piece([tube(pts, [0.018] * len(pts))], "Bouche", BOUCHE)

    rayure = fourrure("Rayures", (0.85, 0.16, 0.0))
    rayures = piece([pastille(tete_c, tete_r, d, t, 0.02)[0] for d, t in (
        ((0, -0.45, 1), (0.08, 0.26, 0.03)),
        ((-0.2, -0.45, 1), (0.06, 0.2, 0.03)),
        ((0.2, -0.45, 1), (0.06, 0.2, 0.03)),
    )], "Rayures", rayure)

    return [corps, museau, nez, bouche, rayures,
            *yeux(tete_c, tete_r, [(-0.38, -1, 0.12), (0.38, -1, 0.12)], (0.17, 0.23, 0.07)),
            joues(tete_c, tete_r, [(-0.62, -0.8, -0.18), (0.62, -0.8, -0.18)])]


# ---------------------------------------------------------------- Bébé dragon
def construire_dragon():
    turquoise = brillant("Turquoise", (0.02, 0.62, 0.5))
    ventre = fourrure("Ventre", (1.0, 0.88, 0.62))
    corail = mat("Corail", (1.0, 0.3, 0.32), {"Roughness": 0.4, "Coat Weight": 0.4})
    corne = mat("Corne", (1.0, 0.85, 0.55), {"Roughness": 0.35, "Coat Weight": 0.5})
    tete_c, tete_r = (0, -0.1, 1.35), (0.85, 0.8, 0.75)
    corps_c, corps_r = (0, 0.2, 0.55), (0.6, 0.6, 0.55)
    nez_c, nez_r = (0, -0.72, 1.1), (0.42, 0.32, 0.28)

    corps = organique([
        sphere(tete_c, tete_r),
        sphere(nez_c, nez_r),
        sphere(corps_c, corps_r),
        sphere((-0.35, -0.25, 0.15), (0.2, 0.24, 0.17)),
        sphere((0.35, -0.25, 0.15), (0.2, 0.24, 0.17)),
        sphere((-0.45, 0.45, 0.18), (0.24, 0.28, 0.2)),
        sphere((0.45, 0.45, 0.18), (0.24, 0.28, 0.2)),
        tube([(0, 0.5, 0.35), (0, 0.95, 0.22), (0.15, 1.35, 0.28), (0.45, 1.6, 0.5), (0.7, 1.6, 0.8)],
             [0.3, 0.22, 0.15, 0.1, 0.05]),
    ], "Corps", turquoise)

    ventre_o = piece([pastille(corps_c, corps_r, (0, -1, 0.05), (0.42, 0.42, 0.1), 0.06)[0]],
                     "Ventre", ventre)

    # ailes : trois "doigts" en éventail par côté, fusionnés ; + piques du dos
    ailes = []
    for s in (-1, 1):
        for ang, long in ((18, 0.68), (50, 0.6), (82, 0.45)):
            a = math.radians(ang)
            centre = (s * (0.3 + long * math.cos(a)), 0.55 + 0.15 * long, 1.05 + long * math.sin(a))
            o = sphere(centre, (long, 0.05, 0.17))
            o.rotation_euler = (0, -s * a, s * math.radians(-15))
            ailes.append(o)
    for d in ((0, 0.45, 0.9), (0, 0.8, 0.6), (0, 0.98, 0.2)):
        p, n = sur_ellipsoide(corps_c, corps_r, d)
        ailes.append(cone(p + n * 0.06, 0.1, 0.01, 0.22, axe=n))
    ailes_o = organique(ailes, "Ailes", corail, voxel=0.018, lissage=4, tris=3000)

    cornes = []
    for s in (-1, 1):
        p, n = sur_ellipsoide(tete_c, tete_r, (s * 0.45, 0.25, 0.9))
        axe = (n + Vector((s * 0.15, 0.7, 0))).normalized()
        cornes.append(cone(p + axe * 0.15, 0.13, 0.03, 0.5, axe=axe))
    cornes_o = organique(cornes, "Cornes", corne, voxel=0.015, lissage=3, tris=1500)

    narines = piece([sphere((s * 0.12, y_surface(nez_c, nez_r, s * 0.12, 1.18) + 0.015, 1.18),
                            (0.04, 0.03, 0.03)) for s in (-1, 1)], "Narines", BOUCHE)
    pts = [(x, y_surface(nez_c, nez_r, x, z), z)
           for x, z in ((-0.2, 1.04), (-0.1, 0.995), (0, 0.985), (0.1, 0.995), (0.2, 1.04))]
    bouche = piece([tube(pts, [0.018] * len(pts))], "Bouche", BOUCHE)

    return [corps, ventre_o, ailes_o, cornes_o, narines, bouche,
            *yeux(tete_c, tete_r, [(-0.42, -0.8, 0.25), (0.42, -0.8, 0.25)], (0.15, 0.2, 0.065)),
            joues(tete_c, tete_r, [(-0.65, -0.6, -0.1), (0.65, -0.6, -0.1)], (0.12, 0.075, 0.03))]


# ---------------------------------------------------------------- Slime royal
def construire_slime():
    gelee = mat("Gelee", (0.08, 0.42, 1.0), {"Roughness": 0.15, "Subsurface Weight": 0.35,
                                             "Subsurface Radius": (0.4, 0.7, 1.0),
                                             "Subsurface Scale": 0.25, "Coat Weight": 1.0,
                                             "Coat Roughness": 0.03})
    rubis = mat("Rubis", (1.0, 0.05, 0.15), {"Roughness": 0.05, "Coat Weight": 1.0})
    saphir = mat("Saphir", (0.15, 0.25, 1.0), {"Roughness": 0.05, "Coat Weight": 1.0})
    corps_c, corps_r = (0, 0, 0.62), (0.88, 0.82, 0.62)

    corps = organique([
        sphere(corps_c, corps_r),
        sphere((0, 0.04, 1.08), (0.62, 0.6, 0.55)),
        sphere((-0.62, -0.42, 0.1), (0.24, 0.24, 0.12)),  # petites coulures à la base
        sphere((0.62, -0.42, 0.1), (0.24, 0.24, 0.12)),
    ], "Corps", gelee, voxel=0.03, lissage=8)

    # couronne : bandeau + 5 pointes à boule, fusionnés
    cz = 1.6
    bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.065, location=(0, 0.04, cz))
    bandeau = bpy.context.active_object
    bandeau.scale = (1, 1, 1.6)
    parts = [bandeau]
    for i in range(5):
        a = 2 * math.pi * i / 5 - math.pi / 2
        x, y = 0.36 * math.cos(a), 0.04 + 0.36 * math.sin(a)
        parts.append(cone((x, y, cz + 0.22), 0.1, 0.02, 0.3))
        parts.append(sphere((x, y, cz + 0.39), (0.05, 0.05, 0.05)))
    couronne = organique(parts, "Couronne", OR, voxel=0.012, lissage=3, tris=3000)
    gemmes = [piece([sphere((0, 0.04 - 0.43, cz), (0.08, 0.04, 0.08))], "Rubis", rubis)]
    saph = []
    for a in (math.radians(-90 + 72), math.radians(-90 - 72)):
        x, y = 0.43 * math.cos(a), 0.04 + 0.43 * math.sin(a)
        o = sphere((x, y, cz), (0.045, 0.025, 0.045))
        o.rotation_euler = (0, 0, a + math.pi / 2)
        saph.append(o)
    gemmes.append(piece(saph, "Saphirs", saphir))

    bouche = piece([pastille(corps_c, corps_r, (0, -1, -0.02), (0.12, 0.075, 0.03), 0.012)[0]],
                   "Bouche", BOUCHE)

    return [corps, couronne, *gemmes, bouche,
            *yeux(corps_c, corps_r, [(-0.33, -1, 0.32), (0.33, -1, 0.32)], (0.19, 0.25, 0.08)),
            joues(corps_c, corps_r, [(-0.6, -0.8, 0.05), (0.6, -0.8, 0.05)])]


pets = {
    "chat": construire_chat(),
    "dragon": construire_dragon(),
    "slime_royal": construire_slime(),
}


# ---------------------------------------------------------------- export FBX
def exporter(nom, objets):
    """Duplique les pièces, écrit leur couleur en couleurs de sommets, fusionne et exporte."""
    copies = []
    for o in objets:
        c = o.copy()
        c.data = o.data.copy()
        coll.objects.link(c)
        rgb = o.data.materials[0]["rgb"]
        attr = c.data.color_attributes.new("Couleur", "BYTE_COLOR", "CORNER")
        attr.data.foreach_set("color", [*rgb, 1.0] * len(c.data.loops))
        copies.append(c)
    bpy.ops.object.select_all(action="DESELECT")
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    pet = bpy.context.active_object
    pet.name = nom
    tris = sum(len(p.vertices) - 2 for p in pet.data.polygons)
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT, nom + ".fbx"),
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        axis_forward="-Z",
        axis_up="Y",
        object_types={"MESH"},
        colors_type="SRGB",
        path_mode="COPY",
    )
    bpy.data.objects.remove(pet)
    print(f"Exporté : {nom}.fbx ({tris} triangles)")


for nom, objets in pets.items():
    exporter(nom, objets)


# ---------------------------------------------------------------- studio
def viser(o, cible):
    o.rotation_euler = (Vector(cible) - o.location).to_track_quat("-Z", "Y").to_euler()


def lumiere(loc, energie, taille, couleur, cible=(0, 0, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    o = bpy.context.active_object
    o.data.energy = energie
    o.data.size = taille
    o.data.color = couleur
    viser(o, cible)
    return o


lumiere((-6, -8, 9), 6000, 7, (1.0, 0.95, 0.88))   # clé, chaude
lumiere((8, -6, 3), 1800, 6, (0.8, 0.88, 1.0))     # remplissage, froide
lumiere((0, 7, 7), 4500, 5, (1.0, 1.0, 1.0))       # contre-jour (liseré)

monde = bpy.data.worlds.new("Monde")
monde.use_nodes = True
fond = monde.node_tree.nodes["Background"]
fond.inputs["Color"].default_value = (0.55, 0.55, 0.75, 1.0)
fond.inputs["Strength"].default_value = 0.35
scene.world = monde

# fond studio arrondi (cyclorama)
profil = [(y, 0.0) for y in (-14, -6, 0, 4)]
profil += [(4 + 5 * math.sin(t), 5 - 5 * math.cos(t))
           for t in (math.radians(a) for a in range(10, 91, 10))]
profil += [(9, 16)]
verts = [(x, y, z) for (y, z) in profil for x in (-25, 25)]
faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(profil) - 1)]
me = bpy.data.meshes.new("Studio")
me.from_pydata(verts, [], faces)
studio = bpy.data.objects.new("Studio", me)
coll.objects.link(studio)
habiller(studio, mat("Studio", (0.4, 0.36, 0.9), {"Roughness": 0.85}))

bpy.ops.object.camera_add()
cam = bpy.context.active_object
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.use_denoising = False  # OpenImageDenoise absent de ce build
scene.cycles.sample_clamp_indirect = 4.0
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = -0.3
except TypeError:
    pass

# léger boost de saturation (AgX désature un peu les couleurs vives)
scene.use_nodes = True
arbre = scene.node_tree
sat = arbre.nodes.new("CompositorNodeHueSat")
sat.inputs["Saturation"].default_value = 1.3
arbre.links.new(arbre.nodes["Render Layers"].outputs["Image"], sat.inputs["Image"])
arbre.links.new(sat.outputs["Image"], arbre.nodes["Composite"].inputs["Image"])


def rendre(chemin, w, h, samples):
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 50 if RAPIDE else 100
    scene.cycles.samples = max(16, samples // 4) if RAPIDE else samples
    scene.render.filepath = chemin
    bpy.ops.render.render(write_still=True)
    print("Rendu :", chemin)


# ---------------------------------------------------------------- icônes
cam.data.lens = 85
demi_fov = math.atan(cam.data.sensor_width / 2 / cam.data.lens)
scene.render.film_transparent = True
studio.hide_render = True
for nom, objets in pets.items():
    for autre, objs in pets.items():
        for o in objs:
            o.hide_render = autre != nom
    pts = [o.matrix_world @ v.co for o in objets for v in o.data.vertices]
    mini = Vector([min(p[i] for p in pts) for i in range(3)])
    maxi = Vector([max(p[i] for p in pts) for i in range(3)])
    centre = (mini + maxi) / 2
    rayon = (maxi - mini).length / 2
    a, e = math.radians(-28), math.radians(12)
    direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = centre + direction * (rayon / math.sin(demi_fov) * 0.92)
    viser(cam, centre)
    rendre(os.path.join(ICONES, nom + ".png"), 512, 512, 128)

# ---------------------------------------------------------------- photo de groupe
scene.render.film_transparent = False
studio.hide_render = False
places = {"chat": (-3.1, 0.0, 18), "dragon": (0.0, 0.4, 0), "slime_royal": (3.1, 0.0, -18)}
for nom, objets in pets.items():
    x, y, rot = places[nom]
    pivot = bpy.data.objects.new("Pivot_" + nom, None)
    coll.objects.link(pivot)
    for o in objets:
        o.hide_render = False
        o.parent = pivot
    pivot.location = (x, y, 0)
    pivot.rotation_euler = (0, 0, math.radians(rot))

cam.data.lens = 50
cam.location = (0, -14, 4.2)
viser(cam, (0, 0, 1.15))
rendre(os.path.join(HERE, "preview.png"), 1600, 800, 256)
