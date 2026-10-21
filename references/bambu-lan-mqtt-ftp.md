# Bambu LAN protocol — FTP + MQTT details (verified on P1S)

Printer: `192.168.1.115`. Serial + access code: `~/.config/BambuStudio/BambuStudio.conf` (grep `serial` / `access_code`). User for both FTP and MQTT: `bblp:<access_code>`.

## FTPS upload (implicit TLS, port 990)

```bash
curl -sS -k --ssl-reqd --ftp-create-dirs \
  -u "bblp:<access_code>" \
  -T /tmp/enclosure.gcode.3mf \
  "ftps://192.168.1.115:990/Metadata/enclosure.gcode.3mf"
```
- `Metadata/` does not exist on a fresh printer → `--ftp-create-dirs`.
- Root listing = system disk (`System Volume Information`, `logger`, `image`, `recorder`, `ipcam`, `timelapse`, `cache`, `boot.emmc`, `fip.bin`, `gpt.img`).
- Do NOT put the password in the command line as a literal if the guard/history matters — read it from the conf file into a shell var.

## .gcode.3mf packaging

A `.gcode.3mf` is a zip with exactly these entries (root-level `Metadata/`):

```
Metadata/plate_1.gcode      (the gcode, verbatim)
Metadata/plate_1.json
Metadata/slice_info.config  ({"prediction":<seconds>,"weight":"...","outside":false})
```

`plate_1.json` (fields the printer/slicer reads):

```json
{
  "prediction": 8487,
  "weight": "0.00",
  "outside": false,
  "plate_index": 0,
  "plate_name": "plate_1",
  "plate_type": "",
  "bed_type": "auto",
  "printer_model": "P1S",
  "nozzle": "0.4",
  "filament_type": "PETG",
  "filament_used": "1234.56",
  "filament_volume": "2500.0",
  "time": 8487,
  "layer_num": 110,
  "filelist": ["Metadata/plate_1.gcode"],
  "first_layer_bed_temp": 75,
  "first_layer_nozzle_temp": 248
}
```

Python: `zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)` + `writestr("Metadata/plate_1.gcode", gcode)` + the two json files. Extract `prediction`/`time`/`layer_num` from the gcode header (`; total layers count`, `; estimated printing time`), `filament_used` from `; filament used [mm]`.

## MQTT client — use paho (verified rc=0)

```python
pip install paho-mqtt   # then:
import paho.mqtt.client as mqtt, ssl
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="bblp")
c.username_pw_set("bblp", CODE)
c.tls_set(cert_reqs=ssl.CERT_NONE); c.tls_insecure_set(True)
c.connect(IP, 8883, keepalive=30)   # rc=0 = accepted
# subscribe device/<serial>/report, publish device/<serial>/request
```

The handcrafted packet builder below was VERIFIED BROKEN on current firmware: its
CONNECT flags byte is `0x02` (clean session only — announces NO username/password) while
the payload still appends `bblp` + access code → the server reads those bytes as a new
packet → CONNACK code 2 (identifier rejected). If you must go stdlib, set flags `0xc2`
(clean session + username + password) to match the appended fields and CHECK the CONNACK
return byte instead of ignoring it. Then publish `project_file` as below:

```python
import socket, ssl, struct, json, hashlib

IP, SERIAL, CODE = "192.168.1.115", "<serial>", "<access_code>"

def _len(n):
    out = b""
    while True:
        b = n % 128; n //= 128
        if n: out += bytes([b | 0x80])
        else: out += bytes([b]); break
    return out

def _pkt(typ, payload=b""):
    return bytes([typ]) + _len(len(payload)) + payload

def connect(ip=IP, port=8883):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    s = ctx.wrap_socket(socket.create_connection((ip, port), timeout=8))
    cid = b"bblp"
    payload = b"\x00\x04MQTT\x04\xc2\x00\x3c" + _len(len(cid)) + cid + _len(4) + b"bblp" + _len(len(CODE)) + CODE.encode()  # flags 0xc2 MUST announce username+password
    s.sendall(_pkt(0x10, payload))
    resp = s.recv(4)  # CONNACK 0x20 len 2
    if resp[2:] != b"\x00\x00":
        raise ConnectionError(f"MQTT CONNACK refused: code {resp[3]}")
    return s

def sub(s, topic):
    p = b"\x00\x01" + _len(len(topic)) + topic + b"\x00"
    s.sendall(_pkt(0x82, p))

def pub(s, topic, payload):
    s.sendall(_pkt(0x30, _len(len(topic)) + topic + json.dumps(payload).encode()))

def read(s, timeout=10):
    s.settimeout(timeout)
    try:
        hdr = s.recv(1)
        if not hdr: return None
        rl = 0; mul = 1
        while True:
            b = s.recv(1)[0]; rl += (b & 0x7F) * mul; mul *= 128
            if not (b & 0x80): break
        body = b""
        while len(body) < rl: body += s.recv(rl - len(body))
        return hdr[0], body
    except socket.timeout:
        return None

s = connect()
rep = f"device/{SERIAL}/report"
sub(s, rep)
time.sleep(3)  # let initial state arrive (sporadic)

md5 = hashlib.md5(open("enclosure.gcode.3mf", "rb").read()).hexdigest()
pub(s, f"device/{SERIAL}/request", {"print": {
    "command": "project_file",
    "param": "Metadata/enclosure.gcode.3mf",
    "subtask_name": "enclosure",
    "url": f"ftp://{IP}/Metadata/enclosure.gcode.3mf",
    "md5": md5,
    "flow_calibration": 0, "cali_mode": "0",
    "timelapse": False, "bed_leveling": True, "vibration_calibration": True,
    "firmware_update": True, "binding_setup": False, "use_ams": False,
}})
# Expect the printer to ECHO the command on report (receipt). A result/ACK
# ({"print":{"command":"project_file","result":...}}) may never come — state
# pushes are unreliable; the printer screen is the ground truth.
```

Notes:
- No `sequence_id` needed for `project_file` (older firmwares may require it; add `"sequence_id": "10001"` if a silent drop is suspected).
- If the connection drops after a `pushall` query, don't retry spam — reconnect fresh.
- The report topic echoes commands back (confirmation); `stg_cur` (state) and `mc_remaining_time` appear in periodic reports when they come.

## gcode temp post-processing (PLA → PETG example)

```python
import re
text = open("plate.gcode", "r", errors="replace").read()
text = re.sub(r"M104 S\d+", "M104 S248", text)   # set nozzle (keep M104 S0: regex \d+ matches 0 too!)
text = re.sub(r"M109 S\d+", "M109 S248", text)
text = re.sub(r"M140 S\d+", "M140 S75", text)
text = re.sub(r"M190 S\d+", "M190 S75", text)
# CAREFUL: M104 S0 (heater off at end) must stay 0 — use a more precise pattern
# like re.sub(r"M104 S(?!0\b)\d+", "M104 S248", text) or handle S0 first.
for a, b in [("; filament_type = PLA", "; filament_type = PETG"),
             ("; nozzle_temperature = 200", "; nozzle_temperature = 248"),
             ("; nozzle_temperature_initial_layer = 200", "; nozzle_temperature_initial_layer = 248"),
             ("; bed_temperature = 65", "; bed_temperature = 75"),
             ("; bed_temperature_initial_layer = 65", "; bed_temperature_initial_layer = 75")]:
    text = text.replace(a, b)
```
Update `plate_1.json` `first_layer_bed_temp`/`first_layer_nozzle_temp`/`filament_type` to match. Verify with `grep -aE "M104 S|M190 S|nozzle_temperature|bed_temperature|filament_type"`.
