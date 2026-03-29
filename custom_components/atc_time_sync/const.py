DOMAIN = "atc_time_sync"

import json
import pathlib
VERSION = json.loads(
    (pathlib.Path(__file__).parent / "manifest.json").read_text()
)["version"]

# BTHome v2
BTHOME_UUID16 = 0xFCD2
BTHOME_INFO_UNENCRYPTED = 0x40
BTHOME_ID_TIMESTAMP = 0x50
BTHOME_ID_PACKET_ID = 0x00

# BLE advertising
ADV_TYPE_SERVICE_DATA_16BIT = 0x16

# Defaults
DEFAULT_BROADCAST_INTERVAL = 10  # seconds between timestamp updates
