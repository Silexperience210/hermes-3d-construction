---
name: bambu-lab-printing
description: Use when slicing or sending prints to a Bambu Lab printer.
---

# Bambu Lab printing (P1S @ 192.168.1.115) — headless slice → LAN send

Full pipeline to get a part from STL onto the printer without the GUI. Verified on a **P1S** (LAN mode) with BambuStudio AppImage on a headless box (no GPU, no sudo).

**Printer identity**: IP `192.168.1.115`, MQTT **8883** (LAN TLS), FTPS **990** (implicit). Serial + access code (LAN password) live in `~/.config/BambuStudio/BambuStudio.conf` — read them from there, never hardcode. The file is JSON and stores the code **keyed by the serial**: `conf["access_code"]` is a dict `{"<serial>": "<code>"}`, so take both at once with `SERIAL, CODE = next(iter(conf["access_code"].items()))`. Grepping for a `serial` field finds nothing (it exists only as that key) and costs a debugging round-trip. FTP/MQTT user is always `bblp:<access_code>`.

## The chain (in order)

1. **Slice** with the BambuStudio CLI (AppImage extracted, see below).
2. **Verify the gcode header** — temps, filament, layer count. The CLI's preset loading is BROKEN (`--load-filaments` is silently ignored → it slices with the user's stored config, often PLA), so **post-process the gcode** when the user wants different temps/filament (e.g. PETG 248°/75°): replace `M104 S\d+`/`M109 S\d+` → nozzle temp (KEEP `M104 S0` shutdown lines!), `M140 S\d+`/`M190 S\d+` → bed temp, update the config block (`; filament_type`, `; nozzle_temperature`, `; bed_temperature`, `; *_initial_layer`), and the `plate_1.json` first-layer temps.
3. **Package** the gcode as a `.gcode.3mf` (zip with `Metadata/plate_1.gcode` + `Metadata/plate_1.json` + `Metadata/slice_info.config`) — the printer's `project_file` command consumes this format.
4. **Upload** via FTPS implicit — but **never pass the access code in argv**: `-u bblp:<code>` is visible in `ps` to every user of the machine. Write a mode-600 curl config instead and let curl read it:
   ```bash
   printf 'user = "bblp:%s"\n' "$CODE" > /tmp/curl-cfg && chmod 600 /tmp/curl-cfg
   curl -sS -k --ssl-reqd --ftp-create-dirs -K /tmp/curl-cfg -T <file>.gcode.3mf \
     "ftps://192.168.1.115:990/Metadata/<name>.gcode.3mf"; rm -f /tmp/curl-cfg
   ```
   The `Metadata/` dir does NOT exist on the printer; `--ftp-create-dirs` creates it. The FTP root is the printer's system disk (boot.emmc, fip.bin, cache/, image/, Metadata after creation). **A zero exit code does not prove the file landed — list `ftps://…/Metadata/` (same `-K` config) and check the name appears.** The uploaded file also survives a printer reboot.
5. **Start** the print via MQTT: connect TLS to `192.168.1.115:8883` (no cert verify), subscribe `device/<serial>/report`, publish to `device/<serial>/request`:
   `{"print":{"command":"project_file","param":"Metadata/<name>.gcode.3mf","subtask_name":"<name>","url":"ftp://192.168.1.115/Metadata/<name>.gcode.3mf","md5":"<md5 of file>","flow_calibration":0,"cali_mode":"0","timelapse":false,"bed_leveling":true,"vibration_calibration":true,"firmware_update":true,"binding_setup":false,"use_ams":false}}`
   The printer echoes the command on `report` (confirmation of receipt). ACK/state reports are sporadic — if no ACK, don't loop forever; tell the user to check the printer screen. A minimal MQTT 3.1.1 client can be handcrafted over `ssl` + `socket` (no paho needed): full code in `references/bambu-lan-mqtt-ftp.md`.

## Headless BambuStudio CLI details

