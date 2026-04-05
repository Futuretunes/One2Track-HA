"""API client for the One2Track GPS platform."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import aiohttp

from .const import BASE_URL, LOGIN_PATH

_LOGGER = logging.getLogger(__name__)

_CSRF_RE = re.compile(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', re.IGNORECASE)
_ACCOUNT_ID_RE = re.compile(r"/users/([^/]+)")
_FUNCTION_CODE_RE = re.compile(r"function=(\d+)")


class One2TrackAuthError(Exception):
    """Raised when authentication fails."""


class One2TrackConnectionError(Exception):
    """Raised when the API is unreachable."""


class One2TrackApiClient:
    """API client for One2Track GPS watches."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._account_id: str | None = None
        self._csrf_token: str | None = None
        self._session: aiohttp.ClientSession | None = None
        self._auth_lock = asyncio.Lock()
        self._closed = False

    @property
    def account_id(self) -> str | None:
        return self._account_id

    def _ensure_session(self) -> aiohttp.ClientSession:
        """Create or return the aiohttp session with its own cookie jar."""
        if self._session is None or self._session.closed:
            jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(
                cookie_jar=jar,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def authenticate(self) -> bool:
        """Authenticate with One2Track and obtain session cookie + account ID.

        Returns True on success, raises One2TrackAuthError on failure.
        """
        session = self._ensure_session()

        # Clear all cookies to avoid stale session interference
        session.cookie_jar.clear()
        self._csrf_token = None

        # Step 1: GET the login page to obtain CSRF token
        try:
            async with session.get(
                f"{BASE_URL}{LOGIN_PATH}", allow_redirects=True
            ) as resp:
                if resp.status != 200:
                    raise One2TrackAuthError(
                        f"Failed to load login page (HTTP {resp.status})"
                    )
                html = await resp.text()
        except aiohttp.ClientError as err:
            raise One2TrackConnectionError(
                f"Cannot reach One2Track: {err}"
            ) from err

        match = _CSRF_RE.search(html)
        if not match:
            raise One2TrackAuthError("Could not find CSRF token on login page")
        csrf_token = match.group(1)

        # Step 2: POST credentials
        form_data = {
            "authenticity_token": csrf_token,
            "user[login]": self._email,
            "user[password]": self._password,
            "user[remember_me]": "1",
            "gdpr": "1",
        }

        try:
            async with session.post(
                f"{BASE_URL}{LOGIN_PATH}",
                data=form_data,
                allow_redirects=False,
            ) as resp:
                # Successful login returns a 302 redirect
                if resp.status not in (301, 302):
                    raise One2TrackAuthError(
                        "Login failed — check email and password"
                    )

                location = resp.headers.get("Location", "")
        except aiohttp.ClientError as err:
            raise One2TrackConnectionError(
                f"Login request failed: {err}"
            ) from err

        # Step 3: Extract account ID from redirect location
        # The redirect goes to something like /users/12345/devices
        account_match = _ACCOUNT_ID_RE.search(location)
        if not account_match:
            # Follow the redirect to find the account ID from the final URL
            try:
                async with session.get(
                    f"{BASE_URL}{location}" if not location.startswith("http") else location,
                    allow_redirects=True,
                ) as resp:
                    account_match = _ACCOUNT_ID_RE.search(str(resp.url))
            except aiohttp.ClientError:
                pass

        if not account_match:
            raise One2TrackAuthError(
                "Login succeeded but could not determine account ID"
            )

        self._account_id = account_match.group(1)
        self._csrf_token = None  # Will be fetched fresh before first POST
        _LOGGER.debug("Authenticated as account %s", self._account_id)
        return True

    async def _ensure_csrf_token(self) -> str:
        """Fetch a fresh CSRF token for POST requests."""
        session = self._ensure_session()
        try:
            async with session.get(
                f"{BASE_URL}/users/{self._account_id}/devices",
                allow_redirects=True,
            ) as resp:
                html = await resp.text()
                match = _CSRF_RE.search(html)
                if match:
                    self._csrf_token = match.group(1)
                    return self._csrf_token
        except aiohttp.ClientError:
            pass
        raise One2TrackConnectionError("Could not obtain CSRF token")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_response: bool = True,
        retry_auth: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request with automatic re-auth on session expiry.

        Returns parsed JSON (if json_response=True) or response text.
        """
        session = self._ensure_session()
        url = f"{BASE_URL}{path}"

        try:
            async with session.request(method, url, allow_redirects=False, **kwargs) as resp:
                # Check for redirect to login page (session expired)
                if resp.status in (301, 302):
                    location = resp.headers.get("Location", "")
                    if "sign_in" in location:
                        if retry_auth:
                            await self._reauth()
                            return await self._request(
                                method, path, json_response=json_response,
                                retry_auth=False, **kwargs,
                            )
                        raise One2TrackAuthError("Session expired and re-auth failed")

                    # Non-login redirect: follow it
                    async with session.get(
                        location if location.startswith("http") else f"{BASE_URL}{location}",
                        allow_redirects=True,
                    ) as follow_resp:
                        if json_response:
                            content_type = follow_resp.headers.get("Content-Type", "")
                            if "application/json" in content_type:
                                return await follow_resp.json()
                            # Got HTML instead of JSON — likely session expired
                            text = await follow_resp.text()
                            if "sign_in" in text and retry_auth:
                                await self._reauth()
                                return await self._request(
                                    method, path, json_response=json_response,
                                    retry_auth=False, **kwargs,
                                )
                            return await follow_resp.json(content_type=None)
                        return await follow_resp.text()

                if resp.status == 200:
                    if json_response:
                        content_type = resp.headers.get("Content-Type", "")
                        if "application/json" in content_type:
                            return await resp.json()
                        # Sometimes the server returns HTML when session is expired
                        text = await resp.text()
                        if "sign_in" in text and retry_auth:
                            await self._reauth()
                            return await self._request(
                                method, path, json_response=json_response,
                                retry_auth=False, **kwargs,
                            )
                        # Try parsing as JSON anyway (some pages lack proper content-type)
                        import json as json_mod
                        try:
                            return json_mod.loads(text)
                        except json_mod.JSONDecodeError:
                            return text
                    return await resp.text()

                if resp.status in (401, 403) and retry_auth:
                    await self._reauth()
                    return await self._request(
                        method, path, json_response=json_response,
                        retry_auth=False, **kwargs,
                    )

                resp.raise_for_status()

        except aiohttp.ClientError as err:
            raise One2TrackConnectionError(f"Request to {path} failed: {err}") from err

        return None

    async def _reauth(self) -> None:
        """Re-authenticate, guarded by a lock to prevent concurrent attempts."""
        async with self._auth_lock:
            _LOGGER.debug("Re-authenticating with One2Track")
            await self.authenticate()

    async def get_devices(self) -> list[dict[str, Any]]:
        """Fetch all devices for the account."""
        if not self._account_id:
            raise One2TrackAuthError("Not authenticated")

        data = await self._request(
            "GET",
            f"/users/{self._account_id}/devices",
            headers={"Accept": "application/json"},
        )

        if not isinstance(data, list):
            _LOGGER.warning("Unexpected device response type: %s", type(data))
            return []

        # Unwrap: API returns [{"device": {...}}, ...] or [{...}, ...]
        devices = []
        for item in data:
            if isinstance(item, dict):
                device = item.get("device", item)
                devices.append(device)
        return devices

    async def get_device_capabilities(self, uuid: str) -> list[str]:
        """Discover which command codes a device supports.

        Returns a list of command code strings like ["0039", "1015", ...].
        """
        try:
            html = await self._request(
                "GET",
                f"/devices/{uuid}/functions",
                params={"list_only": "true"},
                json_response=False,
            )
        except (One2TrackConnectionError, One2TrackAuthError):
            _LOGGER.warning("Could not fetch capabilities for device %s", uuid)
            return []

        if not isinstance(html, str):
            return []

        return _FUNCTION_CODE_RE.findall(html)

    async def get_device_geofences(self, uuid: str) -> list[dict[str, Any]]:
        """Fetch geofences for a device."""
        try:
            data = await self._request(
                "GET",
                f"/devices/{uuid}/geofences",
                headers={"Accept": "application/json"},
            )
        except (One2TrackConnectionError, One2TrackAuthError):
            _LOGGER.warning("Could not fetch geofences for device %s", uuid)
            return []

        if not isinstance(data, list):
            return []

        geofences = []
        for item in data:
            if isinstance(item, dict):
                geofence = item.get("geofence", item)
                geofences.append(geofence)
        return geofences

    async def send_command(
        self, uuid: str, cmd_code: str, cmd_values: list[str] | None = None,
    ) -> bool:
        """Send a command to a device."""
        csrf = await self._ensure_csrf_token()

        form_data: dict[str, Any] = {
            "authenticity_token": csrf,
            "_method": "patch",
            "function[cmd_code]": cmd_code,
        }
        if cmd_values:
            for value in cmd_values:
                # aiohttp handles repeated keys with list of tuples
                pass
            # Build as list of tuples for repeated keys
            fields: list[tuple[str, str]] = [
                ("authenticity_token", csrf),
                ("_method", "patch"),
                ("function[cmd_code]", cmd_code),
            ]
            for value in cmd_values:
                fields.append(("function[cmd_value][]", value))

            try:
                session = self._ensure_session()
                async with session.post(
                    f"{BASE_URL}/devices/{uuid}/functions",
                    data=fields,
                    headers={"X-CSRF-Token": csrf},
                    allow_redirects=True,
                ) as resp:
                    # HTTP 500 can happen even on success (portal quirk)
                    return resp.status in (200, 302, 500)
            except aiohttp.ClientError as err:
                _LOGGER.error("Failed to send command %s to %s: %s", cmd_code, uuid, err)
                return False
        else:
            try:
                session = self._ensure_session()
                async with session.post(
                    f"{BASE_URL}/devices/{uuid}/functions",
                    data=form_data,
                    headers={"X-CSRF-Token": csrf},
                    allow_redirects=True,
                ) as resp:
                    return resp.status in (200, 302, 500)
            except aiohttp.ClientError as err:
                _LOGGER.error("Failed to send command %s to %s: %s", cmd_code, uuid, err)
                return False

    async def send_message(self, uuid: str, message: str) -> bool:
        """Send a text message to a device."""
        csrf = await self._ensure_csrf_token()

        form_data = {
            "authenticity_token": csrf,
            "device_message[message]": message,
        }

        try:
            session = self._ensure_session()
            async with session.post(
                f"{BASE_URL}/devices/{uuid}/messages",
                data=form_data,
                headers={"X-CSRF-Token": csrf},
                allow_redirects=True,
            ) as resp:
                return resp.status in (200, 302)
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to send message to %s: %s", uuid, err)
            return False

    async def close(self) -> None:
        """Close the API client session."""
        self._closed = True
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
