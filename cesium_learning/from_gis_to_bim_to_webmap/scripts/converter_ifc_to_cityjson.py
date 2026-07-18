"""
IFC -> CityJSON, minimal but real.

⚠️  AI-GENERATED CODE (Claude, 2026-07-18). It works end-to-end and the output
    has been validated (cjval schema check + val3dity ISO 19107 + visual check
    in ninja and QGIS), but it deserves a proper human review pass before
    being trusted as a pipeline component: error handling, edge cases
    (multiple buildings, missing georeferencing, rotated map conversions)
    and the §8 mapping decisions are all still naive.

Pipeline:
  1. read length unit scale from IfcUnitAssignment (never assume metres)
  2. read IfcMapConversion (rotation + translation) -> real-world CRS coords
  3. tessellate every IfcProduct with ifcopenshell.geom (USE_WORLD_COORDS=True)
  4. de-duplicate vertices into one global list (CityJSON needs shared indices)
  5. quantize floats -> integers via a transform (scale + translate)

--- Bug history ---
v1 -> v2: the QGIS CityJSON loaders (both the Processing algorithm and the
native dialog) loaded the file "successfully" (log said 'Loaded 1 objects')
but produced NO layer, with no error anywhere. The file itself was proven
valid by three independent tools (ninja, cjval, val3dity), which isolated
the cause to a QGIS-specific incompatibility: the "ifcGlobalId" attribute
was a LIST of 14 strings. QGIS attribute tables only hold scalar values
(one cell = one string/number); a list-valued attribute made the loader
silently drop the entire feature. Lesson: "valid CityJSON" and "loadable
in a tabular GIS" are not the same thing (cf. Vitalis et al. 2020 on the
CityJSON->QGIS impedance mismatch).

v2: attributes are SCALAR only — lists joined with ";" into single strings.

What this script does NOT do (deliberately, for now):
  - no semantic surface classification (WallSurface/RoofSurface/GroundSurface)
  - no per-element granularity (everything collapses into one "Building")
  - no watertightness check / normal orientation fix
"""
import json
import ifcopenshell
import ifcopenshell.geom

IFC_PATH = r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\data\cmcc_footprint_v1.ifc"
OUT_PATH = r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\data\cmcc.city.json"


# --- 1. unit scale factor: everything downstream must be in metres ---

def get_length_scale(model):
    prefix_factors = {
        "EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6,
        "KILO": 1e3, "HECTO": 1e2, "DECA": 1e1, None: 1.0,
        "DECI": 1e-1, "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6,
    }
    for ua in model.by_type("IfcUnitAssignment"):
        for unit in ua.Units:
            if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
                return prefix_factors.get(unit.Prefix, 1.0)
    return 1.0  # fallback: assume metres, but this should never trigger silently


# --- 2. georeferencing: rotation + translation from IfcMapConversion ---

def get_map_conversion(model):
    conv = model.by_type("IfcMapConversion")
    if not conv:
        return None
    c = conv[0]
    ax = c.XAxisAbscissa if c.XAxisAbscissa is not None else 1.0
    ay = c.XAxisOrdinate if c.XAxisOrdinate is not None else 0.0
    crs = model.by_type("IfcProjectedCRS")[0]
    return {
        "e": c.Eastings, "n": c.Northings, "h": c.OrthogonalHeight or 0.0,
        "cos": ax, "sin": ay,
        "epsg_name": crs.Name,  # e.g. "EPSG:32633"
    }


def to_map_coords(x, y, z, scale, mc):
    # apply unit scale first (project units -> metres)
    x, y, z = x * scale, y * scale, z * scale
    if mc is None:
        return x, y, z
    # 2D rotation (IfcMapConversion only rotates in the XY plane)
    xr = mc["cos"] * x - mc["sin"] * y
    yr = mc["sin"] * x + mc["cos"] * y
    return xr + mc["e"], yr + mc["n"], z + mc["h"]


