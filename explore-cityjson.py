"""
This file contains a first approach to cityJson files. At first, there is no need to import specialized libraries, json is enough.
Anyway, there is a cjio that is specifically designed to interact with this kind of objects
"""

# Without specific libraries

import json

path = r'D:\CMCC_REGEN4BE\sample_files\twobuildings.city.json'

with open(path) as myfile:
    cityModel = json.load(myfile)

print(cityModel.keys()) # read the first level, finding: type, version, metadata, CityObjects, vertices, transform
#print(json.dumps(cityModel, indent=2)) # print everything, can flood the terminal
#print(json.dumps(cityModel["type"], indent=2)) # CityJSON
#print(json.dumps(cityModel["version"], indent=2)) # 2.0
#print(json.dumps(cityModel["metadata"], indent=2)) # Prints "geographicalExtent", coordinates in [xmin, ymin, zmin, xmax, ymax, zmax]
# Original file has no declared CRS. We assume it's UTM, so we declare it
# and save another version — this is a guess, not knowledge.
#print(json.dumps(cityModel["CityObjects"], indent=2)) # Contains geometries
#print(json.dumps(cityModel["vertices"], indent=2)) # vertices
#print(json.dumps(cityModel["transform"], indent=2))

# With cjio: important, this is not a library. It's more similar to ogr2ogr and used to make operations on the model

# Original file han no declared ORS. We know it's UTM, so we provide it and save another version of the project.
from cjio import cityjson

out  = r'D:\CMCC_REGEN4BE\sample_files\twobuildings_georef.city.json'

# Print the reference system. it prints "None", so is necessary to adjust this. We asseume is a UTM
cm = cityjson.reader(file=open(path))
print("epsg before:", cm.get_epsg())

cm.set_epsg(32632)                      # ASSUMPTION — see note below
print("epsg after :", cm.get_epsg())    # 32632

with open(out, "w") as f:
    json.dump(cm.j, f, indent=2)

# The exported file has been verified in https://ninja.cityjson.org/ and it shows no anomalies.