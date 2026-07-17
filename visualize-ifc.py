"""
This code uses ifcopenshell and trimesh to visualize .ifc objects. Visualization happens thanks to a conversion in a set of triangular mesh.
"""
import ifcopenshell
import ifcopenshell.geom
import numpy as np
import trimesh # library for "loading and using triangular meshes"

model = ifcopenshell.open(r'D:\CMCC_REGEN4BE\sample_files\Building-Architecture.ifc')

# From parametric description to explicit mesh
settings = ifcopenshell.geom.settings() # creates a config object
# resolve each element's nested local placements into the project's absolute coordinate system.
# If not set, each element keeps its own local origin, so meshes overlap when combined in one scene
settings.set(settings.USE_WORLD_COORDS, True)

#
meshes = []
for element in model.by_type("IfcProduct"): # Taking "IfcProduct" you take a class that is general and contains walls, roof ecc. No need to list each one of them
# If you want to see the difference play with "IfcWall"
# exclude elements with no geometry
    if not element.Representation:
        continue
# Resolve the IFC element's parametric/procedural geometry (extrusions, boolean solids...)
# into an explicit triangulated mesh, using OpenCascade under the hood; also composes
# the nested local placements into absolute coordinates (since USE_WORLD_COORDS=True)
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = np.array(shape.geometry.verts).reshape(-1, 3) # each vert is written one time and shared by more triangles
        faces = np.array(shape.geometry.faces).reshape(-1, 3) # not coordinates, but indices pointing back to rows in verts
        meshes.append(trimesh.Trimesh(vertices=verts, faces=faces)) # create trimesh object
    except Exception as e:
        print(f"Skip {element.is_a()} {element.Name}: {e}")

scene = trimesh.util.concatenate(meshes) # create scene object
scene.show()  # open interactive window for visualization