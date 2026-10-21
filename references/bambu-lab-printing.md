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
- **The gcode lands in `$PWD/bamboo_model/<date>/<time>#<job>#<plate>/Metadata/.<job>.0.gcode`** (hidden file): the folder is created **relative to the current directory**, so launch the slice from a dedicated working directory and look THERE, not in `/tmp`. The most recent: `ls -t "$PWD"/bamboo_model/*/*/Metadata/*.gcode | head -1` (glob over the hidden file — see the terminal-guard pitfall below).
- A **complete** gcode is recognizable by its end (`M104 S0` … `EXECUTABLE_BLOCK_END`): the CLI falls into SIGSEGV (return code −11) **after** it has finished writing, which distinguishes a valid harvest from a truncated file..

## BambuStudio 02.07.01.62: what actually works (reproducible findings)

- **The gcode lands under `$TMPDIR/bamboo_model/`, not under `$PWD`.** Here TMPDIR =
  `$TMPDIR` → look for `$TMPDIR/bamboo_model/<date>/<heure>#<pid>#<plate>/Metadata/`.
  A `find $PWD` finds nothing and makes it look like a failure: the `.0.gcode`/`.1.gcode` (one per plate,
  hidden name) is indeed there. The GL crash (`exit 139`, `Unable to init glew library`) occurs AFTER
  the write; `--export-3mf` succeeds even when thumbnail rendering fails.
  `libGLEW.so.2` was missing from `./osmesa-local/usr/lib/x86_64-linux-gnu` (only `.so.2.2` and
  `.so.2.2.0`): create the link `ln -sf libGLEW.so.2.2.0 libGLEW.so.2` — the rest (OSMesa, LLVM) is there.
- **`--load-filaments` is applied, `--load-settings` is not (and it requires profiles compatible
  with each other).** A `@BBL P1P` process with the `@BBL P1S` machine → `run 2993: process not compatible
  with printer.` (return code -17, exit 239). The `0.20mm Standard @BBL X1C` process accepts the P1S
  (`compatible_printers` lists "Bambu Lab P1S 0.4 nozzle"). Even with machine+process passed, the
  machine stays IGNORED: `printable_area = 0x0,200x0,200x200,0x200` and a "Cool Plate" bed in
  the header. `printable_area`/`curr_bed_type` are therefore purely internal to the CLI — fixing them by
  hand in the gcode is harmless (the printer follows the resolved M140/M190).
- **Verify the temperatures against a PETG job already printed on THIS machine**: list
  `ftps://…/Metadata/` (FTP keeps the old `.gcode.3mf`), re-download one and read its
  resolved `M104/M109/M190`. Here `Lampe_B_planche1_PETG.gcode.3mf` → **245 / 70**, exactly the
  values retained (its header, though, still said `Cool Plate`/`35`: the header is not the truth).
- **Set the temperatures by COPYING the JSON profiles** (never by post-processing alone): copy the
  PETG filament and put `cool_plate_temp`/`textured_plate_temp`/`hot_plate_temp` = 70,
  `nozzle_temperature` 245 / initial 240, `filament_density` 1.27; copy the process and put
  `skirt_loops = 0`, `brim_type = no_brim`, `wall_loops = 3`. Keys unknown to `from_user` are
  rejected (`invalid json type for from_user`): leave the key as-is. The CLI then reports
  itself `filament_type = PETG`, `filament_density = 1.27` (hence a weight in grams) and `M190 S70`.
- **Several STLs = several plates (and an object can disappear silently).** Three STLs
  passed at once gave 2 gcodes (base 205 layers, cover 24) and **the shell was missing** — without
  any error line in the log. The CLI therefore does not keep the provided positions. Recipe that
  works: concatenate the already-placed parts into **ONE single STL** (single object → single plate →
  a single gcode containing the three parts), each part being placed in a disjoint positive
  zone **that fits within 200×200** (the limit the CLI actually applies), outside the
  exclusion zone (`0..18` × `0..28`). A 210 mm object is refused (`Nothing to be sliced`).
- **No skirt.** With the plate placed flush against the edge (y_min ≈ 2 mm), the generated skirt goes off the
  plate (`G1 X50.9 Y-1.901`): `skirt_loops = 0` — the textured PEI plate holds these flat
  footprints without a skirt, and the CLI then has no toolpath off the plate.

