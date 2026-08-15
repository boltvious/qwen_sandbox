# Codex CLI Sandbox Clone with Qwen Login

A command-line interface sandbox that integrates with Qwen AI models, featuring user authentication via Qwen account.

## Features

- **Qwen Account Authentication**: Secure login using Qwen credentials
- **Sandboxed Code Execution**: Safe execution environment for code snippets
- **CLI Interface**: Easy-to-use command-line interface
- **Session Management**: Persistent login sessions

## Installation

```bash
pip install -e .
```

Or install dependencies only:

```bash
pip install -r requirements.txt
```

## Usage

### Login
```bash
qwen-sandbox login
# Or with credentials directly:
qwen-sandbox login --username your@email.com --password yourpassword
```

### Check Status
```bash
qwen-sandbox status
```

### Run Code in Sandbox
```bash
qwen-sandbox run --code 'print("Hello, World!")'
```

### Run Code from File
```bash
qwen-sandbox run --file script.py
```

### Interactive Mode
```bash
qwen-sandbox interactive
```

### Logout
```bash
qwen-sandbox logout
```

## Commands

- `login` - Authenticate with Qwen account
- `logout` - Clear saved credentials
- `status` - Check authentication status
- `run` - Execute code in the sandbox
- `interactive` - Start interactive REPL mode

## Configuration

Create a `.env` file in the root directory for API configuration:
```
QWEN_API_KEY=your_api_key_here
QWEN_API_URL=https://api.qwen.ai
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
    ├── auth.py         # Authentication module
    ├── sandbox.py      # Code execution sandbox
    └── cli.py          # CLI interface
```

## Security Features

- Restricted built-in functions (eval, exec, open, etc.)
- AST-based code validation
- Sandboxed execution environment
- Session-based authentication with expiration

## License

MIT
