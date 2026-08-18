# chat.py  (v6 — multi-platform: chat & coder)
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
import platform as plat
from datetime import datetime

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from client import build_client

console = Console()

PLATFORMS = {
    "chat": {
        "base_url": "https://chat.qwen.ai",
        "completions_path": "/api/v2/chat/completions",
        "default_model": "qwen3.8-max",
        "chat_type": "t2t",
        "feature_config": {
            "thinking_enabled": True,
            "output_schema": "phase",
            "research_mode": "normal",
            "auto_thinking": False,
            "thinking_mode": "Thinking",
            "thinking_format": "summary",
            "auto_search": True,
        },
        "extra_meta": {"subChatType": "t2t"},
        "chat_list_path": "/api/v2/chats/",
    },
    "coder": {
        "base_url": "https://coder.qwen.ai",
        "completions_path": "/coder/api/v2/task/completions",
        "default_model": "qwen3-coder-plus",
        "chat_type": "code",
        "feature_config": {
            "thinking_enabled": False,
            "output_schema": "phase",
        },
        "extra_meta": {"subChatType": "code"},
        "chat_list_path": "/coder/api/v2/chats/",
    },
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, ".endpoint_cache.json")
SESSION_FILE = os.path.join(SCRIPT_DIR, ".session.json")
MAX_FILE_CHARS = 100_000


# ---------- util ----------

def js_timezone() -> str:
    now = datetime.now()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    offset = -time.altzone if time.daylight else -time.timezone
    sign = "+" if offset >= 0 else "-"
    hh, mm = divmod(abs(offset) // 60, 60)
    return (f"{days[now.weekday()]} {months[now.month - 1]} {now.day:02d} "
            f"{now.year} {now:%H:%M:%S} GMT{sign}{hh:02d}{mm:02d}")


def extra_headers(base_url: str, chat_id: str) -> dict:
    return {
        "source": "web",
        "version": "0.2.86",
        "timezone": js_timezone(),
        "x-request-id": str(uuid.uuid4()),
        "x-accel-buffering": "no",
        "referer": f"{base_url}/c/{chat_id}",
    }


def _success(obj):
    return isinstance(obj, dict) and obj.get("success") is True


def _data_of(obj):
    return obj.get("data", obj) if isinstance(obj, dict) else obj


def _deep_get(obj, keys):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str):
                return v
            r = _deep_get(v, keys)
            if r:
                return r
    elif isinstance(obj, list):
        for it in obj:
            r = _deep_get(it, keys)
            if r:
                return r
    return None


# ---------- session lokal (memori B) ----------

def load_session(platform: str):
    try:
        with open(SESSION_FILE) as f:
            return json.load(f).get(platform)
    except Exception:
        return None


def save_session(platform: str, chat_id, parent_id):
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data[platform] = {"chat_id": chat_id, "parent_id": parent_id}
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)


def reset_session(platform: str):
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
        if platform in data:
            del data[platform]
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ---------- manajemen chat ----------

def get_chat(client, base_url, chat_id):
    for path in (f"/api/v2/chats/{chat_id}", f"/api/v2/chat/{chat_id}",
                 f"/coder/api/v2/chats/{chat_id}", f"/coder/api/v2/task/{chat_id}"):
        try:
            r = client.get(path)
        except Exception:
            continue
        if r.status_code == 200:
            try:
                obj = r.json()
            except Exception:
                continue
            if isinstance(obj, dict) and obj.get("success") is not False:
                return obj
    return None


def create_chat(client, base_url, chat_id, title="qwen-coder-cli"):
    paths = ["/api/v2/chats/new", "/coder/api/v2/chats/new",
             "/api/v2/chats/", "/coder/api/v2/chats/"]
    bodies = [
        {"chat_id": chat_id, "title": title},
        {"id": chat_id, "title": title},
        {"chat": {"title": title,
                  "history": {"currentId": None, "messages": {}}}},
    ]
    for path in paths:
        for body in bodies:
            try:
                r = client.post(path, json=body, params={"chat_id": chat_id})
            except Exception:
                continue
            if r.status_code in (200, 201):
                try:
                    obj = r.json()
                except Exception:
                    return True
                if not (isinstance(obj, dict) and obj.get("success") is False):
                    return True
    return False


