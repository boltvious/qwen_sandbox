# auth_store.py — Setup wizard ala Codex CLI 🥷
from __future__ import annotations

import json
import os
import base64
import time
import httpx
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(SCRIPT_DIR, ".qwen_auth.json")

def decode_jwt(token: str) -> dict:
    """Decode payload JWT tanpa verifikasi (cukup buat display)."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


def _quick_profile(cookies: dict) -> dict:
    """Ambil email/nama dari endpoint auths (sekali, saat sign-in)."""
    headers = {"Authorization": f"Bearer {cookies.get('token', '')}"}
    targets = [
        ("https://coder.qwen.ai", "/coder/api/v2/auths/"),
        ("https://chat.qwen.ai", "/api/v2/auths/"),
    ]
    # Hanya kirim token di header, jangan di cookies untuk keamanan
    safe_cookies = {"token": cookies.get("token", "")} if "token" in cookies else {}
    for base, path in targets:
        try:
            r = httpx.get(base + path, headers=headers,
                          cookies=safe_cookies, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", {})
                if isinstance(data, dict) and (data.get("email") or data.get("name")):
                    return data
        except Exception:
            continue
    return {}


def print_auth_status(cookies: dict, profile: dict = None):
    """Tampilin identitas akun + masa berlaku token."""
    if profile is None:
        try:
            with open(AUTH_FILE) as f:
                profile = json.load(f).get("profile") or {}
        except Exception:
            profile = {}

    jwt = decode_jwt(cookies.get("token", ""))
    uid = profile.get("id") or jwt.get("id", "")
    name, email = profile.get("name"), profile.get("email")

    if name and email:
        who = f"{name} <{email}>"
    elif email:
        who = email
    elif uid:
        who = f"id {uid[:8]}…{uid[-4:]}"   # kepala…ekor fallback
    else:
        who = "unknown"

    console.print(f"[green]🔐 Signed in as:[/green] [bold]{who}[/bold]")

    exp = jwt.get("exp")
    if exp:
        when = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
        if exp - time.time() <= 0:
            console.print(f"[red]   ⚠ token expired sejak {when} "
                          f"— jalankan: python auth_store.py[/red]")
        else:
            console.print(f"[dim]   token aktif s/d {when}[/dim]")

def load_saved_auth():
    """Baca token tersimpan kalau ada."""
    try:
        with open(AUTH_FILE) as f:
            data = json.load(f)
        if data.get("cookies"):
            return data["cookies"]
    except Exception:
        pass
    return None


def save_auth(cookies: dict, source: str):
    with open(AUTH_FILE, "w") as f:
        json.dump({"source": source, "cookies": cookies}, f, indent=2)
    console.print(f"[green]✅ Token tersimpan di {os.path.basename(AUTH_FILE)}[/green]")
    console.print("[dim]⚠ File ini rahasia — jangan di-commit / dishare.[/dim]")


def parse_cookie_string(s: str) -> dict:
    cookies = {}
    for item in s.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def wizard():
    console.print(Panel.fit(
        "[bold cyan]🥷 Qwen Ninja CLI — Setup[/bold cyan]\n"
        "Welcome! Pilih cara sign in:",
        border_style="cyan",
    ))
    console.print("  [bold cyan]1.[/bold cyan] Paste cookie/token manual  [dim](copas dari DevTools)[/dim]")
    console.print("  [bold cyan]2.[/bold cyan] Auto-extract dari browser    [dim](butuh terminal admin)[/dim]")
    console.print("  [bold cyan]3.[/bold cyan] Exit")

    choice = Prompt.ask("\n> Pilihan", choices=["1", "2", "3"], default="1")

    if choice == "1":
        console.print(
            "[dim]Cara copas: buka chat.qwen.ai / coder.qwen.ai → F12 → Network → "
            "klik request apa aja → Headers → copy seluruh nilai 'Cookie'[/dim]"
        )
        raw = Prompt.ask("Paste Cookie header di sini")
        cookies = parse_cookie_string(raw)
        if cookies and "token" in cookies:
            profile = _quick_profile(cookies)      # <-- ambil email
            save_auth(cookies, "manual-paste", profile)
            print_auth_status(cookies, profile)    # <-- tampilin
            return cookies
        console.print("[red]❌ Format nggak valid atau 'token' nggak ketemu.[/red]")
        return None

    if choice == "2":
        try:
            from auth import extract_cookies, to_simple_cookie_dict
            cookies = to_simple_cookie_dict(extract_cookies())
        except Exception:
            cookies = None
        if cookies and "token" in cookies:
            save_auth(cookies, "browser-extract")
            return cookies
        console.print("[red]❌ Gagal extract. Coba opsi 1, atau jalanin sebagai admin.[/red]")
        return None

    return None


if __name__ == "__main__":
    result = wizard()
    if result:
        console.print("[bold green]Setup selesai! CLI siap dipakai tanpa ribet lagi. 🚀[/bold green]")