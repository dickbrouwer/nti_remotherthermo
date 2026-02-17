# NTI RemoteThermo (Home Assistant)

Custom Home Assistant integration for reading sensor values and controlling setpoints on **nti.remotethermo.com**.

## Features

- Config Flow (UI setup) with email/password authentication
- Automatic login to the NTI RemoteThermo portal (no manual cookie handling)
- Transparent session renewal on expiry (no user intervention needed)
- Re-authentication flow when credentials change
- Options Flow: configure `paramIds` and polling interval
- One Home Assistant sensor entity per `paramId`
- Writable **Number entity** for Zone CH setpoint temperature (T4_0_2, 90–140°F)
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

- **Client ID**: your RemoteThermo client identifier
- **Email**: your NTI RemoteThermo account email
- **Password**: your NTI RemoteThermo account password

After setup:
- Settings → Devices & services → NTI RemoteThermo → **Configure**
- Update:
  - `param_ids` (comma-separated)
  - `scan_interval` (seconds)

## Upgrading from v1 (cookie-token auth)

If you previously configured this integration using a cookie token, upgrading will automatically migrate your config entry. You will be prompted to re-authenticate with your email and password. All existing sensor history and long-term statistics are preserved.

## Troubleshooting

### Authentication errors
This usually indicates:
- incorrect email or password
- password was changed on the NTI website
- the NTI RemoteThermo portal is temporarily unavailable

When authentication fails, Home Assistant will show a re-authentication prompt. Enter your current credentials to reconnect.

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
