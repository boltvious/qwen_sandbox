# coder_cli.py â€” Qwen Coder Platform CLI 
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
from rich.prompt import Prompt

# Import dari client.py yang udah ada (cookie extractor)
from client import build_client

console = Console()

BASE_URL = "https://coder.qwen.ai"
DEFAULT_MODEL = "qwen3-coder-plus"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, ".coder_cache.json")
SESSION_FILE = os.path.join(SCRIPT_DIR, ".coder_session.json")
MAX_FILE_CHARS = 100_000

# Taruh di atas, setelah import
DEFAULT_ENV_ID = "381f04eb-56b9-44dc-a863-882b27824fea"
DEFAULT_REPO = {
    "repository": "boltvious/qwen_sandbox",
    "git_provider": "github",
    "selected_branch": "main"
}

# ---------- Project Scanner ----------
IGNORE_DIRS = {
    ".git", "venv", "node_modules", "__pycache__", ".idea", ".vscode",
    "dist", "build", ".next", "coverage", ".egg-info",
}
KEY_FILES = [
    "README.md", "readme.md", "agent.md", "package.json", "pyproject.toml",
    "requirements.txt", "setup.py", "Makefile", "main.py", "app.py",
    "index.js", "index.ts", "config.json", ".env.example",
]
MAX_TREE_LINES = 150
MAX_KEY_FILE_CHARS = 6000

# ---------- GitHub Token Management ----------
GITHUB_TOKEN_FILE = os.path.join(SCRIPT_DIR, ".github_token")


def get_github_token(args) -> str | None:
    """Ambil GitHub PAT dari: args → env → file lokal."""
    # 1) Argumen CLI
    if hasattr(args, "github_token") and args.github_token:
        return args.github_token.strip()
    # 2) Environment variable
    env_tok = os.getenv("GITHUB_TOKEN")
    if env_tok:
        return env_tok.strip()
    # 3) File lokal
    if os.path.exists(GITHUB_TOKEN_FILE):
        try:
            with open(GITHUB_TOKEN_FILE) as f:
                tok = f.read().strip()
            if tok:
                return tok
        except Exception:
            pass
    return None


def inject_token_to_repo_url(repo: str, token: str) -> str:
    """Inject PAT ke URL git HTTPS supaya sandbox bisa clone repo private."""
    # Format modern GitHub: https://x-access-token:<token>@github.com/...
    if repo.startswith("https://"):
        # Ganti https://github.com/owner/repo → https://x-access-token:TOKEN@github.com/owner/repo
        return repo.replace("https://", f"https://x-access-token:{token}@", 1)
    if repo.startswith("git@github.com:"):
        # Convert SSH → HTTPS with token
        path = repo.replace("git@github.com:", "")
        return f"https://x-access-token:{token}@github.com/{path}"
    # Fallback: anggap owner/repo
    return f"https://x-access-token:{token}@github.com/{repo}.git"

def scan_project(root=".", max_depth=3):
    """Return (tree_text, list_key_file_paths)."""
    root = os.path.abspath(root)
    lines = [os.path.basename(root) + "/"]
    key_files = []
    truncated = False

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in IGNORE_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirnames[:] = []
        indent = "  " * (depth + 1)

        for d in dirnames:
            if len(lines) < MAX_TREE_LINES:
                lines.append(f"{indent}{d}/")

        for f in sorted(filenames):
            if len(lines) < MAX_TREE_LINES:
                lines.append(f"{indent}{f}")
            full = os.path.join(dirpath, f)
            try:
                if (f in KEY_FILES and len(key_files) < 5
                        and os.path.getsize(full) <= MAX_KEY_FILE_CHARS * 2):
                    key_files.append(full)
            except OSError:
                continue

        if len(lines) >= MAX_TREE_LINES:
            truncated = True
            break

    if truncated:
        lines.append("  â€¦ (truncated)")
    return "\n".join(lines), key_files

# ---------- Trust Directory (ala Codex) ----------
TRUST_FILE = os.path.join(SCRIPT_DIR, ".qwen_trust.json")


def _load_trusted():
    try:
        with open(TRUST_FILE) as f:
            return set(json.load(f).get("trusted", []))
    except Exception:
        return set()


