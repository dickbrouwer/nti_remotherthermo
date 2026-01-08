# NTI RemoteThermo (Home Assistant)

Custom Home Assistant integration for reading sensor values from **nti.remotethermo.com** via the `PlantMenu/Refresh` endpoint.

## Features

- Config Flow (UI setup)
- Options Flow: configure `paramIds` and polling interval
- One Home Assistant sensor entity per `paramId`
- Cookie-based authentication (`.AspNet.ApplicationCookie`)
- Cloud polling via `DataUpdateCoordinator`

## Installation (HACS)

1. In Home Assistant, install **HACS** (if not already installed).
2. HACS → **Integrations** → top-right menu → **Custom repositories**
3. Add this GitHub repository URL and select **Integration**
4. Install **NTI RemoteThermo**
5. Restart Home Assistant

Then:
- Settings → Devices & services → Add integration → **NTI RemoteThermo**

## Configuration

During setup you will be prompted for:

- **Client ID**
- **Cookie token**: the value of `.AspNet.ApplicationCookie`

After setup:
- Settings → Devices & services → NTI RemoteThermo → **Configure**
- Update:
  - `param_ids` (comma-separated)
  - `scan_interval` (seconds)

## Getting the cookie token

Use your existing method of obtaining the `.AspNet.ApplicationCookie` value (e.g., browser devtools or curl login flow).
This integration currently expects you to paste the cookie token value.

## Troubleshooting

### 403 Forbidden
This usually indicates:
- token expired/invalid
- token does not match the configured client id
- missing required request headers/cookies

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.nti_remotethermo: debug
```

Restart Home Assistant, then inspect logs.


## Disclaimer

This is not an official NTI integration. Use at your own risk.
