from __future__ import annotations

import rookiepy
from rich.console import Console
from rich.table import Table

console = Console()

# Domain bisa beda-beda tergantung web resminya pakai domain apa.
# Sementara kita coba beberapa kemungkinan.
DOMAINS = [
    "qwen.coder.ai",
    ".qwen.coder.ai",
    "qwen.ai",
    ".qwen.ai",
    "chat.qwen.ai",
    ".chat.qwen.ai",
]


def get_browser_loaders():
    loaders = [
        ("Chrome", getattr(rookiepy, "chrome", None)),
        ("Edge", getattr(rookiepy, "edge", None)),
        ("Brave", getattr(rookiepy, "brave", None)),
    ]

    return [(name, fn) for name, fn in loaders if callable(fn)]


def extract_cookies():
    all_cookies = []

    table = Table(title="Hasil scan cookie Qwen Coder")
    table.add_column("Browser", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Jumlah", justify="right")

    for name, loader in get_browser_loaders():
        try:
            cookies = loader(domains=DOMAINS)

            if cookies:
                table.add_row(name, "[green]OK[/green]", str(len(cookies)))
                all_cookies.extend(cookies)
            else:
                table.add_row(name, "[yellow]Kosong[/yellow]", "0")

        except Exception as exc:
            table.add_row(name, f"[red]Error: {exc}[/red]", "0")

    console.print(table)
    return all_cookies


def summarize_cookies(cookies):
    if not cookies:
        console.print("[red]Nggak ada cookie yang ketemu bro.[/red]")
        console.print("Pastikan kamu sudah login di browser, atau domainnya belum cocok.")
        return

    names = sorted({cookie.get("name", "?") for cookie in cookies if cookie.get("name")})

    console.print(f"\n[green]Total cookie ketemu:[/green] [bold]{len(cookies)}[/bold]")
    console.print("\n[bold]Nama cookie:[/bold]")
    console.print(", ".join(names[:30]) + ("..." if len(names) > 30 else ""))

    console.print("\n[yellow]Penting: jangan print/share value cookie ke mana-mana.[/yellow]")
    console.print("[yellow]Value cookie itu kayak password session akun kamu.[/yellow]")


def to_simple_cookie_dict(cookies):
    """
    Ubah list cookie jadi dict sederhana:
    {
        "nama_cookie": "value_cookie"
    }

    Nanti ini bisa dipakai buat header Cookie di httpx/requests.
    """
    result = {}

    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")

        if name is not None and value is not None:
            result[name] = value

    return result


if __name__ == "__main__":
    cookies = extract_cookies()
    summarize_cookies(cookies)

    # Kalau mau test dict cookie, uncomment bagian ini.
    # Tapi jangan sembarangan print value-nya.

    # cookie_dict = to_simple_cookie_dict(cookies)
    # print(cookie_dict.keys())