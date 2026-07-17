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
| `explore-cityjson.py` | Prima ispezione di un file CityJSON: prima con la sola libreria `json`, poi con `cjio` per assegnare un CRS al file di esempio. |
| `twobuildings.city.json` | File CityJSON di esempio (versione 2.0), senza CRS dichiarato. |
| `twobuildings_georef.city.json` | Stesso file dopo l'assegnazione dell'EPSG con `cjio`. |


## Come partire

Serve Python 3.9+ (testato su 3.13).

```bash
git clone https://github.com/Aittam93/appunti-ifc-ifcopenshell.git
cd appunti-ifc-ifcopenshell

python -m venv venv-ifc

# Windows (PowerShell)
venv-ifc\Scripts\Activate.ps1
# macOS / Linux
source venv-ifc/bin/activate

pip install -r requirements.txt

python explore-ifc.py
python visualize-ifc.py
python explore-cityjson.py
```

Gli script leggono i file dalla stessa cartella, quindi non serve toccare i path.

> **Windows**: il comando è `python`, non `python3`. Se l'attivazione del venv dà
> *"l'esecuzione di script è disabilitata"*, lanciare prima
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

> **VS Code**: dopo aver creato il venv, selezionare l'interprete con
> `Ctrl+Shift+P` → *Python: Select Interpreter* → quello dentro `venv-ifc`.
> L'estensione Code Runner **ignora** questa impostazione e usa il Python di
> sistema: usare il Run nativo dell'estensione Python (`Ctrl+F5`).

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

## Visualizzare in Python

La tassellazione — da geometria parametrica a mesh triangolare — è fatta da `ifcopenshell.geom.create_shape()`, che risolve anche la catena di placement
annidati (`USE_WORLD_COORDS=True`). Trimesh riceve vertici e facce già calcolati e serve solo come contenitore e viewer interattivo (vedi visualize-ifc.py).

<img width="1271" height="792" alt="image" src="https://github.com/user-attachments/assets/dce8ad74-f40d-4d03-bc4f-3f996a48ae1f" />

## Visualizzatori Desktop per IFC : Blender + Bonsai

Puoi installare Blender e andare su Modifica > Preferenze > Get Extension per cercare e installare Bonsai.
L'installazione di Bonsai aggiunge funzioni specifiche a Blender come "New IFC Project" e "Load IFC Project".
Per testare, fai l'installazione e carica il sample file di questo repo.

<img width="1903" height="968" alt="image" src="https://github.com/user-attachments/assets/56f58ba5-dd30-46b6-87bf-41a620955abb" />

## CityJSON — il secondo formato della pipeline

CityJSON è il secondo formato che ci interessa nella pipeline verso la web map 3D.
A differenza di IFC è JSON puro e auto-descrittivo: si apre con la sola libreria
`json` e la struttura di primo livello è già leggibile (`type`, `version`,
`metadata`, `CityObjects`, `vertices`, `transform`).

Oltre a `json` esiste `cjio`, che però **non è una libreria** ma uno strumento a riga
di comando per operare sul modello, più vicino a `ogr2ogr` che a IfcOpenShell.

Il file di esempio non dichiarava alcun CRS (`get_epsg()` restituisce `None`). Le
coordinate sembrano UTM, quindi abbiamo assegnato con `cjio` l'EPSG 32632 e salvato
una seconda versione del file — **è un'assunzione, non un dato di partenza**. Il file
esportato è stato verificato su [ninja.cityjson.org](https://ninja.cityjson.org/) e non
mostra anomalie.

<img width="1918" height="910" alt="image" src="https://github.com/user-attachments/assets/3faadc7c-7cf7-4dcf-b703-0b99ea1e54a2" />


```bash
pip install cjio
python explore-cityjson.py
```
### CityJSON su QGIS via CityJSON loader plugin

In versioni precedenti a QGIS4 è possibile scaricare il plugin CityJSON loader (https://plugins.qgis.org/plugins/CityJSON-loader/).
Il plugin parsa il CityJSON in formato compatibile su QGIS.

<img width="1173" height="727" alt="image" src="https://github.com/user-attachments/assets/c55b6b14-56df-4d86-8548-c1e4ed0713be" />

Da notare come è strutturata la tabella degli attributi. Ci sono due due UID (Building_1 e Building_2) a cui fanno riferimento molte righe. Le righe sono
a loro volta classificata in surface_type (esempio: GroundSurface, WallSurface). Le colonne parents e children mantengono eventuali relazioni tra gli oggetti.
Notare anche che ogni feature è renderizzata come triangolo.
L'attributo "type" = building definisce il tipo di oggetto urbano. CityGML ne definisce anche altri (ad esempio relativi alle infrastrutture).

<img width="678" height="328" alt="image" src="https://github.com/user-attachments/assets/b6bf79a5-498b-43a8-9bf3-d7216720c586" />
<img width="777" height="507" alt="image" src="https://github.com/user-attachments/assets/d4d68063-73b5-477d-9d98-bac99f5c2187" />

<img width="617" height="506" alt="image" src="https://github.com/user-attachments/assets/8e84878d-5120-4324-92cf-40e0d8feed06" />


## Riferimenti

- [Documentazione IfcOpenShell](https://docs.ifcopenshell.org/)
- [Tutorial ufficiale](https://docs.ifcopenshell.org/ifcopenshell-python.html) — lo script segue questo percorso
- [Specifica IFC4 (buildingSMART)](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/)
- [Blender] (https://www.blender.org/)
- [Bonsai] (https://bonsaibim.org/)
