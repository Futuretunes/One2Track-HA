# One2Track GPS — Home Assistant Integration

Custom [Home Assistant](https://www.home-assistant.io/) integration for [One2Track](https://www.one2trackgps.com/) GPS watches. Built from scratch with a focus on robust session management and reliability.

## Features

### Device Tracker
- GPS position on the Home Assistant map
- Dynamic icon based on location type (GPS / WiFi / Cell tower)
- GPS accuracy from the watch or estimated by positioning method
- Stale location detection — marks unavailable if no update in 30 minutes
- Address, location type, heading, and accuracy as attributes

### Sensors
| Sensor | Unit | Description |
|---|---|---|
| Battery | % | Watch battery level |
| Signal strength | % | Cellular signal strength |
| Satellites | count | Number of GPS satellites |
| Speed | km/h | Current speed |
| Altitude | m | Current altitude |
| Steps | count | Step counter (daily total) |
| SIM balance | EUR | SIM card balance |
| Last communication | timestamp | Last time the watch contacted the server |
| Last location update | timestamp | Last GPS fix |
| Location type | — | GPS, WiFi, or LBS |
| Status | — | Online status |

### Binary Sensors
| Sensor | Description |
|---|---|
| Fall detected | Tumble/fall detection alert |
| Geofence (per zone) | Whether the watch is inside a geofence configured on One2Track |

### Buttons
| Button | Description |
|---|---|
| Refresh location | Request an active GPS fix (~2 min) |
| Find device | Ring the watch |
| Remote shutdown | Power off the watch (disabled by default) |

### Select
| Select | Description |
|---|---|
| GPS interval | Set tracking interval (10s / 5min / 10min) |
| Profile mode | Sound / Vibrate / Silent |

### Switch
| Switch | Description |
|---|---|
| Step counter | Enable/disable step counting |

### Text
| Entity | Description |
|---|---|
| SOS number | Configure the emergency SOS number on the watch |

### Services
| Service | Description |
|---|---|
| `one2track.send_message` | Send a text message to a watch |
| `one2track.set_phonebook` | Set phonebook entries on a watch |
| `one2track.set_quiet_times` | Configure quiet time periods |

### Diagnostics
Full diagnostic dump available via **Settings → Devices → One2Track → Download Diagnostics**. Sensitive data (location, names, phone numbers) is automatically redacted.

> **Note:** Select, switch, button, and text entities only appear if the watch model supports the corresponding command. Capabilities are auto-detected per device.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) → **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Search for "One2Track GPS" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/one2track/` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "One2Track GPS"
3. Enter your One2Track account email and password
4. Your watches will appear as devices with all supported entities

### Options

After setup, click **Configure** on the integration to change:

- **Update interval** — How often to poll for new data (30–300 seconds, default: 60)

## How it works

One2Track does not offer an official API. This integration communicates with the One2Track web portal (`www.one2trackgps.com`) using the same session-based authentication as the web interface.

### Session management

The integration uses a dedicated HTTP session with its own cookie jar and implements:

- **Automatic re-authentication** when the session expires
- **Lock-guarded re-auth** to prevent multiple concurrent login attempts
- **Fresh CSRF tokens** before every write operation
- **Content-type validation** to detect and recover from unexpected responses
- **Progressive auth failure handling** — temporary failures retry, persistent failures (3+) trigger the HA re-auth flow

### Rate limits

The integration polls every 60 seconds by default. The watches themselves typically only update their position every 5–10 minutes, so more frequent polling provides no benefit. You can adjust the interval in the integration options.

## Supported models

The integration uses dynamic capability discovery and should work with any One2Track watch, including:

- Connect One
- Connect MOVE
- Connect UP

## Translations

The integration is available in:
- English
- Dutch (Nederlands)

## Troubleshooting

### "Invalid email or password"
Verify your credentials work at [one2trackgps.com](https://www.one2trackgps.com/). The integration uses the same login.

### Entities show "unavailable"
- **Device tracker**: Goes unavailable if the last location update is older than 30 minutes — this means the watch hasn't reported in. Check if it's powered on and has signal.
- **Other entities**: Check the Home Assistant logs for `one2track` entries. The most common cause is a temporary connection issue — the integration will automatically retry.

### Missing buttons/selects/switches
These entities only appear if the watch model supports the corresponding command. This is detected automatically on startup.

### Diagnostics
Download diagnostics from the device page to share when reporting issues. Sensitive data is automatically redacted.

## License

MIT
