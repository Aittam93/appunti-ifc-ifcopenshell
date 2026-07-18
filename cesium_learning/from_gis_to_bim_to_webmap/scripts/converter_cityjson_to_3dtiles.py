"""
CityJSON -> 3D Tiles (glb + tileset.json), no external tiler.

AI-GENERATED CODE (Claude, 2026-07-18). Tested end-to-end: the output GLB
passes the official Khronos glTF validator (0 errors) and the tileset passes
the official CesiumGS 3d-tiles-validator (0 errors). Still deserves a human
review pass: no metadata/picking extensions yet (EXT_mesh_features), single
tile only, naive triangle fan for non-triangular faces.

Why not just `cjio export glb`? Tested it: cjio writes vertices in ABSOLUTE
UTM coordinates (e.g. 4.5 million metres). Two problems: (a) float32 on the
GPU loses ~half a metre of precision at that magnitude -> jitter; (b) adding
a tileset ECEF transform on top would double-apply the position. 3D Tiles
requires SMALL local vertices + the large numbers in the tileset transform
(read once, in float64). Same origin-shift pattern as IfcMapConversion and
the CityJSON transform - third format, same physics.

Approach A from Module 3 (pure translation):
  1. de-quantize CityJSON vertices -> real UTM coords
  2. UTM -> ECEF (EPSG:4978) with pyproj
  3. subtract the ECEF centroid -> small local coords (float32-safe)
  4. rotate Z-up -> Y-up baked into vertices (per 3D Tiles spec, the glTF
     content is rotated Y-up -> Z-up at load time; we pre-compensate)
  5. write a minimal valid GLB (positions + indices, nothing else)
  6. write tileset.json with transform = translation to the ECEF centroid
     (column-major 4x4; bounding box is in the tile's LOCAL Z-up frame)
"""
import json
import struct
import numpy as np
from pyproj import Transformer


CJ_PATH = r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\data\cmcc.city.json"
GLB_PATH = r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\tiles\building.glb"
TILESET_PATH = r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\tiles\tileset.json"


def load_cityjson(path):
    cm = json.load(open(path))
    tr = cm["transform"]
    verts = np.array([
        [v[0] * tr["scale"][0] + tr["translate"][0],
         v[1] * tr["scale"][1] + tr["translate"][1],
         v[2] * tr["scale"][2] + tr["translate"][2]]
        for v in cm["vertices"]
    ])
    # collect all triangles from all geometries
    # (our ifc_to_cityjson pipeline writes triangles only; the fan below
    #  handles the general polygon case for convex faces)
    tris = []
    for co in cm["CityObjects"].values():
        for geom in co.get("geometry", []):
            for surface in geom["boundaries"]:   # MultiSurface: [ [ring], ... ]
                ring = surface[0]                # outer ring (no holes handled)
                if len(ring) == 3:
                    tris.append(ring)
                else:
                    for i in range(1, len(ring) - 1):
                        tris.append([ring[0], ring[i], ring[i + 1]])
    epsg = cm["metadata"]["referenceSystem"].rsplit("/", 1)[-1]
    return verts, np.array(tris, dtype=np.uint32), epsg


def to_ecef_local(verts, epsg):
    t = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4978", always_xy=True)
    X, Y, Z = t.transform(verts[:, 0], verts[:, 1], verts[:, 2])
    ecef = np.column_stack([X, Y, Z])
    origin = ecef.mean(axis=0)                   # float64: keeps full precision
    return (ecef - origin).astype(np.float32), origin


def zup_to_yup(verts):
    # (x, y, z)_Zup -> (x, z, -y)_Yup ; Cesium applies the inverse at load time
    out = np.empty_like(verts)
    out[:, 0] = verts[:, 0]
    out[:, 1] = verts[:, 2]
    out[:, 2] = -verts[:, 1]
    return out


def write_glb(path, verts, tris):
    pos = verts.astype(np.float32)
    idx = tris.ravel().astype(np.uint32)

    pos_bytes = pos.tobytes()
    idx_bytes = idx.tobytes()
    pad1 = (4 - len(pos_bytes) % 4) % 4          # 4-byte alignment between views
    bin_chunk = pos_bytes + b"\x00" * pad1 + idx_bytes
    pad2 = (4 - len(bin_chunk) % 4) % 4
    bin_chunk += b"\x00" * pad2

    gltf = {
        "asset": {"version": "2.0", "generator": "cityjson_to_tiles.py"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{
            "attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(pos),
             "type": "VEC3",
             "min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist()},
            {"bufferView": 1, "componentType": 5125, "count": len(idx),
             "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes),
             "target": 34962},
            {"buffer": 0, "byteOffset": len(pos_bytes) + pad1,
             "byteLength": len(idx_bytes), "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_chunk)}],
    }
    gltf_json = json.dumps(gltf, separators=(",", ":")).encode()
    pad3 = (4 - len(gltf_json) % 4) % 4
    gltf_json += b" " * pad3                     # JSON chunk padded with spaces

    total = 12 + 8 + len(gltf_json) + 8 + len(bin_chunk)
    with open(path, "wb") as f:
        f.write(b"glTF" + struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(gltf_json), 0x4E4F534A) + gltf_json)
        f.write(struct.pack("<II", len(bin_chunk), 0x004E4942) + bin_chunk)


if __name__ == "__main__":
    verts_utm, tris, epsg = load_cityjson(CJ_PATH)
    print("EPSG:", epsg, "| vertices:", len(verts_utm), "| triangles:", len(tris))

    verts_local, origin = to_ecef_local(verts_utm, epsg)
    print("ECEF origin:", origin.round(1).tolist())

    # bounding box in the tile's LOCAL Z-up frame (centre + half-extents, +1m margin)
    c = (verts_local.max(axis=0) + verts_local.min(axis=0)) / 2
    h = (verts_local.max(axis=0) - verts_local.min(axis=0)) / 2 + 1.0
    box = [float(c[0]), float(c[1]), float(c[2]),
           float(h[0]), 0, 0,   0, float(h[1]), 0,   0, 0, float(h[2])]

    write_glb(GLB_PATH, zup_to_yup(verts_local), tris)
    print("glb written:", GLB_PATH)

    tileset = {
        "asset": {"version": "1.1"},
        "geometricError": 100,
        "root": {
            "transform": [1, 0, 0, 0,
                          0, 1, 0, 0,
                          0, 0, 1, 0,
                          float(origin[0]), float(origin[1]), float(origin[2]), 1],
            "boundingVolume": {"box": box},
            "geometricError": 0,
            "refine": "REPLACE",
            "content": {"uri": "building.glb"},
        },
    }
    with open(TILESET_PATH, "w") as f:
        json.dump(tileset, f, indent=2)
    print("tileset written:", TILESET_PATH)

    # sanity check: the origin must land on Caserta
    t = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
    lon, lat, hgt = t.transform(*origin)
    print(f"origin geographic: lon={lon:.5f} lat={lat:.5f} "
          f"(expect ~14.358, ~41.049 -> Caserta)")