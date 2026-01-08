from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import COOKIE_NAME

_LOGGER = logging.getLogger(__name__)


class NtiRemoteThermoApiError(Exception):
    """Base exception for NTI API errors."""


class NtiRemoteThermoAuthError(NtiRemoteThermoApiError):
    """401/403 errors."""


class NtiRemoteThermoRateLimitError(NtiRemoteThermoApiError):
    """429 errors."""


class NtiRemoteThermoServerError(NtiRemoteThermoApiError):
    """5xx errors."""


class NtiRemoteThermoApiClient:
    """Async client for NTI RemoteThermo Refresh endpoint."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        refresh_path: str,
        client_id: str,
        token: str,
        timeout: int = 15,
    ) -> None:
        self._session = session
        self._url = f"{base_url}{refresh_path}"
        self._client_id = client_id
        self._token = token
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._lock = asyncio.Lock()

    async def fetch(self, param_ids: list[str]) -> dict[str, Any]:
        """Fetch current values for given param IDs."""
        params = {"id": self._client_id, "paramIds": ",".join(param_ids)}
        cookies = {COOKIE_NAME: self._token}

        # Keep these “browser-ish” headers since they resolved your 403 earlier.
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "HomeAssistant/nti_remotethermo",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.nti.remotethermo.com/",
        }

        async with self._lock:
            try:
                async with self._session.get(
                    self._url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=self._timeout,
                ) as resp:
                    if resp.status >= 400:
                        # Read body (best-effort) for diagnostics; do not log cookies/token.
                        body = ""
                        try:
                            body = await resp.text()
                        except Exception:
                            body = "<unable to read body>"

                        body_snip = body[:500].replace("\n", "\\n").replace("\r", "\\r")
                        _LOGGER.error(
                            "NTI API HTTP error %s %s (client_id=%s, path=%s, body=%s)",
                            resp.status,
                            resp.reason,
                            self._client_id,
                            str(resp.url),
                            body_snip,
                        )

                        if resp.status in (401, 403):
                            raise NtiRemoteThermoAuthError(
                                f"HTTP {resp.status} {resp.reason}"
                            )
                        if resp.status == 429:
                            raise NtiRemoteThermoRateLimitError(
                                f"HTTP 429 {resp.reason}"
                            )
                        if 500 <= resp.status <= 599:
                            raise NtiRemoteThermoServerError(
                                f"HTTP {resp.status} {resp.reason}"
                            )
                        raise NtiRemoteThermoApiError(
                            f"HTTP {resp.status} {resp.reason}"
                        )

                    # Parse JSON with explicit error handling
                    try:
                        return await resp.json()
                    except aiohttp.ContentTypeError as err:
                        text = await resp.text()
                        _LOGGER.error(
                            "NTI API returned non-JSON response (client_id=%s, path=%s, body=%s)",
                            self._client_id,
                            str(resp.url),
                            text[:500].replace("\n", "\\n").replace("\r", "\\r"),
                        )
                        raise NtiRemoteThermoApiError("Non-JSON response") from err

            except asyncio.TimeoutError as err:
                _LOGGER.warning(
                    "NTI API request timed out (client_id=%s, url=%s)",
                    self._client_id,
                    self._url,
                )
                raise NtiRemoteThermoApiError("Request timed out") from err

            except aiohttp.ClientConnectionError as err:
                _LOGGER.warning(
                    "NTI API connection error (client_id=%s, url=%s): %s",
                    self._client_id,
                    self._url,
                    err,
                )
                raise NtiRemoteThermoApiError("Connection error") from err

            except aiohttp.ClientError as err:
                # Catch-all for aiohttp errors not covered above
                _LOGGER.warning(
                    "NTI API client error (client_id=%s, url=%s): %s",
                    self._client_id,
                    self._url,
                    err,
                )
                raise NtiRemoteThermoApiError("HTTP client error") from err
