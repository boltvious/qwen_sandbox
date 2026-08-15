"""
CLI interface for Qwen Sandbox with Qwen Coder API integration
"""

import click
import sys
from typing import Optional

from .auth import QwenAuth
from .sandbox import CodeSandbox


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """Qwen Sandbox CLI - Safe code execution with Qwen Coder API"""
    pass


@cli.command()
@click.option('--username', '-u', default=None, help='Qwen account username/email')
@click.option('--password', '-p', default=None, help='Qwen account password')
def login(username: str, password: str):
    """Login with Qwen account credentials to get API token"""
    auth = QwenAuth()
    
    # If credentials not provided via options, prompt for them
    if not username:
        username = click.prompt('Username/Email')
    if not password:
        password = click.prompt('Password', hide_input=True)
    
    click.echo("Authenticating with Qwen Coder API...")
    result = auth.login(username, password)
    
    if result.get("success"):
        user_info = result.get("user", {})
        click.echo(click.style(f"✓ Login successful! Welcome, {user_info.get('username', 'User')}", fg='green'))
        click.echo(f"  User ID: {user_info.get('id')}")
        click.echo(f"  Session expires: {result.get('expires_at', 'N/A')}")
        click.echo(f"  API Endpoint: {auth.api_url}")
    else:
        error = result.get("error", "Unknown error")
        click.echo(click.style(f"✗ Login failed: {error}", fg='red'))
        sys.exit(1)


@cli.command()
def logout():
    """Logout and clear saved credentials"""
    auth = QwenAuth()
    
    if auth.is_authenticated():
        auth.logout()
        click.echo(click.style("✓ Logged out successfully", fg='green'))
    else:
        click.echo("Not currently logged in")


@cli.command()
def status():
    """Check authentication status"""
    auth = QwenAuth()
    
    if auth.is_authenticated():
        user_info = auth.get_user_info()
        click.echo(click.style("✓ Authenticated", fg='green'))
        click.echo(f"  Username: {user_info.get('username', 'Unknown')}")
        click.echo(f"  User ID: {user_info.get('id', 'Unknown')}")
        click.echo(f"  API Endpoint: {auth.api_url}")
    else:
        click.echo(click.style("✗ Not authenticated", fg='red'))
        click.echo("  Use 'qwen-sandbox login' to authenticate")


@cli.command()
@click.option('--code', '-c', default=None, help='Code to execute')
@click.option('--file', '-f', type=click.File('r'), help='File containing code to execute')
@click.option('--api/--local', default=False, help='Use Qwen Coder API instead of local execution')
@click.option('--model', '-m', default='qwen-turbo', help='Qwen model to use (for API mode)')
def run(code: Optional[str], file, api: bool, model: str):
    """Execute code in the sandbox"""
    auth = QwenAuth()
    
    # Check authentication
    if not auth.is_authenticated():
        click.echo(click.style("Error: Not authenticated", fg='red'))
        click.echo("Please login first: qwen-sandbox login")
        sys.exit(1)
    
    # Get code from option or file
    if code:
        code_to_run = code
    elif file:
        code_to_run = file.read()
    else:
        click.echo(click.style("Error: No code provided", fg='red'))
        click.echo("Use --code or --file to provide code")
        sys.exit(1)
    
    # Get auth token for API mode
    auth_token = auth.get_token() if api else None
    
    # Execute code
    sandbox = CodeSandbox(
        api_url=auth.api_url if api else None,
        auth_token=auth_token,
        timeout=30
    )
    result = sandbox.execute(code_to_run, use_api=api)
    
    # Display results
    if result["output"]:
        click.echo(result["output"])
    
    if result["error"]:
        click.echo(click.style(result["error"], fg='red'), err=True)
    
    sys.exit(result["exit_code"])


@cli.command()
@click.option('--api/--local', default=False, help='Use Qwen Coder API instead of local execution')
@click.option('--model', '-m', default='qwen-turbo', help='Qwen model to use (for API mode)')
def interactive(api: bool, model: str):
    """Start interactive mode"""
    auth = QwenAuth()
    
    # Check authentication
    if not auth.is_authenticated():
        click.echo(click.style("Error: Not authenticated", fg='red'))
        click.echo("Please login first: qwen-sandbox login")
        sys.exit(1)
    
    user_info = auth.get_user_info()
    mode_str = "API Mode" if api else "Local Mode"
    click.echo(click.style(f"Welcome to Qwen Sandbox Interactive Mode ({mode_str}), {user_info.get('username')}!", fg='cyan'))
    click.echo("Type 'exit' or 'quit' to exit, 'clear' to clear screen")
    click.echo("-" * 60)
    
    # Get auth token for API mode
    auth_token = auth.get_token() if api else None
    
    sandbox = CodeSandbox(
        api_url=auth.api_url if api else None,
        auth_token=auth_token,
        timeout=30
    )
    
    while True:
        try:
            # Get input
            code = click.prompt(click.style(">>>", fg='green'), prompt_suffix=' ')
            
            # Check for exit commands
            if code.strip().lower() in ('exit', 'quit'):
                click.echo("Goodbye!")
                break
            
            # Check for clear command
            if code.strip().lower() == 'clear':
                click.clear()
                continue
            
            # Execute code
            result = sandbox.execute(code, use_api=api)
            
            # Display results
            if result["output"]:
                click.echo(result["output"])
            
            if result["error"]:
                click.echo(click.style(result["error"], fg='red'), err=True)
                
        except KeyboardInterrupt:
            click.echo("\nUse 'exit' to quit")
            continue
        except EOFError:
            click.echo("\nGoodbye!")
            break


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
