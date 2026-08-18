# Qwen Coder CLI - Ninja Edition

## Project Overview
CLI unofficial untuk chat.qwen.ai via session cookie.

## Arsitektur
- auth.py: Ekstrak cookie via rookiepy
- client.py: HTTP client + header spoofing
- chat.py: Main CLI, streaming, REPL, memory
- pyproject.toml: Packaging
- .gitignore: Jaga file lokal

## Fitur
- Session-based auth
- Streaming + markdown
- Memory persistent (.session.json)
- Context: --file & pipe
- REPL mode

## Technical Fixes
1. App-Bound Encryption -> rookiepy + Edge
2. CHAT_NOT_FOUND -> GET verify + fallback
3. WAF -> inject source/version headers
4. Windows pipe -> sys.stdin.buffer + decode replace
5. WSL conflict -> prioritize Git Bash/PowerShell

## Usage
qwen-coder "prompt" --file app.py
cat code.py | qwen-coder "review"
qwen-coder  # REPL

## Security
Personal use only. Jaga cookie & session privat.