- **FUSE is blocked** in this sandbox → `./BambuStudio.AppImage --appimage-extract` → binary at `/tmp/squashfs-root/bin/bambu-studio` (a PrusaSlicer-derived CLI).
- Needs **libOSMesa + libLLVM.so.20 + libGLEW** for offline rendering: `apt-get download libosmesa6 libllvm20 libglew2.2` + `dpkg -x` into `/tmp/osmesa-local`, then `LD_LIBRARY_PATH="$PWD/bin:/tmp/osmesa-local/usr/lib/x86_64-linux-gnu"`.
- Slice command: `env LD_LIBRARY_PATH=... ./bin/bambu-studio --slice 0 --export-3mf /tmp/out.3mf <file.stl>` — `--slice` REQUIRES a value (0 = all plates); `--load-settings`/`--load-filaments` → "setup params error" or silently ignored.
- **The GL context fails at the 3mf packaging step (exit 2) but the gcode IS written before the crash.** Always harvest the gcode after a failed run.
- **Le gcode atterrit dans `$PWD/bamboo_model/<date>/<time>#<job>#<plate>/Metadata/.<job>.0.gcode`** (fichier caché) : le dossier est créé **relativement au répertoire courant**, donc lancer le slice depuis un dossier de travail dédié et regarder LÀ, pas dans `/tmp`. Le plus récent : `ls -t "$PWD"/bamboo_model/*/*/Metadata/*.gcode | head -1` (glob sur le fichier caché — voir le piège du garde-fou de terminal plus bas).
- Un gcode **complet** se reconnaît à sa fin (`M104 S0` … `EXECUTABLE_BLOCK_END`) : le CLI tombe en SIGSEGV (code retour −11) **après** avoir fini d'écrire, ce qui permet de distinguer une récolte valable d'un fichier tronqué..

## BambuStudio 02.07.01.62 : ce qui marche réellement (constats reproductibles)

- **Le gcode atterrit sous `$TMPDIR/bamboo_model/`, pas sous `$PWD`.** Ici TMPDIR =
  `$TMPDIR` → chercher `$TMPDIR/bamboo_model/<date>/<heure>#<pid>#<plate>/Metadata/`.
  Un `find $PWD` ne trouve rien et fait croire à un échec : le `.0.gcode`/`.1.gcode` (un par plateau,
  nom caché) y est bien. Le crash GL (`exit 139`, `Unable to init glew library`) survient APRÈS
  l'écriture ; `--export-3mf` réussit même quand le rendu de vignette échoue.
  `libGLEW.so.2` manquait dans `./osmesa-local/usr/lib/x86_64-linux-gnu` (seuls `.so.2.2` et
  `.so.2.2.0`) : créer le lien `ln -sf libGLEW.so.2.2.0 libGLEW.so.2` — le reste (OSMesa, LLVM) y est.
