import json

layer = iface.activeLayer()
feat = next(layer.getFeatures())     # se ce n'è più d'uno, selezionalo prima nella mappa

geom = feat.geometry()
ring = (geom.asMultiPolygon()[0] if geom.isMultipart() else geom.asPolygon())[0]

pts = [(p.x(), p.y()) for p in ring]
if pts[0] == pts[-1]:
    pts = pts[:-1]                   # il ring è chiuso, l'ultimo punto è ridondante

origin = (min(p[0] for p in pts), min(p[1] for p in pts))
local  = [(round(x - origin[0], 3), round(y - origin[1], 3)) for x, y in pts]

out = {
    "crs": "EPSG:32633",
    "origin_utm": [round(origin[0], 3), round(origin[1], 3)],
    "vertices_local_m": local,
    "height_m": 9.0,                 # da misurare/stimare: piani × 3
    "source": "OSM via QuickOSM, elementId 877880557"
}

with open(r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\data\footprint_cmcc.json", "w") as f:
    json.dump(out, f, indent=2)

print(json.dumps(out, indent=2))