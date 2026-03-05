"""Supabase-based authentication for JellyJelly."""

from __future__ import annotations

from typing import Any

import httpx

from jellyjelly.models import AuthSession

SUPABASE_URL = "https://cbtzdoasmkbbiwnyoxvz.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNidHpkb2FzbWtiYml3bnlveHZ6Iiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3MzY0NTQ3NzgsImV4cCI6MjA1MjAzMDc3OH0"
    ".VoA53bSzMBxiGVdFVKLYWWfBRpCIENOC_C5MqI3-bzU"
)


class JellyAuthError(Exception):
    """Raised when a JellyJelly auth operation fails."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"JellyJelly auth error: {detail}")


class JellyAuth:
    """Supabase-based auth for JellyJelly.

    Usage::

        auth = JellyAuth()
        await auth.send_otp("+15551234567")
        session = await auth.verify_otp("+15551234567", "123456")
        print(session.access_token)
    """

    def __init__(
        self,
        supabase_url: str = SUPABASE_URL,
        anon_key: str = SUPABASE_ANON_KEY,
        timeout: float = 30.0,
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._anon_key = anon_key
        self._client = httpx.AsyncClient(
            base_url=f"{self._supabase_url}/auth/v1",
            timeout=timeout,
            headers={
                "apikey": self._anon_key,
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST to a Supabase Auth endpoint."""
        resp = await self._client.post(path, json=body)
        data: Any = resp.json()
        if resp.status_code >= 400:
            msg = data.get("msg") or data.get("error_description") or resp.text
            raise JellyAuthError(str(msg))
        if not isinstance(data, dict):
            raise JellyAuthError(f"Unexpected response: {resp.text[:200]}")
        return data

    def _parse_session(self, data: dict[str, Any]) -> AuthSession:
        """Extract an AuthSession from a Supabase auth response."""
        access_token = data.get("access_token", "")
        refresh_token = data.get("refresh_token", "")
        expires_at = data.get("expires_at", 0)
        user = data.get("user", {})
        user_id = user.get("id", "") if isinstance(user, dict) else ""
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_id=user_id,
        )

    async def send_otp(self, phone: str) -> bool:
        """Send an OTP code to a phone number via Twilio.

        Args:
            phone: Phone number in E.164 format (e.g. +15551234567).

        Returns:
            True if OTP was sent successfully.
        """
        await self._post("/otp", {"phone": phone})
        return True

    async def verify_otp(self, phone: str, code: str) -> AuthSession:
        """Verify an OTP code and return an authenticated session.

        Args:
            phone: Phone number used in send_otp.
            code: The 6-digit OTP code.

        Returns:
            AuthSession with access and refresh tokens.
        """
        data = await self._post(
            "/verify",
            {"phone": phone, "token": code, "type": "sms"},
        )
        return self._parse_session(data)

    async def sign_in_email(self, email: str, password: str) -> AuthSession:
        """Sign in with email and password.

        Args:
            email: User email.
            password: User password.

        Returns:
            AuthSession with access and refresh tokens.
        """
        data = await self._post(
            "/token?grant_type=password",
            {"email": email, "password": password},
        )
        return self._parse_session(data)

    async def refresh_token(self, refresh_token: str) -> AuthSession:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token from a previous session.

        Returns:
            New AuthSession with fresh tokens.
        """
        data = await self._post(
            "/token?grant_type=refresh_token",
            {"refresh_token": refresh_token},
        )
        return self._parse_session(data)
