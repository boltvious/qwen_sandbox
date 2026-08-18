# client.py
from __future__ import annotations

import os
import httpx
from rich.console import Console

from auth import extract_cookies, to_simple_cookie_dict

console = Console()

BASE_URL = os.getenv("QWEN_BASE_URL", "https://chat.qwen.ai")

CANDIDATE_PREFIXES = ["/api/v2", "/api/v1", "/api", ""]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
)


def build_client() -> httpx.Client:
    from auth_store import load_saved_auth, wizard

    # 1) Coba token tersimpan; kalau belum ada, buka wizard ala Codex
    cookie_dict = load_saved_auth()
    if cookie_dict:
        from auth_store import print_auth_status
        print_auth_status(cookie_dict)     # ganti console.print lama
    else:
        cookie_dict = wizard()

    # 2) Validasi final
    if not cookie_dict or "token" not in cookie_dict:
        raise SystemExit("Auth gagal bro. Jalankan: python auth_store.py")

    # 3) Headers browser-like (Origin/Referer per-request
    #    di-override oleh extra_headers() masing-masing CLI)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    # 4) Token hanya di header Authorization (lebih aman)
    headers["Authorization"] = f"Bearer {cookie_dict['token']}"
    console.print("[green]🗝️ Token dipasang sebagai Bearer header.[/green]")

    # Filter cookie: jangan kirim semua cookie, cukup yang esensial saja
    # untuk menghindari kebocoran data sensitif
    safe_cookies = {}
    for key in ["_bl_uid", "locale"]:  # contoh cookie non-sensitif
        if key in cookie_dict:
            safe_cookies[key] = cookie_dict[key]

    return httpx.Client(
        headers=headers,
        cookies=safe_cookies if safe_cookies else None,
        timeout=30,
        follow_redirects=True,
    )

def probe_session(client: httpx.Client):
    """Nyari prefix API yang valid lewat endpoint ringan."""
    for prefix in CANDIDATE_PREFIXES:
        for path in (f"{prefix}/auths/", f"{prefix}/auths",
                     f"{prefix}/settings", f"{prefix}/configs/"):
            try:
                resp = client.get(path)
            except Exception as exc:
                console.print(f"[red]Network error di {path}: {exc}[/red]")
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    continue
                preview = str(data)[:120].replace("\n", " ")
                console.print(f"[green]VALID[/green] GET {path} -> 200 | {preview}...")
                return prefix, data

            console.print(f"[yellow]coba[/yellow] GET {path} -> {resp.status_code}")

    return None, None


if __name__ == "__main__":
    client = build_client()
    prefix, data = probe_session(client)

    if prefix is None:
        console.print("[red]Belum nemu prefix API yang valid bro.[/red]")
    else:
        console.print(f"\n[bold green]🎯 Prefix API ketemu: {prefix}[/bold green]")
        console.print("Session VALID. Siap lanjut ke misi capture POST completions!")