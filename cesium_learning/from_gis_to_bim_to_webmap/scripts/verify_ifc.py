import ifcopenshell

model = ifcopenshell.open(r"D:\CMCC_REGEN4BE\sample_files\cesium_learning\from_gis_to_bim_to_webmap\data\cmcc_footprint_v1.ifc")

crs = model.by_type("IfcProjectedCRS")
conv = model.by_type("IfcMapConversion")

print("ProjectedCRS:", crs)
print("MapConversion:", conv)

if conv:
    c = conv[0]
    print()
    print("Eastings:", c.Eastings)
    print("Northings:", c.Northings)
    print("Height:", c.OrthogonalHeight)