def get_latest_chat_id(client, chat_list_path: str):
    for suffix in ("?page=1", "?page_num=1&page_size=10", ""):
        try:
            r = client.get(chat_list_path + suffix)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        try:
            obj = r.json()
        except Exception:
            continue
        data = _data_of(obj)
        items = (data if isinstance(data, list)
                 else (data.get("items") or data.get("list") or data.get("chats") or [])
                 if isinstance(data, dict) else [])
        for it in items:
            if isinstance(it, dict):
                cid = it.get("id") or it.get("chat_id") or it.get("chatId")
                if isinstance(cid, str) and "-" in cid and len(cid) > 8:
                    return cid
    return None


def ensure_chat(client, platform: str, wanted_id=None):
    cfg = PLATFORMS[platform]
    if wanted_id:
        obj = get_chat(client, cfg["base_url"], wanted_id)
        parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
        return wanted_id, parent

    latest = get_latest_chat_id(client, cfg["chat_list_path"])
    if latest:
        console.print(f"[cyan] Numpang di chat terbaru ({platform}):[/cyan] {latest[:8]}…")
        obj = get_chat(client, cfg["base_url"], latest)
        parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
        return latest, parent

    chat_id = str(uuid.uuid4())
    if create_chat(client, cfg["base_url"], chat_id):
        if get_chat(client, cfg["base_url"], chat_id) is not None:
            console.print(f"[green] Chat baru dibuat ({platform}):[/green] {chat_id[:8]}…")
            return chat_id, None

    console.print(f"[yellow]⚠ Nggak ada history & gagal create via API untuk {platform}.[/yellow]")
    console.print(f"[cyan]💡 Pakai --chat-id <ID_CHAT_WEB> atau buka web dan kirim 1 pesan manual.[/cyan]")
    return None, None


# ---------- konteks file & lingkungan ----------

