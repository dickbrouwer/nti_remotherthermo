from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    NtiRemoteThermoApiClient,
    NtiRemoteThermoApiError,
    NtiRemoteThermoAuthError,
    NtiRemoteThermoRateLimitError,
    NtiRemoteThermoServerError,
)

_LOGGER = logging.getLogger(__name__)


class NtiRemoteThermoCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator to fetch and cache NTI RemoteThermo data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NtiRemoteThermoApiClient,
        param_ids: list[str],
        scan_interval_s: int,
    ) -> None:
        self._client = client
        self._param_ids = param_ids

        super().__init__(
            hass,
            _LOGGER,
            name="NTI RemoteThermo",
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=scan_interval_s),
        )

    def set_params(self, param_ids: list[str], scan_interval_s: int) -> None:
        """Update parameters at runtime (used when options change)."""
        self._param_ids = param_ids
        self.update_interval = timedelta(seconds=scan_interval_s)

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            payload = await self._client.fetch(self._param_ids)

        except NtiRemoteThermoAuthError as err:
            # Auth issues should be obvious in HA UI and logs
            raise UpdateFailed(f"Authentication failed: {err}") from err

        except NtiRemoteThermoRateLimitError as err:
            raise UpdateFailed(f"Rate limited by server: {err}") from err

        except NtiRemoteThermoServerError as err:
            raise UpdateFailed(f"Server error: {err}") from err

        except NtiRemoteThermoApiError as err:
            raise UpdateFailed(f"NTI API error: {err}") from err

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise UpdateFailed("Unexpected NTI response (ok != true)")

        data_list = payload.get("data", [])
        if not isinstance(data_list, list):
            raise UpdateFailed("Unexpected NTI response (data not list)")

        by_id: dict[str, dict[str, Any]] = {}
        for item in data_list:
            if isinstance(item, dict) and "id" in item:
                by_id[str(item["id"])] = item

        _LOGGER.debug("NTI update OK (items=%d)", len(by_id))

        return by_id