- **`--load-filaments` est appliqué, `--load-settings` non (et il exige des profils compatibles
  entre eux).** Un process `@BBL P1P` avec la machine `@BBL P1S` → `run 2993: process not compatible
  with printer.` (code retour -17, exit 239). Le process `0.20mm Standard @BBL X1C` accepte la P1S
  (`compatible_printers` liste « Bambu Lab P1S 0.4 nozzle »). Même avec machine+process passés, la
  machine reste IGNORÉE : `printable_area = 0x0,200x0,200x200,0x200` et plateau « Cool Plate » dans
  l'en-tête. `printable_area`/`curr_bed_type` sont donc purement internes au CLI — les corriger à la
  main dans le gcode est sans risque (l'imprimante suit les M140/M190 résolus).
- **Vérifier les températures contre un job PETG déjà imprimé sur CETTE machine** : lister
  `ftps://…/Metadata/` (le FTP garde les anciens `.gcode.3mf`), en retélécharger un et lire ses
  `M104/M109/M190` résolus. Ici `Lampe_B_planche1_PETG.gcode.3mf` → **245 / 70**, exactement les
  valeurs retenues (son en-tête, lui, disait encore `Cool Plate`/`35` : l'en-tête n'est pas la vérité).
- **Fixer les températures par COPIE des profils JSON** (jamais en post-traitement seul) : copier le
  filament PETG et y poser `cool_plate_temp`/`textured_plate_temp`/`hot_plate_temp` = 70,
  `nozzle_temperature` 245 / initiale 240, `filament_density` 1.27 ; copier le process et y poser
  `skirt_loops = 0`, `brim_type = no_brim`, `wall_loops = 3`. Les clés inconnues de `from_user` sont
  refusées (`invalid json type for from_user`) : laisser la clé telle quelle. Le CLI reporte alors
  lui-même `filament_type = PETG`, `filament_density = 1.27` (donc un poids en grammes) et `M190 S70`.
- **Plusieurs STL = plusieurs plateaux (et un objet peut disparaître en silence).** Trois STL
  passés d'un coup ont donné 2 gcodes (pied 205 couches, capot 24) et **la coque manquait** — sans
  aucune ligne d'erreur dans le log. Le CLI ne garde donc pas les positions fournies. Recette qui
  marche : concaténer les pièces déjà placées dans **UN seul STL** (objet unique → un seul plateau →
  un seul gcode contenant les trois pièces), chaque pièce étant posée dans une zone positive
  disjointe **qui tient dans 200×200** (la limite que le CLI applique vraiment), hors zone
  d'exclusion (`0..18` × `0..28`). Un objet de 210 mm est refusé (`Nothing to be sliced`).
- **Pas de jupe.** Avec la plaque posée au ras du bord (y_min ≈ 2 mm), la jupe générée sort du
  plateau (`G1 X50.9 Y-1.901`) : `skirt_loops = 0` — le plateau PEI texturé tient ces empreintes
  plates sans jupe, et le CLI n'a alors plus aucune trajectoire hors plateau.

## Multi-object slicing: pre-place EVERY STL (the CLI does not auto-arrange)

Dropping several STLs at once fails with `Found Object X partly inside, can not be sliced` / `Nothing to be sliced... no object is fully inside the print volume` when the meshes are exported centered on the origin (Blender keeps x/y/z straddling 0): the CLI lays every object at the plate origin, half outside, and never moves them. Fix BEFORE slicing, on copies in a scratch dir (never the project STLs):
- **Pre-rotate** each copy to its intended print orientation — the headless CLI cannot rotate; an enclosure half meant to print flat needs e.g. a +90°-about-X rotation (`z' = y`) so its flat face sits at z = 0 with cavities up.
- **Pre-translate** each into a DISJOINT zone of the positive quadrant (numpy-stl: `v += (zone_x - v.min_x, zone_y - v.min_y, -v.min_z)`), margins ~5 mm, all within the 256×256 plate.
- Verify bbox after transform (footprint × height) against the design's print-orientation notes before slicing.

## Reliable CLI binary & libs

The persistent AppImage extraction `~/Applications/squashfs-root/bin/bambu-studio` (run with `LD_LIBRARY_PATH=$PWD/bin`, its libs live in `bin/`) outlives the `/tmp/.mount_*` AppImage mounts and `/tmp/osmesa-local` — tmp cleanup breaks the mounts first (`libavcodec.so.61: cannot open shared object file`) and then the OSMesa rendering dir. `/tmp/osmesa-local` is ephemeral: re-create it (`apt-get download libosmesa6 libllvm20 libglew2.2` + `dpkg -x`) when the slice crashes at the GL/3mf step. The gcode is written before that crash either way — harvest `$PWD/bamboo_model/<date>/<time>#<job>#<plate>/Metadata/`.

## Honor « default filament » by copying a KNOWN-GOOD gcode's resolved temps

The CLI always slices with the user's stored config (usually PLA, bed 35 = cool-plate profile) whatever filament the user names. Instead of guessing vendor defaults, read the RESOLVED M-command temps from the user's last successful gcode of that filament on that machine: `grep -aE "M109 S[0-9]+|M190 S[0-9]+" <old-gcode>` (e.g. PETG 245° nozzle / 70° bed on Textured PEI). The `; config` header can show different values than the resolved commands (e.g. nozzle 255 in header, 245 actually run) — the resolved ones are what printed fine. Update temps in all three places: resolved M-commands, `; config` header block, `plate_1.json` first-layer fields. When writing a custom temp-rewrite alternation, cover `M104|M109|M140|M190` — `M14[09]` silently misses M190 (M19+0). **Pour réécrire une ligne d'en-tête `; clé = valeur`, matcher la valeur sans condition** (`(; textured_plate_temp = )\S+`) : un `(?!\d)` « pour épargner un nombre » saute exactement les valeurs numériques, donc celles à changer, et l'en-tête garde l'ancienne température pendant que le gcode, lui, est juste. Ne réécrire que les commandes résolues laisse l'écran de l'imprimante annoncer une température fausse — vérifier les deux.

## Lire l'état et la matière chargée (MQTT, lecture seule)

- **Collecter au moins 20 s.** Une fenêtre de 9 s rend des champs vides (`gcode_state`, températures) et fait croire que la sonde est cassée : publier `{"pushing":{"sequence_id":"1","command":"pushall"}}` sur `device/<serial>/request`, puis lire ≥20 s en **ne gardant que les trames qui portent une clé `print`** (les premières sont des fragments `upgrade_state`/`ipcam`).
- **Le rapport ne dit PAS quelle matière est chargée si la bobine n'a pas de RFID.** L'AMS ne remonte que les bobines étiquetées ; une bobine tierce sur la bobine externe apparaît vide (`tray_type` vide, `remain` 0 %) alors qu'elle est là. Ne pas en conclure « rien n'est chargé » — **demander à la personne**, c'est aussi ce qui évite d'envoyer un gcode PETG 245 °C dans une buse chargée en PLA.
- Champs utiles : `gcode_state` (`IDLE`/`PREPARE`/`RUNNING`/`FINISH`), `mc_percent`, `subtask_name`, `nozzle_temper`/`bed_temper` et leurs cibles, `ams.tray_now` (**255 = bobine externe**, 254 = rien), `hms` — les codes y apparaissent en **décimal** (`65543` = la famille de « command verification failed »).
- **`mc_percent` est une progression de TEMPS, pas de couches** (vu 60 % à la couche 44/204). Pour dire où en est vraiment l'impression, citer `layer_num`/`total_layer_num` et `mc_remaining_time`.
- **Un HMS peut disparaître de lui-même** : relire l'état avant de le rapporter comme un défaut en cours.

## Prouver QUEL fichier imprime (avant de refaire un tranchage)

Quand les températures tenues par l'imprimante ne sont pas celles du gcode, l'ordre est : **prouver l'identité du fichier**, puis accuser l'imprimante.

1. Lister `ftps://…/Metadata/` et comparer **taille + horodatage** du fichier qui porte le nom du job avec le `.gcode.3mf` local. Même taille à l'octet et horodatage de son propre envoi = c'est bien ce fichier qui tourne ; un fichier plus récent = quelqu'un a renvoyé le sien.
2. Relire les commandes résolues **dans le fichier livré** (`Metadata/plate_1.gcode` à l'intérieur du zip) : `M140`/`M190`/`M104`/`M109` + le fil.
3. Si les deux concordent, la divergence vient de l'imprimante : elle peut tenir sa propre consigne (vu **250 °C / 80 °C** avec un gcode à **245/70** sur une PETG) sans qu'aucun autre tranchage ne soit en cause. Le constater et le dire tel quel — les deux valeurs restent dans la plage du filament — plutôt que de retrancher ; et le consigner, parce que l'écart revient.

Ne jamais déduire l'identité du fichier de son seul nom : le poste et l'imprimante peuvent porter le même nom pour deux tranchages différents.
- **Un `FINISH` non acquitté bloque le démarrage à distance.** Lire `gcode_state` avant de publier : si elle est restée sur le travail précédent, le dire à la personne — un appui sur l'écran la remet en `IDLE` — et lui proposer de lancer depuis la bibliothèque de l'écran, qui n'est pas une commande MQTT et passe toujours.

## MQTT start: two DIFFERENT failure layers (diagnose in order)

1. **CONNACK return code 2 = your client's CONNECT packet is malformed, NOT the printer refusing auth.** The handcrafted stdlib client sends connect flags `0x02` (clean session only, no username/password bits) while still appending username+password to the payload → the server reads those bytes as a garbage next packet → identifier rejected. Fix: paho-mqtt (`pip install paho-mqtt`; `username_pw_set("bblp", code)`; `tls_insecure_set(True)`) connects rc=0 — or set flags `0xc2` in the handcrafted packet. Verify with paho before concluding the printer is blocking you.
2b. **Écho reçu (`project_file` avec le bon `param`), `gcode_state` reste `IDLE`, températures à 0 et un HMS apparaît : `attr` `83887360` (= `0500-0500`) + `code` `65543` (= `0001-0007`).** C'est le refus de vérification de commande (firmware qui rejette un `project_file` non signé) — le fichier est bien télversé et présent dans `Metadata/`. Ne pas réessayer en boucle : soit démarrer depuis la bibliothèque de l'écran (le projet y apparaît sous son `subtask_name`), soit activer le mode développeur. Vérifier le fichier par la LISTE FTP avant de conclure quoi que ce soit sur le téléversement.
   **Seen in practice (P1S, firmware 01.10.00.00 en mode cloud) : le démarrage à distance reste refusé, et c'est LUI qui a la solution.** Le mode développeur n'apparaît pas dans son menu tant que « LAN uniquement » n'est pas activé (il ne veut pas y toucher) ; la GUI de Bambu Studio a été ouverte et pilotée, mais **c'est lui qui a lancé à la main avant qu'elle serve** — ne pas en conclure que la route GUI est morte (elle reste utile et se pilote avec le skill `gui-drive-x11`). Ce qui marche : préparer → téléverser → vérifier par MQTT → annoncer « c'est prêt, lance depuis l'écran ». Ne pas insister sur MQTT, et ne pas engager d'installation de paquets pour l'écran virtuel de `computer_use` sans son accord explicite.

2. **Command accepted (echoed on `report`) but the print never starts and the screen shows `HMS 0500-0500-0001-0007`** = « MQTT Command verification failed »: firmware ≥ ~01.08.02 rejects unsigned third-party `project_file` commands. The on-screen file library is NOT an MQTT command → always works: start from the printer screen or Bambu Handy. For scripted/third-party starts enable **Developer Mode** on the printer (Settings → Network → LAN Mode → developer mode) which disables command verification. A leftover on-screen FINISH state also blocks remote start until acknowledged (reboot → IDLE).
3. **A `.gcode.3mf` dragged into Bambu Studio GUI says « le fichier ne contient pas de data »** — that format is NOT openable by drag-and-drop (it is a print-job container for the printer, not a project). When the user needs to slice/start from the Studio GUI, hand them the **STL(s)** (pre-oriented to print orientation if the originals are not) and let Studio slice.
4. **The uploaded file SURVIVES a printer reboot** (stays in `Metadata/`) — if the on-screen library does not show it, check FTP first before re-uploading.

## Pitfalls (all hit on this machine)

- **The terminal guard crashes ("embedded null byte") on commands referencing the hidden `.162*.gcode` path** — the guard tries to read it as a referenced script and hits NUL bytes (binary thumbnail blobs in the gcode). Workarounds: `cp "$(ls -t ... | head -1)" /tmp/plate.gcode` FIRST (glob works), or do everything in `execute_code` with pure Python (zipfile/json/subprocess) and never mention the hidden path in a shell command.
- **`pkill -f ser_cap.py` kills the calling shell** — the pattern matches its own command line. Use `pgrep -f` to list PIDs first, then kill by number.
- The gcode's temps live in BOTH the `M104/M140/M109/M190` startup lines AND the `; config` header block AND `plate_1.json` — all three must be updated or the printer screen / slicer shows stale values.
- `use_ams:false` in `project_file` = external spool (correct for generic PETG on the back spool); `true` = filament from the AMS.
- Bed/nozzle temp verification: `grep -aE "nozzle_temperature|bed_temperature|filament_type|M104 S|M190 S" <gcode>` (binary-safe `-a`).

## Verification

- Header check: `nozzle_temperature` / `M104 S248` / `M190 S75` / `filament_type = PETG` present.
- FTP listing shows the file under `Metadata/`.
- MQTT: the printer echoes the `project_file` command on `device/<serial>/report` → receipt confirmed.
- Final check is the printer screen (state reports are unreliable — if ambiguous, tell the user to look).

Full copy-pasteable MQTT client (pure stdlib), `plate_1.json` template, and packaging script: `references/bambu-lan-mqtt-ftp.md`.
