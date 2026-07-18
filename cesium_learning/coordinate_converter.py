from pyproj import Transformer

# WGS84 (lon/lat come da Maps) -> UTM 33N (Caserta è nel fuso 33)
t = Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True)
e, n = t.transform(14.358010460749957, 41.04950752828624)
print(f"Easting: {e:.3f}  Northing: {n:.3f}")