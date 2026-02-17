from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

from .const import COOKIE_NAME

_LOGGER = logging.getLogger(__name__)


class NtiRemoteThermoApiError(Exception):
    """Base exception for NTI API errors."""


class NtiRemoteThermoAuthError(NtiRemoteThermoApiError):
    """Authentication errors (bad credentials, expired cookie, 401/403)."""


class NtiRemoteThermoRateLimitError(NtiRemoteThermoApiError):
    """429 errors."""


class NtiRemoteThermoServerError(NtiRemoteThermoApiError):
    """5xx errors."""


class NtiRemoteThermoApiClient:
    """Async client for NTI RemoteThermo with email/password authentication."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        refresh_path: str,
        login_path: str,
        client_id: str,
        email: str,
        password: str,
        timeout: int = 15,
    ) -> None:
        self._session = session
        self._base_url = base_url
        self._refresh_url = f"{base_url}{refresh_path}"
        self._login_url = f"{base_url}{login_path}"
        self._client_id = client_id
        self._email = email
        self._password = password
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._token: str | None = None
        self._login_lock = asyncio.Lock()

    async def _login(self) -> str:
        """Perform email/password login and return the auth cookie value.

        1. GET the login page to capture session cookies and CSRF token.
        2. POST credentials as form-encoded data.
        3. Extract .AspNet.ApplicationCookie from response.
        """
        # Step 1: GET login page for CSRF token and session cookies
        try:
            async with self._session.get(
                self._login_url, timeout=self._timeout
            ) as resp:
                login_html = await resp.text()
                # Capture any cookies the server set (e.g. anti-forgery)
                login_cookies = {
                    k: v.value for k, v in resp.cookies.items()
                }
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise NtiRemoteThermoApiError(
                f"Failed to load login page: {err}"
            ) from err

        verification_token = self._extract_verification_token(login_html)

        # Step 2: POST credentials
        form_data: dict[str, str] = {
            "Email": self._email,
            "Password": self._password,
            "RememberMe": "true",
        }
        if verification_token:
            form_data["__RequestVerificationToken"] = verification_token

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "HomeAssistant/nti_remotethermo",
            "Referer": self._login_url,
        }

        try:
            async with self._session.post(
                self._login_url,
                data=form_data,
                headers=headers,
                cookies=login_cookies,
                allow_redirects=False,
                timeout=self._timeout,
            ) as resp:
                # Extract auth cookie from response
                cookie_value = None
                for cookie_key, cookie_morsel in resp.cookies.items():
                    if cookie_key == COOKIE_NAME:
                        cookie_value = cookie_morsel.value
                        break

                if not cookie_value:
                    # ASP.NET may return 200 (re-rendered login form) or
                    # 302 back to login on failure — either way, no cookie
                    # means authentication failed.
                    _LOGGER.error(
                        "NTI login failed: no auth cookie returned "
                        "(status=%s, email=%s)",
                        resp.status,
                        self._email,
                    )
                    raise NtiRemoteThermoAuthError(
                        "Login failed: invalid email or password"
                    )

                _LOGGER.debug(
                    "NTI login successful (email=%s)", self._email
                )
                return cookie_value

        except NtiRemoteThermoAuthError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise NtiRemoteThermoApiError(
                f"Login request failed: {err}"
            ) from err

    @staticmethod
    def _extract_verification_token(html: str) -> str | None:
        """Extract __RequestVerificationToken from a hidden input field."""
        match = re.search(
            r'<input[^>]+name="__RequestVerificationToken"[^>]+value="([^"]*)"',
            html,
        )
        if match:
            return match.group(1)
        # Also try the reverse attribute order
        match = re.search(
            r'<input[^>]+value="([^"]*)"[^>]+name="__RequestVerificationToken"',
            html,
        )
        return match.group(1) if match else None

    async def _ensure_token(self) -> str:
        """Return the cached cookie or perform a fresh login."""
        if self._token is not None:
            return self._token
        async with self._login_lock:
            # Double-check after acquiring lock
            if self._token is not None:
                return self._token
            self._token = await self._login()
            return self._token

    async def _invalidate_and_refresh_token(self, failed_token: str) -> str:
        """Invalidate the cached cookie and re-login.

        Uses a stale-token check so that concurrent callers that fail with
        the same expired cookie don't all re-login redundantly.
        """
        async with self._login_lock:
            if self._token is not None and self._token != failed_token:
                # Another coroutine already refreshed the token
                return self._token
            self._token = None
            self._token = await self._login()
            return self._token

    async def fetch(self, param_ids: list[str]) -> dict[str, Any]:
        """Fetch current values for given param IDs.

        Automatically handles authentication and retries once on auth errors.
        """
        token = await self._ensure_token()
        try:
            return await self._do_fetch(param_ids, token)
        except NtiRemoteThermoAuthError:
            _LOGGER.debug(
                "Auth error during fetch, refreshing token (client_id=%s)",
                self._client_id,
            )
            token = await self._invalidate_and_refresh_token(token)
            return await self._do_fetch(param_ids, token)

    async def _do_fetch(
        self, param_ids: list[str], token: str
    ) -> dict[str, Any]:
        """Perform the actual HTTP GET to the Refresh endpoint."""
        params = {"id": self._client_id, "paramIds": ",".join(param_ids)}
        cookies = {COOKIE_NAME: token}

        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "HomeAssistant/nti_remotethermo",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.nti.remotethermo.com/",
        }

        try:
            async with self._session.get(
                self._refresh_url,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=self._timeout,
            ) as resp:
                if resp.status >= 400:
                    body = ""
                    try:
                        body = await resp.text()
                    except Exception:
                        body = "<unable to read body>"

                    body_snip = (
                        body[:500].replace("\n", "\\n").replace("\r", "\\r")
                    )
                    _LOGGER.error(
                        "NTI API HTTP error %s %s "
                        "(client_id=%s, path=%s, body=%s)",
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

                try:
                    return await resp.json()
                except aiohttp.ContentTypeError as err:
                    text = await resp.text()
                    _LOGGER.error(
                        "NTI API returned non-JSON response "
                        "(client_id=%s, path=%s, body=%s)",
                        self._client_id,
                        str(resp.url),
                        text[:500]
                        .replace("\n", "\\n")
                        .replace("\r", "\\r"),
                    )
                    raise NtiRemoteThermoApiError(
                        "Non-JSON response"
                    ) from err

        except asyncio.TimeoutError as err:
            _LOGGER.warning(
                "NTI API request timed out (client_id=%s, url=%s)",
                self._client_id,
                self._refresh_url,
            )
            raise NtiRemoteThermoApiError("Request timed out") from err

        except aiohttp.ClientConnectionError as err:
            _LOGGER.warning(
                "NTI API connection error (client_id=%s, url=%s): %s",
                self._client_id,
                self._refresh_url,
                err,
            )
            raise NtiRemoteThermoApiError("Connection error") from err

        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "NTI API client error (client_id=%s, url=%s): %s",
                self._client_id,
                self._refresh_url,
                err,
            )
            raise NtiRemoteThermoApiError("HTTP client error") from err
