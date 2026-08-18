# chat.py  (v5 — level-up A+B+C+D)
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime

from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from client import build_client

console = Console()

BASE_URL = "https://chat.qwen.ai"
DEFAULT_MODEL = "qwen3.8-max"
FALLBACK_CHAT_ID = "b5056d17-c582-46ac-907b-3d5a562311e0"

ENDPOINT_CANDIDATES = [
    "/api/v2/chat/completions",
    "/api/v2/completions",
    "/api/v2/chat",
    "/api/v2/chats/completions",
]

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


def extra_headers(chat_id: str) -> dict:
    return {
        "source": "web",
        "version": "0.2.86",
        "timezone": js_timezone(),
        "x-request-id": str(uuid.uuid4()),
        "x-accel-buffering": "no",
        "referer": f"{BASE_URL}/c/{chat_id}",
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

def load_session():
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_session(chat_id, parent_id):
    with open(SESSION_FILE, "w") as f:
        json.dump({"chat_id": chat_id, "parent_id": parent_id}, f)


def reset_session():
    try:
        os.remove(SESSION_FILE)
    except OSError:
        pass


# ---------- manajemen chat ----------

def get_chat(client, chat_id):
    for path in (f"/api/v2/chats/{chat_id}", f"/api/v2/chat/{chat_id}"):
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


def create_chat(client, chat_id, title="qwen-coder-cli"):
    paths = ["/api/v2/chats/new", "/api/v2/chats/", "/api/v2/chats"]
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


def get_latest_chat_id(client):
    for path in ("/api/v2/chats/?page=1", "/api/v2/chats?page=1", "/api/v2/chats/"):
        try:
            r = client.get(path)
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


def ensure_chat(client, wanted_id=None):
    if wanted_id:
        obj = get_chat(client, wanted_id)
        parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
        return wanted_id, parent

    chat_id = str(uuid.uuid4())
    if create_chat(client, chat_id):
        console.print(f"[green]📝 Chat baru dibuat:[/green] {chat_id[:8]}…")
        return chat_id, None

    console.print("[yellow]⚠ Nggak bisa buat chat baru via API, pakai chat existing.[/yellow]")
    latest = get_latest_chat_id(client) or FALLBACK_CHAT_ID
    obj = get_chat(client, latest)
    parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
    console.print(f"[cyan]📎 Numpang di chat:[/cyan] {latest[:8]}…")
    return latest, parent


# ---------- konteks file (fitur A) ----------

def read_context_files(paths):
    parts = []
    for p in paths or []:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as exc:
            console.print(f"[yellow]⚠ gagal baca {p}: {exc}[/yellow]")
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n... (truncated)"
            console.print(f"[yellow]⚠ {p} kepotong (>{MAX_FILE_CHARS} char)[/yellow]")
        parts.append(f'<file name="{p}">\n{content}\n</file>')
    return "\n\n".join(parts)


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

def build_payload(prompt: str, model: str, chat_id: str, parent_id=None) -> dict:
    ts = int(time.time())
    fid = str(uuid.uuid4())
    child = str(uuid.uuid4())
    return {
        "stream": True,
        "version": "2.1",
        "incremental_output": True,
        "chatId": chat_id, "parentId": parent_id,
        "chat_id": chat_id, "parent_id": parent_id,
        "chat_mode": "normal",
        "model": model,
        "messages": [{
            "id": None,
            "fid": fid,
            "parentId": parent_id,
            "childrenIds": [child],
            "role": "user",
            "content": prompt,
            "user_action": "chat",
            "files": [],
            "timestamp": ts,
            "models": [model],
            "model": "",
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
            "extra": {"meta": {"subChatType": "t2t"}},
            "sub_chat_type": "t2t",
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


def load_cached_endpoint():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f).get("endpoint")
        except Exception:
            return None
    return None


def pick_endpoints():
    cached = load_cached_endpoint()
    if cached:
        return [cached] + [e for e in ENDPOINT_CANDIDATES if e != cached]
    return ENDPOINT_CANDIDATES


# ---------- streaming ----------

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


def stream_chat(client, endpoint, payload, raw=False, pretty=True):
    headers = extra_headers(payload["chatId"])
    params = {"chat_id": payload["chatId"]}
    full, think, raw_buf = [], [], []

    with client.stream("POST", endpoint, json=payload, params=params,
                       headers=headers, timeout=120) as resp:
        if resp.status_code != 200:
            body = resp.read().decode("utf-8", "replace")
            return resp.status_code, None, body, False

        ctype = resp.headers.get("content-type", "")
        fatal_msg = None

        if pretty:
            with Live(console=console, refresh_per_second=12,
                      vertical_overflow="visible") as live:
                for kind, chunk in iter_chunks(resp, raw=raw):
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
                        parts.append(Text("🤔 " + "".join(think)[-1500:],
                                          style="dim italic"))
                    if full:
                        parts.append(Markdown("".join(full)))
                    live.update(Group(*parts) if parts else Text("…"))
        else:
            for kind, chunk in iter_chunks(resp, raw=raw):
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
            return 200, None, f"SERVER ERROR: {fatal_msg}", True

        if not full and not think:
            preview = f"[content-type: {ctype}]\n" + "\n".join(raw_buf)[:1000]
            return 200, None, preview, False

        return 200, "".join(full), None, False


# ---------- inti ----------

def ask(client, prompt_text, model, args):
    chat_id, parent_id = None, None

    if args.chat_id:
        chat_id = args.chat_id
        obj = get_chat(client, chat_id)
        parent_id = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
    else:
        sess = load_session()
        if sess and sess.get("chat_id"):
            obj = get_chat(client, sess["chat_id"])
            if obj is not None:
                chat_id = sess["chat_id"]
                parent_id = (sess.get("parent_id")
                             or _deep_get(obj, {"currentId", "current_id", "current_node"}))
        if not chat_id:
            chat_id, parent_id = ensure_chat(client)

    console.print(Panel.fit(
        f"[bold cyan]Qwen Coder CLI[/bold cyan]\n"
        f"model: [green]{model}[/green] | chat: [dim]{chat_id[:8]}…[/dim]",
        border_style="cyan",
    ))

    payload = build_payload(prompt_text, model, chat_id, parent_id)

    for endpoint in pick_endpoints():
        status, text, extra, fatal = stream_chat(client, endpoint, payload,
                                                 raw=args.raw, pretty=not args.plain)
        if fatal:
            console.print(f"[red]✗ Server menolak request:[/red] {extra}")
            return False

        if status != 200:
            console.print(f"[red]✗ {status}[/red] | {str(extra)[:300]}")
            if status in (401, 403):
                console.print("[yellow]Kemungkinan kena WAF (bx-ua). Kabarin aku.[/yellow]")
                return False
            continue

        with open(CACHE_FILE, "w") as f:
            json.dump({"endpoint": endpoint}, f)

        if text:
            obj = get_chat(client, chat_id)
            new_parent = (_deep_get(obj, {"currentId", "current_id", "current_node"})
                          if obj else parent_id)
            save_session(chat_id, new_parent)
            console.print(f"\n[bold green]✅ DONE[/bold green] [dim]({endpoint})[/dim]")
            return True

        console.print("\n[yellow]⚠ Status 200 tapi parser belum ngerti formatnya.[/yellow]")
        console.print(Panel(extra or "", title="raw preview", border_style="yellow"))
        return False
    return False


# ---------- REPL (fitur D) ----------

def repl(client, args):
    model = args.model
    console.print(Panel.fit(
        "[bold cyan]Qwen Coder CLI — mode interaktif[/bold cyan]\n"
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
            console.print("[dim]bye bro 🥷[/dim]")
            break
        if user == "/new":
            reset_session()
            console.print("[cyan]🆕 Sesi lokal direset. Chat baru di request berikutnya.[/cyan]")
            continue
        if user.startswith("/model"):
            parts = user.split(maxsplit=1)
            model = parts[1].strip() if len(parts) > 1 else DEFAULT_MODEL
            console.print(f"[cyan]model -> {model}[/cyan]")
            continue
        files_ctx = read_context_files(args.file)
        ask(client, build_final_prompt(user, files_ctx, ""), model, args)


def main():
    ap = argparse.ArgumentParser(description="Qwen Coder CLI — ninja edition 🥷")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--chat-id", default=None)
    ap.add_argument("--file", action="append", default=None,
                    help="file konteks (bisa lebih dari satu)")
    ap.add_argument("--new", action="store_true", help="mulai percakapan baru")
    ap.add_argument("--plain", action="store_true",
                    help="streaming teks polos tanpa markdown live")
    ap.add_argument("--raw", action="store_true")
    args = ap.parse_args()

    stdin_text = "" if sys.stdin.isatty() else sys.stdin.read().strip()

    client = build_client()

    if args.new:
        reset_session()

    prompt = " ".join(args.prompt)

    if not prompt and not stdin_text:
        repl(client, args)
        return

    if not prompt:
        prompt = "Analisis input berikut dan berikan ringkasan serta rekomendasi singkat."

    files_ctx = read_context_files(args.file)
    ask(client, build_final_prompt(prompt, files_ctx, stdin_text), args.model, args)


if __name__ == "__main__":
    main()