## Multi-object slicing: pre-place EVERY STL (the CLI does not auto-arrange)

Dropping several STLs at once fails with `Found Object X partly inside, can not be sliced` / `Nothing to be sliced... no object is fully inside the print volume` when the meshes are exported centered on the origin (Blender keeps x/y/z straddling 0): the CLI lays every object at the plate origin, half outside, and never moves them. Fix BEFORE slicing, on copies in a scratch dir (never the project STLs):
- **Pre-rotate** each copy to its intended print orientation — the headless CLI cannot rotate; an enclosure half meant to print flat needs e.g. a +90°-about-X rotation (`z' = y`) so its flat face sits at z = 0 with cavities up.
- **Pre-translate** each into a DISJOINT zone of the positive quadrant (numpy-stl: `v += (zone_x - v.min_x, zone_y - v.min_y, -v.min_z)`), margins ~5 mm, all within the 256×256 plate.
- Verify bbox after transform (footprint × height) against the design's print-orientation notes before slicing.

## Reliable CLI binary & libs

The persistent AppImage extraction `~/Applications/squashfs-root/bin/bambu-studio` (run with `LD_LIBRARY_PATH=$PWD/bin`, its libs live in `bin/`) outlives the `/tmp/.mount_*` AppImage mounts and `/tmp/osmesa-local` — tmp cleanup breaks the mounts first (`libavcodec.so.61: cannot open shared object file`) and then the OSMesa rendering dir. `/tmp/osmesa-local` is ephemeral: re-create it (`apt-get download libosmesa6 libllvm20 libglew2.2` + `dpkg -x`) when the slice crashes at the GL/3mf step. The gcode is written before that crash either way — harvest `$PWD/bamboo_model/<date>/<time>#<job>#<plate>/Metadata/`.

## Honor "default filament" by copying a KNOWN-GOOD gcode's resolved temps

The CLI always slices with the user's stored config (usually PLA, bed 35 = cool-plate profile) whatever filament the user names. Instead of guessing vendor defaults, read the RESOLVED M-command temps from the user's last successful gcode of that filament on that machine: `grep -aE "M109 S[0-9]+|M190 S[0-9]+" <old-gcode>` (e.g. PETG 245° nozzle / 70° bed on Textured PEI). The `; config` header can show different values than the resolved commands (e.g. nozzle 255 in header, 245 actually run) — the resolved ones are what printed fine. Update temps in all three places: resolved M-commands, `; config` header block, `plate_1.json` first-layer fields. When writing a custom temp-rewrite alternation, cover `M104|M109|M140|M190` — `M14[09]` silently misses M190 (M19+0). **To rewrite a `; key = value` header line, match the value unconditionally** (`(; textured_plate_temp = )\S+`): a `(?!\d)` "to spare a number" skips exactly the numeric values, hence the ones to change, and the header keeps the old temperature while the gcode itself is correct. Rewriting only the resolved commands leaves the printer screen announcing a wrong temperature — check both.

## Read state and loaded material (MQTT, read-only)

- **Collect for at least 20 s.** A 9 s window returns empty fields (`gcode_state`, temperatures) and makes it look like the probe is broken: publish `{"pushing":{"sequence_id":"1","command":"pushall"}}` on `device/<serial>/request`, then read for ≥20 s keeping **only the frames that carry a `print` key** (the first ones are `upgrade_state`/`ipcam` fragments).
- **The report does NOT say which material is loaded if the spool has no RFID.** The AMS only reports tagged spools; a third-party spool on the external spool shows up empty (`tray_type` empty, `remain` 0 %) even though it is there. Do not conclude "nothing is loaded" from that — **ask the person**, which is also what avoids sending a PETG 245 °C gcode into a nozzle loaded with PLA.
- Useful fields: `gcode_state` (`IDLE`/`PREPARE`/`RUNNING`/`FINISH`), `mc_percent`, `subtask_name`, `nozzle_temper`/`bed_temper` and their targets, `ams.tray_now` (**255 = external spool**, 254 = nothing), `hms` — the codes appear there in **decimal** (`65543` = the "command verification failed" family).
- **`mc_percent` is a TIME progression, not a layer one** (seen 60 % at layer 44/204). To say where the print really stands, cite `layer_num`/`total_layer_num` and `mc_remaining_time`.
- **An HMS can disappear on its own**: re-read the state before reporting it as an ongoing fault.