def ask_trust(path="."):
    path = os.path.abspath(path)
    if path in _load_trusted():
        return True  # udah pernah di-yes-in, langsung gas

    console.print(f"\n[bold white]> You are in {path}[/bold white]\n")
    console.print(
        "Do you trust the contents of this directory? Working with untrusted "
        "contents comes with higher risk of prompt injection. Trusting the "
        "directory allows project scanning & auto-attach key files.\n"
    )
    console.print("  [bold cyan]1.[/bold cyan] Yes, continue")
    console.print("  [bold cyan]2.[/bold cyan] No, skip scan")

    choice = Prompt.ask("\n> Pilih", choices=["1", "2"], default="1")
    if choice == "1":
        trusted = _load_trusted()
        trusted.add(path)
        with open(TRUST_FILE, "w") as f:
            json.dump({"trusted": sorted(trusted)}, f, indent=2)
        console.print("[dim]ðŸ’¾ Disimpan â€” folder ini nggak akan ditanya lagi.[/dim]")
        return True
    return False

def get_env_config(client, env_id=None, repo_info=None):
    env_id = env_id or DEFAULT_ENV_ID
    repo_info = repo_info or DEFAULT_REPO
    return {
        "env_id": env_id,
        "meta": {
            "repo_info": repo_info,
            "env_info": {"env_name": "qwen_sandbox"}
        }
    }
# ---------- Util ----------

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
    """Headers sesuai format coder.qwen.ai (bukan chat!)."""
    return {
        # Note: NO 'source', NO 'timezone' untuk coder platform
        "version": "0.0.26",  # <-- INI PENTING! Beda dari chat.qwen.ai
        "x-request-id": str(uuid.uuid4()),
        "x-accel-buffering": "no",
        "referer": f"{BASE_URL}/c/{chat_id}",
        # bx-ua & bx-umidtoken opsional - kalau kena 403, uncomment & isi manual:
        # "bx-ua": "",
        # "bx-umidtoken": "",
        "bx-v": "2.5.37",
    }


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


# ---------- Session Management ----------

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

def _url(path: str) -> str:
    """Gabungkan BASE_URL + path jadi URL absolut."""
    return f"{BASE_URL}{path}"
# ---------- Chat Management ----------

def get_chat(client, chat_id):
    """Ambil info chat dari API."""
    paths = [
        f"/coder/api/v2/task/{chat_id}",
        f"/coder/api/v2/chats/{chat_id}",
        f"/api/v2/chats/{chat_id}",
    ]
    for path in paths:
        try:
            r = client.get(_url(path))
            if r.status_code == 200:
                obj = r.json()
                if isinstance(obj, dict) and obj.get("success") is not False:
                    return obj
        except Exception:
            continue
    return None


def create_chat(client, chat_id, title="coder-cli", env_id=None, repo_info=None):
    env_config = get_env_config(client, env_id, repo_info)
    
    payload = {
        "chat_id": chat_id,
        "title": title,
        **env_config  # inject env_id & meta
    }

    paths = ["/coder/api/v2/chats/", "/coder/api/v2/chats/new"]
    for path in paths:
        try:
            r = client.post(_url(path), json=payload)
            if r.status_code in (200, 201):
                try:
                    obj = r.json()
                    if isinstance(obj, dict) and obj.get("success") is not False:
                        console.print(f"[green]âœ… Chat + environment created:[/green] {chat_id[:8]}â€¦")
                        return True
                except Exception:
                    return True
        except Exception:
            continue
    return False

def get_latest_chat_id(client):
    """Ambil chat terbaru dari history web."""
    paths = [
        "/coder/api/v2/chats/?page=1",
        "/coder/api/v2/chats?page_num=1&page_size=10",
        "/coder/api/v2/chats/",
    ]
    for path in paths:
        try:
            r = client.get(_url(path))
            if r.status_code != 200:
                continue
            obj = r.json()
            data = _data_of(obj)
            items = (data if isinstance(data, list)
                     else (data.get("items") or data.get("list") or data.get("chats") or [])
                     if isinstance(data, dict) else [])
            for it in items:
                if isinstance(it, dict):
                    cid = it.get("id") or it.get("chat_id") or it.get("chatId")
                    if isinstance(cid, str) and "-" in cid and len(cid) > 8:
                        return cid
        except Exception:
            continue
    return None


