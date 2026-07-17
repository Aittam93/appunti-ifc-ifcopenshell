# Appunti IFC + IfcOpenShell + altro

Primi appunti su **come accedere e usare i file IFC** da Python con la libreria
[IfcOpenShell](https://ifcopenshell.org/). Materiale di partenza per chi non ha mai
aperto un `.ifc` a livello di dati.

L'obiettivo del repo è studiare la pipeline che porta da un file IFC a una web map 3D.

## Cosa c'è qui

| File | Contenuto |
|---|---|
| `explore-ifc.py` | Script commentato passo passo: apertura del modello, lettura entità, attributi, property set, relazioni inverse, traverse, e (commentate) le operazioni di scrittura. |
| `visualize-ifc.py` | Converte la geometria parametrica degli `IfcProduct` in mesh triangolari con `ifcopenshell.geom` e le mostra in una finestra interattiva con trimesh. |
| `Building-Architecture.ifc` | File IFC di esempio (schema IFC4) usato dallo script. |

## Come partire

Serve Python 3.9+.

```bash
git clone https://github.com/Aittam93/appunti-ifc-ifcopenshell.git
cd appunti-ifc-ifcopenshell

python -m venv venv-ifc
# Windows
venv-ifc\Scripts\activate
# macOS / Linux
source venv-ifc/bin/activate

pip install ifcopenshell trimesh numpy

python explore-ifc.py
python visualize-ifc.py
```

Lo script legge il file IFC dalla stessa cartella, quindi non serve toccare i path.

## L'idea chiave da portarsi a casa

Un file IFC è una **lista piatta di entità numerate** (`#N=ENTITÀ(...)`), non un formato
nidificato come JSON o XML. Le relazioni tra righe sono espresse tramite riferimenti
numerici (`#245`, `#1`) e sono interpretabili solo grazie allo schema EXPRESS esterno.
Concettualmente è più vicino al dump di un database relazionale (dati piatti + schema
esterno) che a un documento auto-descrittivo.

Esempio dal file di esempio:

```
#311=IFCSURFACESTYLERENDERING(#312,0.,$,$,$,$,$,$,.NOTDEFINED.);
#312=IFCCOLOURRGB($,1.,1.,1.);
```

`IFCSURFACESTYLERENDERING` referenzia `IFCCOLOURRGB`. In `IFCCOLOURRGB` il `$` indica
`Name` nullo, mentre R=1, G=1, B=1 sono normalizzati: il muro è completamente bianco.

## Visualizzare in Python con trimesh

La libreria trimesh si occupa di generare le mesh triangolari necessarie a renderizzare l'oggetto ifc (vedi visualize-ifc.py)

<img width="1271" height="792" alt="image" src="https://github.com/user-attachments/assets/dce8ad74-f40d-4d03-bc4f-3f996a48ae1f" />

## Visualizzatori Desktop per IFC : Blender + Bonsai

Puoi installare Blender e andare su Modifica > Preferenze > Get Extension per cercare e installare Bonsai.
L'installazione di Bonsai aggiunge funzioni specifiche a Blender come "New IFC Project" e "Load IFC Project".
Per testare, fai l'installazione e carica il sample file di questo repo.

<img width="1903" height="968" alt="image" src="https://github.com/user-attachments/assets/56f58ba5-dd30-46b6-87bf-41a620955abb" />

## Riferimenti

- [Documentazione IfcOpenShell](https://docs.ifcopenshell.org/)
- [Tutorial ufficiale](https://docs.ifcopenshell.org/ifcopenshell-python.html) — lo script segue questo percorso
- [Specifica IFC4 (buildingSMART)](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/)
- [Blender] (https://www.blender.org/)
- [Bonsai] (https://bonsaibim.org/)
