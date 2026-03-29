# ATC Thermometer Time Sync

Home Assistant integration for automatic time synchronization with [ATC_MiThermometer](https://github.com/pvvx/ATC_MiThermometer) devices.

## How it works

Broadcasts a BTHome v2 beacon containing the current UTC timestamp via your HA Bluetooth adapter. ATC thermometers with `SERVICE_SCANTIM` enabled will periodically scan for this beacon and update their internal clocks — no BLE connection or button press needed.

## Requirements

- Home Assistant with local Bluetooth adapter
- ATC_MiThermometer firmware with `SERVICE_SCANTIM` enabled
- `hcitool` available on the HA host (included in most Linux BLE setups)

## Installation

### HACS (recommended)

1. Open HACS → three-dot menu (top right) → **Custom repositories**
2. URL: `https://github.com/chinaboard/ha-atc-time-sync`
3. Category: **Integration**
4. Click **Add** → find "ATC Thermometer Time Sync" → **Install**
5. Restart Home Assistant

### Manual

Copy `custom_components/atc_time_sync/` to your HA `custom_components/` directory and restart.

## Setup

1. Settings → Integrations → **Add Integration** → search "ATC Time Sync"
2. Select your Bluetooth adapter (default: `hci0`)
3. Done — beacon starts broadcasting automatically

## Thermometer Configuration

After flashing firmware with `SERVICE_SCANTIM` enabled:

1. Press the device button → connect via [TelinkMiFlasher](https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html)
2. Set **Scan target MAC** = your HA Bluetooth adapter MAC
3. Set **Scan interval** (e.g. 3600 = hourly)