def ensure_chat(client, wanted_id=None):
    """Pastikan kita punya chat_id yang valid."""
    if wanted_id:
        obj = get_chat(client, wanted_id)
        parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
        return wanted_id, parent

    # Coba ambil chat terbaru dari web
    latest = get_latest_chat_id(client)
    if latest:
        console.print(f"[cyan]ðŸ“Ž Numpang di chat terbaru (coder):[/cyan] {latest[:8]}â€¦")
        obj = get_chat(client, latest)
        parent = _deep_get(obj, {"currentId", "current_id", "current_node"}) if obj else None
        return latest, parent

    # Coba buat chat baru
    chat_id = str(uuid.uuid4())
    if create_chat(client, chat_id):
        if get_chat(client, chat_id) is not None:
            console.print(f"[green]ðŸ“ Chat baru dibuat (coder):[/green] {chat_id[:8]}â€¦")
            return chat_id, None

    # Fallback
    console.print("[yellow]âš  Nggak ada history & gagal create via API.[/yellow]")
    console.print("[cyan]ðŸ’¡ Buka coder.qwen.ai, kirim 1 pesan manual, lalu coba lagi.[/cyan]")
    return None, None


# ---------- File Context ----------

def read_context_files(paths):
    parts = []
    for p in paths or []:
        try:
            with open(p, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")
        except Exception as exc:
            console.print(f"[yellow]âš  gagal baca {p}: {exc}[/yellow]")
            continue
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n... (truncated)"
            console.print(f"[yellow] {p} kepotong (>{MAX_FILE_CHARS} char)[/yellow]")
        parts.append(f'<file name="{p}">\n{content}\n</file>')
    return "\n\n".join(parts)


def get_coder_system_prompt():
    import platform
    return (
        f"<system_instruction>\n"
        f"ROLE: You are an expert coding assistant.\n"
        f"USER_CONTEXT: The user is working locally on {platform.system()} in {os.getcwd()}.\n"
        f"CONSTRAINT: You run on a remote server and CANNOT directly access the local filesystem.\n"
        f"WORKFLOW: The CLI tool reads local files and injects them into this prompt.\n"
        f"TOOL - READ FILE: If you need to see a file that is NOT in the current context, "
        f"you MUST output EXACTLY this format on a new line: <read_file>filename.py</read_file>\n"
        f"The CLI will automatically read the file and feed it back to you. Do not guess file contents.\n"
        f"TASK: Analyze the injected code. Provide refactoring, bug fixes, or explanations.\n"
        f"</system_instruction>\n"
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


# ---------- Payload Builder ----------

# Di build_payload(), tambahkan env & meta ke root payload:
def build_payload(prompt: str, model: str, chat_id: str, parent_id=None, env_id=None, repo_info=None) -> dict:
    meta = env_config["meta"].copy()
    if github_token and "repo_info" in meta:
        repo_info = meta["repo_info"].copy()
        original_repo = repo_info.get("repository", "")
        repo_info["repository"] = inject_token_to_repo_url(original_repo, github_token)
        meta["repo_info"] = repo_info
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
        "model": model or DEFAULT_MODEL,
        "env_id": env_config["env_id"],  # <-- INI KUNCI NYA
        "meta": meta,
        "messages": [{
            "id": None,
            "fid": fid,
            "parentId": None,
            "childrenIds": [child],
            "role": "user",
            "content": prompt,
            "user_action": "chat",
            "files": [],
            "timestamp": ts,
            "models": [model or DEFAULT_MODEL],
            "model": "",
            "chat_type": "code",
            "feature_config": {"thinking_enabled": False, "output_schema": "phase"},
            "extra": {"meta": {"subChatType": "code"}},
            "sub_chat_type": "code",
            "parent_id": parent_id,
        }],
        "timestamp": ts,
    }


def extract_delta(obj):
    """Ekstrak text/thinking dari chunk SSE."""
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

# ---------- Streaming ----------

def _first_str(d: dict, *keys):
    if not isinstance(d, dict): return None
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v: return v
    return None

def iter_chunks(resp, raw=False):
    """Parser SSE yang support function event & nangkep response_id."""
    for line in resp.iter_lines():
        yield ("raw", line, None)
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

        rid = obj.get("response_id")  # <-- Ambil response_id

        if obj.get("success") is False:
            yield ("fatal", json.dumps(obj.get("data", {}), ensure_ascii=False)[:400], rid)
            return

        choices = obj.get("choices")
        if isinstance(choices, list) and choices:
            delta = choices[0].get("delta") or choices[0].get("message") or {}
            
            # 1. Handle Function/Agent event
            if delta.get("role") == "function":
                func = delta.get("extra", {}).get("function", {})
                yield ("function", {
                    "action": func.get("action", "Processing..."),
                    "status": func.get("status", "running"),
                    "detail": delta.get("content", "")
                }, rid)
                continue

            # 2. Handle standard text/thinking
            text = _first_str(delta, "content", "text")
            thinking = _first_str(delta, "reasoning_content", "thinking")
            if thinking: yield ("think", thinking, rid)
            if text: yield ("text", text, rid)
            if text or thinking: continue

        # 3. Fallback extraction (kalau struktur beda)
        if isinstance(obj.get("output"), dict):
            out = obj["output"]
            text = _first_str(out, "text", "content")
            if text: yield ("text", text, rid)
        else:
            text = _first_str(obj, "content", "text")
            thinking = _first_str(obj, "reasoning_content", "thinking")
            if thinking: yield ("think", thinking, rid)
            if text: yield ("text", text, rid)
def parse_chunk(obj):
    """Parse SSE JSON jadi event terstruktur + ambil response_id."""
    if not isinstance(obj, dict):
        return None

    response_id = obj.get("response_id")  # <-- Ambil ini

    choices = obj.get("choices")
    if isinstance(choices, list) and choices:
        delta = choices[0].get("delta", {})
        if delta.get("role") == "function":
            func = delta.get("extra", {}).get("function", {})
            return ("function", {
                "action": func.get("action", "Processing..."),
                "status": func.get("status", "running"),
                "detail": delta.get("content", "")
            }, response_id)
        content = delta.get("content")
        if content:
            return ("text", content, response_id)
        reasoning = delta.get("reasoning_content")
        if reasoning:
            return ("thinking", reasoning, response_id)

    if obj.get("success") is False:
        return ("error", json.dumps(obj.get("data", {}), ensure_ascii=False), response_id)
    if "response.created" in obj:
        return ("meta", obj.get("response.created", {}), response_id)
    return None

def stream_chat(client, endpoint: str, payload: dict, raw=False, pretty=True):
    headers = extra_headers(payload["chatId"])
    params = {"chat_id": payload["chatId"]}
    full_text, full_think = [], []
    current_func = None
    last_response_id = None  # <-- Track response_id terakhir

    with client.stream("POST", _url(endpoint), json=payload, params=params,
                       headers=headers, timeout=120) as resp:
        if resp.status_code != 200:
            return resp.status_code, None, resp.read().decode(), False, None

        if pretty:
            with Live(console=console, refresh_per_second=12,
                      vertical_overflow="visible") as live:
                for kind, chunk, rid in iter_chunks(resp, raw=raw):
                    if rid: last_response_id = rid  # <-- Simpan rid
                    if kind == "raw": continue
                    if kind == "fatal":
                        return 200, None, chunk, True, last_response_id

                    if kind == "function":
                        current_func = chunk
                    elif kind == "think":
                        full_think.append(chunk)
                    elif kind == "text":
                        full_text.append(chunk)

                    panels = []
                    if current_func:
                        icon = "â³" if current_func["status"] == "running" else "âœ…"
                        color = "cyan" if current_func["status"] == "running" else "green"
                        panels.append(Panel(
                            f"{icon} [bold]{current_func['action']}[/bold]\n[dim]{current_func['detail']}[/dim]",
                            title="ðŸ¤– Coder Agent", border_style=color, expand=False
                        ))
                    if full_think:
                        panels.append(Text("ðŸ’­ " + "".join(full_think)[-500:], style="dim italic"))
                    if full_text:
                        panels.append(Markdown("".join(full_text)))

                    live.update(Group(*panels) if panels else Text("â³ Initializing..."))
        else:
            # Plain mode fallback
            for kind, chunk, rid in iter_chunks(resp, raw=raw):
                if rid: last_response_id = rid
                if kind == "raw": continue
                if kind == "fatal":
                    return 200, None, chunk, True, last_response_id
                if kind == "think":
                    console.print(chunk, style="dim italic", end="", soft_wrap=True)
                elif kind == "text":
                    console.print(chunk, end="", soft_wrap=True)

    # Return 5 tuple: status, text, extra, fatal, response_id
    return 200, "".join(full_text), None, False, last_response_id
# ---------- Main Logic ----------

import re  # <-- PASTIKAN INI ADA DI ATAS

def get_git_mode_prompt(repo=None, branch="main"):
    repo = repo or DEFAULT_REPO["repository"]
    return (
        "<git_mode>\n"
        f"The user's project is bound to your sandbox from github: {repo} (branch {branch}).\n"
        "The code lives in your /workspace. Use your shell/file tools to read, search, "
        "and run it DIRECTLY there.\n"
        "If the code looks stale, run `git pull` first.\n"
        "Do NOT ask the user to paste file contents â€” you already have full access.\n"
        "</git_mode>\n"
    )

def ask(client, full_prompt, model, args):
    chat_id, parent_id = ensure_chat(client, args.chat_id)
    if not chat_id:
        return False

    current_prompt = full_prompt
    max_loops = 3
    last_text = None  # Track teks terakhir buat save session

    # Ambil token SEKALI di luar loop (nggak perlu tiap iterasi)
    gh_token = get_github_token(args)
    if gh_token and args.git:
        console.print("[dim]🔑 GitHub token di-inject ke repo URL.[/dim]")
        console.print("[yellow]⚠ Token akan masuk ke payload API (server Qwen). "
                      "Pakai token expire pendek & revoke setelah uji coba.[/yellow]")

    for loop_count in range(max_loops):
        console.print(Panel.fit(
            f"[bold cyan]Qwen Coder CLI (coder.qwen.ai)[/bold cyan]\n"
            f"model: [green]{model or DEFAULT_MODEL}[/green] | chat: [dim]{chat_id[:8]}…{chat_id[-4:]}[/dim]",
            border_style="cyan",
        ))

        # Rebuild payload tiap iterasi (current_prompt berubah)
        payload = build_payload(current_prompt, model, chat_id, parent_id,
                                github_token=gh_token)
        endpoint = "/coder/api/v2/task/completions"

        if loop_count == 0:
            console.print(f"[yellow]➜ POST[/yellow] {_url(endpoint)}")

        status, text, extra, fatal, new_response_id = stream_chat(
            client, endpoint, payload, raw=args.raw, pretty=not args.plain
        )

        if fatal or status != 200:
            console.print(f"[red]✗ Error: {extra}[/red]")
            return False

        # Simpan text terakhir buat save session
        if text:
            last_text = text

        # 🔥 AGENTIC LOOP DETECTOR 🔥
        match = re.search(r'<read_file>(.*?)</read_file>', text or "",
                          re.IGNORECASE | re.DOTALL)

        if not match:
            # AI selesai, nggak minta file lagi
            break

        filename = match.group(1).strip()
        console.print(f"\n[bold yellow]🤖 AI minta akses baca: [cyan]{filename}[/cyan][/bold yellow]")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            current_prompt = (
                f"<tool_response>\n"
                f"Here is the content of {filename}:\n\n"
                f"{content}\n"
                f"</tool_response>\n\n"
                f"Continue your previous task based on this new file."
            )
            parent_id = new_response_id or parent_id
            console.print(f"[green]✅ File {filename} berhasil dibaca & dikirim balik ke AI...[/green]\n")

        except Exception as e:
            current_prompt = f"<tool_response>Error reading {filename}: {e}</tool_response>"
            parent_id = new_response_id or parent_id

    # Save session terakhir
    if last_text:
        save_session(chat_id, new_response_id or parent_id)
        console.print(f"\n[bold green]✅ DONE[/bold green] [dim]({endpoint})[/dim]")
        console.print(f"[dim]🔗 pantau di web: {BASE_URL}/c/{chat_id}[/dim]")
        return True

    return False
    
def repl(client, args):
    console.print(Panel.fit(
        "[bold cyan]codercode â€” interactive mode[/bold cyan]\n"
        "[dim]/new[/dim] = reset sesi | [dim]/exit[/dim] = keluar | Ctrl+C = bye",
        border_style="cyan",
    ))
    while True:
        try:
            user = console.input("[bold green]coder>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye bro ðŸ¥·[/dim]")
            break
        if not user:
            continue
        if user in ("/exit", "/quit"):
            console.print("[dim]bye bro ðŸ¥·[/dim]")
            break
        if user == "/new":
            reset_session()
            console.print("[cyan]ðŸ†• Sesi direset.[/cyan]")
            continue
        files_ctx = read_context_files(args.file)
        full = (get_coder_system_prompt() + "\n"
                + build_final_prompt(user, files_ctx, ""))
        ask(client, full, args.model, args)

def main():
    ap = argparse.ArgumentParser(description="Qwen Coder CLI (coder.qwen.ai) ðŸ¥·")
    # Di main(), tambah argument parser:
    ap.add_argument("--env-id", default=None, help="Environment ID")
    ap.add_argument("--repo", default=None, help="Repo string (owner/name)")
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--model", default=None, help="Model (default: qwen3-coder-plus)")
    ap.add_argument("--chat-id", default=None)
    ap.add_argument("--file", action="append", default=None, help="File konteks")
    ap.add_argument("--new", action="store_true", help="Sesi baru")
    ap.add_argument("--plain", action="store_true", help="Tanpa markdown live")
    ap.add_argument("--raw", action="store_true", help="Debug mode")
    ap.add_argument("--env", default="381f04eb-56b9-44dc-a863-882b27824fea",
                help="Environment ID (default: qwen_sandbox)")
    ap.add_argument("--scan", nargs="?", const=".", default=None,
                help="Scan folder proyek & inject struktur + file kunci")
    ap.add_argument("--git", action="store_true",
                help="Git mode: AI baca kode langsung dari sandbox repo (hemat token)")
    ap.add_argument("--push", action="store_true",
                help="(bareng --git) auto push dulu biar sandbox dapet kode terbaru")
    ap.add_argument("--github-token", default=None,
                help="GitHub Personal Access Token (atau set GITHUB_TOKEN env)")
    ap.add_argument("--save-token", action="store_true",
                help="Simpan --github-token ke file lokal .github_token")
    args = ap.parse_args()

        # Handle save GitHub token
    if args.save_token and args.github_token:
        with open(GITHUB_TOKEN_FILE, "w") as f:
            f.write(args.github_token.strip())
        os.chmod(GITHUB_TOKEN_FILE, 0o600)  # read/write only owner
        console.print(f"[green]✅ GitHub token tersimpan di {os.path.basename(GITHUB_TOKEN_FILE)}[/green]")

    stdin_text = "" if sys.stdin.isatty() else sys.stdin.buffer.read().decode("utf-8", errors="replace").strip()

    if args.new:
        reset_session()

    if args.git and args.push:
        import subprocess
        console.print("[cyan]ðŸ“¤ Sync lokal â†’ github...[/cyan]")
        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", "codercode sync", "--allow-empty"])
        subprocess.run(["git", "push"])

    prompt = " ".join(args.prompt)
    if not prompt and not stdin_text:
        client = build_client()
        repl(client, args)
        return

    if not prompt:
        prompt = "Analisis input berikut dan berikan ringkasan serta rekomendasi singkat."

    client = build_client()
    scan_ctx = ""
    if args.git:
        # GIT MODE: nggak inject apa-apa, AI ambil sendiri dari sandbox
        scan_ctx = get_git_mode_prompt()
    elif args.scan:
        if ask_trust(args.scan):
            tree, key_files = scan_project(args.scan)
            scan_ctx = f"<project_structure>\n{tree}\n</project_structure>\n"
            if key_files:
                scan_ctx += ("<key_files_auto_attached>\n"
                             + read_context_files(key_files)
                             + "\n</key_files_auto_attached>\n")
            console.print(f"[cyan]ðŸ“‚ Scan: {len(tree.splitlines())} baris tree "
                          f"+ {len(key_files)} key files injected[/cyan]")
        else:
            console.print("[yellow]âš  Scan dilewati â€” directory tidak dipercaya.[/yellow]")

    files_ctx = read_context_files(args.file)
    system_ctx = get_coder_system_prompt()
    full_prompt = (system_ctx + scan_ctx
                   + build_final_prompt(prompt, files_ctx, stdin_text))
    ask(client, full_prompt, args.model, args)

if __name__ == "__main__":
    main()

