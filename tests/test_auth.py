"""Tests for JellyJelly Supabase auth module."""

from __future__ import annotations

import httpx
import pytest
import respx

from jellyjelly.auth import JellyAuth, JellyAuthError

from .conftest import make_auth_response


class TestSendOTP:
    async def test_send_otp_success(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/otp").mock(return_value=httpx.Response(200, json={}))
        auth = JellyAuth()
        try:
            result = await auth.send_otp("+15551234567")
            assert result is True
        finally:
            await auth.close()

    async def test_send_otp_error(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/otp").mock(
            return_value=httpx.Response(400, json={"msg": "Invalid phone number"})
        )
        auth = JellyAuth()
        try:
            with pytest.raises(JellyAuthError, match="Invalid phone number"):
                await auth.send_otp("bad-phone")
        finally:
            await auth.close()


class TestVerifyOTP:
    async def test_verify_otp_success(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/verify").mock(
            return_value=httpx.Response(200, json=make_auth_response())
        )
        auth = JellyAuth()
        try:
            session = await auth.verify_otp("+15551234567", "123456")
            assert session.access_token == "test-access-token"
            assert session.refresh_token == "test-refresh-token"
            assert session.user_id == "user-001"
            assert session.expires_at == 1735689600
        finally:
            await auth.close()

    async def test_verify_otp_invalid_code(
        self, mock_supabase: respx.MockRouter
    ) -> None:
        mock_supabase.post("/verify").mock(
            return_value=httpx.Response(
                401, json={"msg": "Token has expired or is invalid"}
            )
        )
        auth = JellyAuth()
        try:
            with pytest.raises(JellyAuthError, match="expired or is invalid"):
                await auth.verify_otp("+15551234567", "000000")
        finally:
            await auth.close()


class TestSignInEmail:
    async def test_sign_in_email_success(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/token", params={"grant_type": "password"}).mock(
            return_value=httpx.Response(200, json=make_auth_response())
        )
        auth = JellyAuth()
        try:
            session = await auth.sign_in_email("rick@test.com", "pass123")
            assert session.access_token == "test-access-token"
            assert session.user_id == "user-001"
        finally:
            await auth.close()

    async def test_sign_in_email_bad_credentials(
        self, mock_supabase: respx.MockRouter
    ) -> None:
        mock_supabase.post("/token", params={"grant_type": "password"}).mock(
            return_value=httpx.Response(
                400,
                json={"error_description": "Invalid login credentials"},
            )
        )
        auth = JellyAuth()
        try:
            with pytest.raises(JellyAuthError, match="Invalid login"):
                await auth.sign_in_email("rick@test.com", "wrong")
        finally:
            await auth.close()


class TestRefreshToken:
    async def test_refresh_success(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/token", params={"grant_type": "refresh_token"}).mock(
            return_value=httpx.Response(
                200,
                json=make_auth_response(
                    access_token="new-access-token",
                    refresh_token="new-refresh-token",
                ),
            )
        )
        auth = JellyAuth()
        try:
            session = await auth.refresh_token("old-refresh-token")
            assert session.access_token == "new-access-token"
            assert session.refresh_token == "new-refresh-token"
        finally:
            await auth.close()

    async def test_refresh_expired(self, mock_supabase: respx.MockRouter) -> None:
        mock_supabase.post("/token", params={"grant_type": "refresh_token"}).mock(
            return_value=httpx.Response(
                401, json={"msg": "Token has expired or is invalid"}
            )
        )
        auth = JellyAuth()
        try:
            with pytest.raises(JellyAuthError, match="expired or is invalid"):
                await auth.refresh_token("expired-token")
        finally:
            await auth.close()


class TestParseSession:
    async def test_missing_user_key(self, mock_supabase: respx.MockRouter) -> None:
        """Auth response without user key still parses."""
        mock_supabase.post("/verify").mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_at": 0,
                },
            )
        )
        auth = JellyAuth()
        try:
            session = await auth.verify_otp("+15551234567", "123456")
            assert session.access_token == "tok"
            assert session.user_id == ""
        finally:
            await auth.close()