# --- 3 & 4. tessellate every IfcProduct, de-duplicating vertices globally ---

def tessellate_all(model, scale, mc):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    global_verts = []       # list of (x,y,z) in real-world map coordinates
    vertex_index = {}       # rounded (x,y,z) -> index, for de-duplication
    faces_per_product = []  # list of (product, [[i,j,k], ...])

    def get_index(pt):
        key = tuple(round(c, 4) for c in pt)  # snap to 0.1mm before de-dup
        if key not in vertex_index:
            vertex_index[key] = len(global_verts)
            global_verts.append(pt)
        return vertex_index[key]

    for product in model.by_type("IfcProduct"):
        if not product.Representation:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
        except Exception as e:
            print(f"skip {product.is_a()} {product.Name}: {e}")
            continue

        raw_verts = shape.geometry.verts
        raw_faces = shape.geometry.faces

        local_to_global = {}
        for i in range(0, len(raw_verts), 3):
            x, y, z = raw_verts[i], raw_verts[i + 1], raw_verts[i + 2]
            mapped = to_map_coords(x, y, z, scale, mc)
            local_to_global[i // 3] = get_index(mapped)

        faces = []
        for i in range(0, len(raw_faces), 3):
            tri = [local_to_global[raw_faces[i]],
                   local_to_global[raw_faces[i + 1]],
                   local_to_global[raw_faces[i + 2]]]
            faces.append(tri)

        faces_per_product.append((product, faces))

    return global_verts, faces_per_product


# --- 5. quantization: floats -> integers, per the CityJSON transform ---

def quantize(verts, scale_m=0.001):
    xs, ys, zs = zip(*verts)
    origin = (min(xs), min(ys), min(zs))
    q = [
        [round((x - origin[0]) / scale_m),
         round((y - origin[1]) / scale_m),
         round((z - origin[2]) / scale_m)]
        for x, y, z in verts
    ]
    return q, origin, scale_m


# --- assemble the CityJSON ---

def build_cityjson(global_verts, faces_per_product, mc, quant_scale=0.001):
    q_verts, origin, scale_m = quantize(global_verts, quant_scale)

    boundaries = []
    for product, faces in faces_per_product:
        boundaries.extend([[f] for f in faces])  # MultiSurface: one ring per face

    # v2: scalar attributes only. QGIS attribute tables cannot hold lists;
    # a list-valued attribute can make the loader drop the feature silently.
    city_object = {
        "type": "Building",
        "attributes": {
            "ifcGlobalIds": ";".join(p.GlobalId for p, _ in faces_per_product),
            "elementCount": len(faces_per_product),
            "elementTypes": ";".join(sorted(set(p.is_a() for p, _ in faces_per_product))),
        },
        "geometry": [{
            "type": "MultiSurface",
            "lod": "2",
            "boundaries": boundaries,
        }],
    }

    cm = {
        "type": "CityJSON",
        "version": "2.0",
        "transform": {
            "scale": [scale_m, scale_m, scale_m],
            "translate": list(origin),
        },
        "metadata": {
            "referenceSystem": (
                f"https://www.opengis.net/def/crs/EPSG/0/{mc['epsg_name'].split(':')[-1]}"
                if mc else None
            ),
        },
        "CityObjects": {"building_1": city_object},
        "vertices": q_verts,
    }
    return cm


if __name__ == "__main__":
    model = ifcopenshell.open(IFC_PATH)

    scale = get_length_scale(model)
    mc = get_map_conversion(model)

    print("unit scale -> metres:", scale)
    print("map conversion:", mc)

    verts, faces = tessellate_all(model, scale, mc)
    print("global (de-duplicated) vertices:", len(verts))
    print("products tessellated:", len(faces))

    cm = build_cityjson(verts, faces, mc)

    with open(OUT_PATH, "w") as f:
        json.dump(cm, f, indent=2)

    print("written:", OUT_PATH)