## Prove WHICH file is printing (before re-slicing)

When the temperatures held by the printer are not those of the gcode, the order is: **prove the file's identity**, then blame the printer.

1. List `ftps://…/Metadata/` and compare **size + timestamp** of the file carrying the job name with the local `.gcode.3mf`. Same size to the byte and a timestamp of your own upload = this is indeed the file running; a more recent file = someone re-sent theirs.
2. Re-read the resolved commands **in the delivered file** (`Metadata/plate_1.gcode` inside the zip): `M140`/`M190`/`M104`/`M109` + the filament.
3. If the two agree, the divergence comes from the printer: it can hold its own setpoint (seen **250 °C / 80 °C** with a gcode at **245/70** on a PETG) without any other slicing being involved. Note it and say it as it is — both values stay within the filament range — rather than re-slicing; and record it, because the discrepancy comes back.

Never infer the file's identity from its name alone: the workstation and the printer can carry the same name for two different slicings.
- **An unacknowledged `FINISH` blocks remote start.** Read `gcode_state` before publishing: if it stayed on the previous job, tell the person — one tap on the screen puts it back to `IDLE` — and offer to start from the screen's library, which is not an MQTT command and always goes through.

## MQTT start: two DIFFERENT failure layers (diagnose in order)

1. **CONNACK return code 2 = your client's CONNECT packet is malformed, NOT the printer refusing auth.** The handcrafted stdlib client sends connect flags `0x02` (clean session only, no username/password bits) while still appending username+password to the payload → the server reads those bytes as a garbage next packet → identifier rejected. Fix: paho-mqtt (`pip install paho-mqtt`; `username_pw_set("bblp", code)`; `tls_insecure_set(True)`) connects rc=0 — or set flags `0xc2` in the handcrafted packet. Verify with paho before concluding the printer is blocking you.
2b. **Echo received (`project_file` with the right `param`), `gcode_state` stays `IDLE`, temperatures at 0 and an HMS appears: `attr` `83887360` (= `0500-0500`) + `code` `65543` (= `0001-0007`).** This is the command verification refusal (firmware rejecting an unsigned `project_file`) — the file is indeed uploaded and present in `Metadata/`. Do not retry in a loop: either start from the screen's library (the project appears there under its `subtask_name`), or enable developer mode. Check the file via the FTP LISTING before concluding anything about the upload.
   **Seen in practice (P1S, firmware 01.10.00.00 in cloud mode): remote start stays refused, and HE is the one with the solution.** Developer mode does not appear in his menu until "LAN only" is enabled (he does not want to touch it); the Bambu Studio GUI was opened and driven, but **he started it by hand before it could be of any use** — do not conclude that the GUI route is dead (it remains useful and is driven with the `gui-drive-x11` skill). What works: prepare → upload → verify via MQTT → announce "it's ready, start it from the screen". Do not insist on MQTT, and do not commit to installing packages for the `computer_use` virtual display without his explicit agreement.

2. **Command accepted (echoed on `report`) but the print never starts and the screen shows `HMS 0500-0500-0001-0007`** = "MQTT Command verification failed": firmware ≥ ~01.08.02 rejects unsigned third-party `project_file` commands. The on-screen file library is NOT an MQTT command → always works: start from the printer screen or Bambu Handy. For scripted/third-party starts enable **Developer Mode** on the printer (Settings → Network → LAN Mode → developer mode) which disables command verification. A leftover on-screen FINISH state also blocks remote start until acknowledged (reboot → IDLE).
3. **A `.gcode.3mf` dragged into Bambu Studio GUI says "the file does not contain data"** — that format is NOT openable by drag-and-drop (it is a print-job container for the printer, not a project). When the user needs to slice/start from the Studio GUI, hand them the **STL(s)** (pre-oriented to print orientation if the originals are not) and let Studio slice.
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