def read_context_files(paths):
    parts = []
    for p in paths or []:
        try:
            with open(p, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
        except Exception as exc:
            console.print(f"[yellow]⚠ gagal baca {p}: {exc}[/yellow]")
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n... (truncated)"
            console.print(f"[yellow] {p} kepotong (>{MAX_FILE_CHARS} char)[/yellow]")
        parts.append(f'<file name="{p}">\n{content}\n</file>')
    return "\n\n".join(parts)


def get_local_context():
    return (
        f"<local_environment_context>\n"
        f"You are running as a local CLI tool on the user's personal machine.\n"
        f"OS: {plat.system()} {plat.release()}\n"
        f"Current Working Directory: {os.getcwd()}\n"
        f"</local_environment_context>\n"
    )


def build_final_prompt(prompt, files_ctx, stdin_text):
    blocks = []
    if files_ctx:
        blocks.append(files_ctx)
    if stdin_text:
        blocks.append(f"<stdin>\n{stdin_text}\n</stdin>")
    if not blocks:
        return prompt
    return "\n\n".join(blocks) + f"\n\n<user_request>\n{prompt}\n</user_request>"


# ---------- payload & parser ----------

def build_payload(prompt: str, model: str, chat_id: str, parent_id, platform: str) -> dict:
    cfg = PLATFORMS[platform]
    ts = int(time.time())
    fid = str(uuid.uuid4())
    child = str(uuid.uuid4())
    return {
        "stream": True,
        "version": "2.1",
        "incremental_output": True,
        "chatId": chat_id,
        "parentId": "" if parent_id is None else parent_id,
        "chat_id": chat_id,
        "parent_id": parent_id,
        "chat_mode": "normal",
        "model": model or cfg["default_model"],
        "messages": [{
            "id": None,
            "fid": fid,
            "parentId": "" if parent_id is None else parent_id,
            "childrenIds": [child],
            "role": "user",
            "content": prompt,
            "user_action": "chat",
            "files": [],
            "timestamp": ts,
            "models": [model or cfg["default_model"]],
            "model": "",
            "chat_type": cfg["chat_type"],
            "feature_config": cfg["feature_config"],
            "extra": {"meta": cfg["extra_meta"]},
            "sub_chat_type": cfg["chat_type"],
            "parent_id": parent_id,
        }],
        "timestamp": ts,
    }


def _first_str(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v:
            return v
    return None


def extract_delta(obj):
    if not isinstance(obj, dict):
        return None, None
    if isinstance(obj.get("data"), dict):
        return extract_delta(obj["data"])

    text = thinking = None

    choices = obj.get("choices")
    if isinstance(choices, list) and choices:
        d = choices[0].get("delta") or choices[0].get("message") or {}
        text = _first_str(d, "content", "text")
        thinking = _first_str(d, "reasoning_content", "thinking")

    if text is None and isinstance(obj.get("output"), dict):
        out = obj["output"]
        text = _first_str(out, "text", "content")
        ch = out.get("choices")
        if isinstance(ch, list) and ch:
            d = ch[0].get("delta") or ch[0].get("message") or {}
            text = text or _first_str(d, "content", "text")
            thinking = thinking or _first_str(d, "reasoning_content", "thinking")

    if text is None:
        text = _first_str(obj, "content", "text")
    thinking = thinking or _first_str(obj, "reasoning_content", "thinking")

    return text, thinking


def load_cached_endpoint(platform: str):
    try:
        with open(CACHE_FILE) as f:
            return json.load(f).get(platform)
    except Exception:
        return None


def pick_endpoints(platform: str):
    cached = load_cached_endpoint(platform)
    cfg = PLATFORMS[platform]
    base = [cfg["completions_path"]]
    if cached and cached != cfg["completions_path"]:
        base.append(cached)
    return base


def iter_chunks(resp, raw=False):
    for line in resp.iter_lines():
        yield ("raw", line)
        if raw:
            console.print(line, style="dim")
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line in ("", "[DONE]"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("success") is False:
            yield ("fatal", json.dumps(obj.get("data", {}), ensure_ascii=False)[:400])
            return
        text, thinking = extract_delta(obj)
        if thinking:
            yield ("think", thinking)
        if text:
            yield ("text", text)


def stream_chat(client, endpoint: str, payload: dict, raw=False, pretty=True):
    cfg = PLATFORMS[payload.get("chatId", "").split("-")[0] if "-" in payload.get("chatId", "") else "chat"] 
    # Trick: ambil platform dari payload/chat_id context atau pass eksplisit. 
    # Biar clean, kita pass platform eksplisit di fungsi ask() nanti.
    pass


# ---------- inti ----------

def ask(client, prompt_text, model, platform, args):
    cfg = PLATFORMS[platform]
    chat_id, parent_id = ensure_chat(client, platform, args.chat_id)
    if not chat_id:
        return False

    console.print(Panel.fit(
        f"[bold cyan]Qwen Coder CLI ({platform.upper()})[/bold cyan]\n"
        f"model: [green]{model or cfg['default_model']}[/green] | chat: [dim]{chat_id[:8]}…[/dim]",
        border_style="cyan",
    ))

    payload = build_payload(prompt_text, model, chat_id, parent_id, platform)
    headers = extra_headers(cfg["base_url"], chat_id)
    params = {"chat_id": chat_id}

    # Tambahkan WAF headers statis kalau kamu mau (opsional, biasanya bisa skip dulu)
    # headers.update({"bx-ua": "...", "bx-umidtoken": "...", "bx-v": "2.5.37"})

    endpoints = pick_endpoints(platform)
    for endpoint in endpoints:
        with client.stream("POST", endpoint, json=payload, params=params,
                           headers=headers, timeout=120) as resp:
            if resp.status_code != 200:
                console.print(f"[red]✗ {resp.status_code}[/red] | {resp.read().decode()[:300]}")
                continue

            full, think, raw_buf = [], [], []
            fatal_msg = None

            if pretty:
                with Live(console=console, refresh_per_second=12, vertical_overflow="visible") as live:
                    for kind, chunk in iter_chunks(resp, raw=args.raw):
                        if kind == "raw":
                            raw_buf.append(chunk)
                            continue
                        if kind == "fatal":
                            fatal_msg = chunk
                            break
                        if kind == "think":
                            think.append(chunk)
                        else:
                            full.append(chunk)
                        parts = []
                        if think:
                            parts.append(Text("🤔 " + "".join(think)[-1500:], style="dim italic"))
                        if full:
                            parts.append(Markdown("".join(full)))
                        live.update(Group(*parts) if parts else Text("…"))
            else:
                for kind, chunk in iter_chunks(resp, raw=args.raw):
                    if kind == "raw":
                        raw_buf.append(chunk)
                        continue
                    if kind == "fatal":
                        fatal_msg = chunk
                        break
                    if kind == "think":
                        think.append(chunk)
                        console.print(chunk, style="dim italic", end="", soft_wrap=True)
                    else:
                        full.append(chunk)
                        console.print(chunk, end="", soft_wrap=True)

            if fatal_msg:
                console.print(f"[red]✗ Server menolak:[/red] {fatal_msg}")
                return False

            if full or think:
                obj = get_chat(client, cfg["base_url"], chat_id)
                new_parent = (_deep_get(obj, {"currentId", "current_id", "current_node"})
                              if obj else parent_id)
                save_session(platform, chat_id, new_parent)
                with open(CACHE_FILE, "w") as f:
                    json.dump({platform: endpoint}, f)
                console.print(f"\n[bold green]✅ DONE[/bold green] [dim]({endpoint})[/dim]")
                return True

            preview = f"[content-type: {resp.headers.get('content-type','')}]\n" + "\n".join(raw_buf)[:1000]
            console.print("\n[yellow]⚠ Parser belum ngerti format response.[/yellow]")
            console.print(Panel(preview, title="raw preview", border_style="yellow"))
            return False
    return False


# ---------- REPL ----------

def repl(client, args):
    platform = args.platform
    model = args.model
    cfg = PLATFORMS[platform]
    console.print(Panel.fit(
        f"[bold cyan]Qwen Coder CLI — mode interaktif ({platform.upper()})[/bold cyan]\n"
        "[dim]/new[/dim] = sesi baru | [dim]/model <nama>[/dim] = ganti model | "
        "[dim]/exit[/dim] = keluar",
        border_style="cyan",
    ))
    while True:
        try:
            user = console.input("[bold green]qwen>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye bro 🥷[/dim]")
            break
        if not user:
            continue
        if user in ("/exit", "/quit"):
            console.print("[dim]bye bro [/dim]")
            break
        if user == "/new":
            reset_session(platform)
            console.print(f"[cyan]🆕 Sesi {platform} direset.[/cyan]")
            continue
        if user.startswith("/model"):
            parts = user.split(maxsplit=1)
            model = parts[1].strip() if len(parts) > 1 else cfg["default_model"]
            console.print(f"[cyan]model -> {model}[/cyan]")
            continue
        files_ctx = read_context_files(args.file)
        local_ctx = get_local_context()
        ask(client, local_ctx + "\n" + build_final_prompt(user, files_ctx, ""), model, platform, args)


def main():
    ap = argparse.ArgumentParser(description="Qwen Coder CLI — ninja edition 🥷")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--model", default=None)
    ap.add_argument("--chat-id", default=None)
    ap.add_argument("--file", action="append", default=None)
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--platform", choices=["chat", "coder"], default="chat",
                    help="Target platform: chat (default) or coder")
    args = ap.parse_args()

    stdin_text = "" if sys.stdin.isatty() else sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()
    client = build_client()

    if args.new:
        reset_session(args.platform)

    prompt = " ".join(args.prompt)
    if not prompt and not stdin_text:
        repl(client, args)
        return
    if not prompt:
        prompt = "Analisis input berikut dan berikan ringkasan serta rekomendasi singkat."

    files_ctx = read_context_files(args.file)
    local_ctx = get_local_context()
    ask(client, local_ctx + "\n" + build_final_prompt(prompt, files_ctx, stdin_text),
        args.model, args.platform, args)


if __name__ == "__main__":
    main()