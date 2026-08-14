"""
عميل REST بسيط للتواصل مع باك اند WolfHost.
- لا يلمس قاعدة البيانات مباشرة أبدًا — كل شيء عبر HTTP فقط.
- المصادقة عبر هيدر X-API-Key ثابت (BOT_CONTROL_API_KEY في .env الرئيسي)
  والذي يقابله دعم جديد أضيف في backend/app/core/dependencies.py::get_current_user.
"""
from __future__ import annotations

import httpx

from bot.config import settings


class ApiError(Exception):
    """خطأ عام قادم من الـ API (حالة HTTP غير ناجحة)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class WolfHostClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.WOLFHOST_API_BASE_URL,
            headers={"X-API-Key": settings.WOLFHOST_API_KEY},
            timeout=settings.API_TIMEOUT_SECONDS,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = await self._client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(0, f"connection_error: {exc}") from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise ApiError(resp.status_code, str(detail))
        return resp

    # ---------- Bots ----------
    async def list_bots(self) -> list[dict]:
        r = await self._request("GET", "/bots")
        return r.json()

    async def get_bot(self, bot_id: str) -> dict:
        r = await self._request("GET", f"/bots/{bot_id}")
        return r.json()

    async def create_bot(self, name: str, source_type: str, entrypoint: str = "main.py", git_url: str | None = None) -> dict:
        payload = {"name": name, "source_type": source_type, "entrypoint": entrypoint}
        if git_url:
            payload["git_url"] = git_url
        r = await self._request("POST", "/bots", json=payload)
        return r.json()

    async def upload_bot_file(self, bot_id: str, filename: str, content: bytes) -> dict:
        files = {"file": (filename, content)}
        r = await self._request("POST", f"/bots/{bot_id}/upload", files=files)
        return r.json()

    async def start_bot(self, bot_id: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/start")
        return r.json()

    async def stop_bot(self, bot_id: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/stop")
        return r.json()

    async def restart_bot(self, bot_id: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/restart")
        return r.json()

    async def delete_bot(self, bot_id: str) -> None:
        await self._request("DELETE", f"/bots/{bot_id}")

    async def update_env(self, bot_id: str, env_vars: dict[str, str]) -> dict:
        r = await self._request("PUT", f"/bots/{bot_id}/env", json={"env_vars": env_vars})
        return r.json()

    async def get_logs(self, bot_id: str, tail: int = 100) -> str:
        r = await self._request("GET", f"/bots/{bot_id}/logs", params={"tail": tail})
        return r.json().get("logs", "")

    async def get_stats(self, bot_id: str) -> dict | None:
        try:
            r = await self._request("GET", f"/bots/{bot_id}/stats")
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise
        return r.json()

    # ---------- Files ----------
    async def list_files(self, bot_id: str, path: str = "") -> list[dict]:
        r = await self._request("GET", f"/bots/{bot_id}/files", params={"path": path})
        return r.json()

    async def read_file(self, bot_id: str, path: str) -> str:
        r = await self._request("GET", f"/bots/{bot_id}/files/content", params={"path": path})
        return r.json().get("content", "")

    async def write_file(self, bot_id: str, path: str, content: str) -> dict:
        r = await self._request("PUT", f"/bots/{bot_id}/files/content", params={"path": path}, json={"content": content})
        return r.json()

    async def download_file(self, bot_id: str, path: str) -> bytes:
        r = await self._request("GET", f"/bots/{bot_id}/files/download", params={"path": path})
        return r.content

    async def delete_file(self, bot_id: str, path: str) -> dict:
        r = await self._request("DELETE", f"/bots/{bot_id}/files", params={"path": path})
        return r.json()

    async def rename_file(self, bot_id: str, path: str, new_name: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/files/rename", params={"path": path}, json={"new_name": new_name})
        return r.json()

    async def move_file(self, bot_id: str, path: str, destination: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/files/move", params={"path": path}, json={"destination": destination})
        return r.json()

    async def copy_file(self, bot_id: str, path: str, destination: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/files/copy", params={"path": path}, json={"destination": destination})
        return r.json()

    # ---------- Console ----------
    async def run_console(self, bot_id: str, command: str) -> dict:
        r = await self._request("POST", f"/bots/{bot_id}/console", params={"command": command})
        return r.json()

    # ---------- Account / Settings ----------
    async def get_profile(self) -> dict:
        r = await self._request("GET", "/users/me")
        return r.json()

    async def change_password(self, current_password: str, new_password: str) -> dict:
        r = await self._request(
            "PUT", "/users/me/password",
            params={"current_password": current_password, "new_password": new_password},
        )
        return r.json()

    async def get_audit_logs(self, limit: int = 20) -> list[dict]:
        r = await self._request("GET", "/users/me/audit-logs", params={"limit": limit})
        return r.json()


api_client = WolfHostClient()
