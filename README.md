# Qwen Sandbox CLI - Codex CLI Clone with Qwen Coder API

A command-line interface sandbox that integrates with **Qwen Coder API** (`https://coder.qwen.ai/coder/api/v2/task/completions`), featuring user authentication via Qwen account with token-based login.

## Features

- **Qwen Account Authentication**: Secure login using Qwen credentials to get API tokens
- **Qwen Coder API Integration**: Send code to `https://coder.qwen.ai/coder/api/v2/task/completions` for execution
- **Dual Execution Modes**: Local sandbox or remote API execution
- **Token-Based Authentication**: Bearer token authentication for API requests
- **Sandboxed Code Execution**: Safe local execution environment with restricted built-ins
- **CLI Interface**: Easy-to-use command-line interface
- **Session Management**: Persistent login sessions with 30-day expiration
- **Interactive Mode**: REPL-style interactive coding environment

## Installation

```bash
pip install -e .
```

Or install dependencies only:

```bash
pip install -r requirements.txt
```

## Usage

### Login (Get API Token)
```bash
qwen-sandbox login
# Or with credentials directly:
qwen-sandbox login --username your@email.com --password yourpassword
```

### Check Status
```bash
qwen-sandbox status
```

### Run Code Locally (Default)
```bash
qwen-sandbox run --code 'print("Hello, World!")'
```

### Run Code via Qwen Coder API
```bash
qwen-sandbox run --code 'print("Hello from Qwen API!")' --api
```

### Run Code from File
```bash
qwen-sandbox run --file script.py
qwen-sandbox run --file script.py --api  # Via API
```

### Interactive Mode
```bash
qwen-sandbox interactive              # Local mode
qwen-sandbox interactive --api        # API mode
```

### Logout
```bash
qwen-sandbox logout
```

## Commands

| Command | Description |
|---------|-------------|
| `login` | Authenticate with Qwen account and get API token |
| `logout` | Clear saved credentials |
| `status` | Check authentication status |
| `run` | Execute code in sandbox (local or API) |
| `interactive` | Start interactive REPL mode |

## Options for `run` and `interactive`

| Option | Description |
|--------|-------------|
| `--code`, `-c` | Code string to execute |
| `--file`, `-f` | File containing code to execute |
| `--api` / `--local` | Toggle between API and local execution |
| `--model`, `-m` | Qwen model to use (default: qwen-turbo) |

## Configuration

Create a `.env` file in the root directory for API configuration:

```env
QWEN_API_KEY=your_api_key_here
QWEN_API_URL=https://coder.qwen.ai/coder/api/v2/task/completions
QWEN_AUTH_URL=https://coder.qwen.ai/coder/api/v2/auth/login
```

## Project Structure

```
/workspace
├── main.py              # Main entry point
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
├── README.md           # This file
└── qwen_sandbox/       # Package directory
    ├── __init__.py     # Package init
    ├── auth.py         # Authentication module (Qwen API login)
    ├── sandbox.py      # Code execution sandbox (local + API)
    └── cli.py          # CLI interface
```

## API Integration

### Authentication Flow

1. User runs `qwen-sandbox login` with credentials
2. CLI sends POST request to `https://coder.qwen.ai/coder/api/v2/auth/login`
3. Server returns authentication token
4. Token is stored securely in `~/.qwen_sandbox/credentials.json`
5. Token is used in `Authorization: Bearer <token>` header for API requests

### Code Execution via API

When using `--api` flag:

```python
POST https://coder.qwen.ai/coder/api/v2/task/completions
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json

Body:
{
  "code": "print('Hello')",
  "language": "python",
  "timeout": 30
}
```

## Security Features

- Restricted built-in functions (eval, exec, open, etc.) in local mode
- AST-based code validation
- Sandboxed execution environment
- Session-based authentication with expiration
- Secure token storage in user home directory
- Bearer token authentication for API requests

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QWEN_API_KEY` | None | Optional API key for additional authentication |
| `QWEN_API_URL` | `https://coder.qwen.ai/coder/api/v2/task/completions` | Code execution endpoint |
| `QWEN_AUTH_URL` | `https://coder.qwen.ai/coder/api/v2/auth/login` | Authentication endpoint |

## License

MIT

## Version

0.2.0 - Added Qwen Coder API integration
