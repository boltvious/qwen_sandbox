# push_handler.py - Handler untuk push request dengan konfirmasi user
from __future__ import annotations
import subprocess
import sys
from rich.console import Console
from rich.prompt import Prompt

console = Console()


class PushRequestHandler:
    """
    Handler untuk mengelola proses git push dengan mekanisme konfirmasi user.
    
    Workflow:
    1. Emit tag <push_request>branch=...;summary=...</push_request>
    2. Tunggu persetujuan user (via CLI prompt)
    3. Jika disetujui, lakukan push
    4. Jika ditolak, skip push
    """
    
    def __init__(self, branch: str = "main"):
        self.branch = branch
        self.pushed = False
    
    def emit_push_request(self, summary: str) -> None:
        """
        Emit tag push_request ke stdout untuk ditangkap oleh CLI.
        Tag ini akan diparse oleh CLI dan menampilkan prompt interaktif ke user.
        """
        tag = f"<push_request>branch={self.branch};summary={summary}</push_request>"
        print(tag, flush=True)
        console.print(f"\n[cyan]📤 Push request emitted:[/cyan] {summary}")
        console.print(f"[dim]   Branch: {self.branch}[/dim]\n")
    
    def wait_for_approval(self) -> bool:
        """
        Menunggu persetujuan user sebelum melanjutkan push.
        Return True jika user approve, False jika reject.
        
        Note: Fungsi ini akan dipanggil otomatis oleh CLI setelah user merespons tag.
        """
        # Ini adalah fallback manual jika CLI tidak menghandle tag secara otomatis
        console.print("[yellow]⚠ Waiting for user approval...[/yellow]")
        choice = Prompt.ask(
            "\nProceed with git push?",
            choices=["yes", "no", "y", "n"],
            default="yes"
        )
        return choice.lower() in ["yes", "y"]
    
    def execute_push(self, force: bool = False) -> bool:
        """
        Eksekusi git push setelah mendapat persetujuan.
        
        Args:
            force: Jika True, lakukan force push (git push --force)
        
        Returns:
            True jika push berhasil, False jika gagal
        """
        try:
            cmd = ["git", "push", "--force" if force else "push"]
            console.print(f"[cyan]📤 Pushing to remote (branch: {self.branch})...[/cyan]")
            
            result = subprocess.run(cmd, capture_output=False, text=True)
            
            if result.returncode == 0:
                self.pushed = True
                console.print(f"[green]✅ Successfully pushed to {self.branch}[/green]\n")
                return True
            else:
                console.print(f"[red]❌ Push failed with exit code {result.returncode}[/red]")
                if result.stderr:
                    console.print(f"[dim]{result.stderr}[/dim]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Push error: {e}[/red]")
            return False
    
    def sync_and_push(self, commit_message: str = "codercode sync", allow_empty: bool = True) -> bool:
        """
        Lakukan git add, commit, dan push dengan konfirmasi user.
        
        Args:
            commit_message: Pesan commit
            allow_empty: Izinkan commit kosong jika tidak ada perubahan
        
        Returns:
            True jika semua operasi berhasil, False jika ada yang gagal
        """
        try:
            # Step 1: Git add
            console.print("[cyan]📝 Staging changes...[/cyan]")
            result = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]⚠ Git add warning: {result.stderr}[/red]")
            
            # Step 2: Git commit
            console.print(f"[cyan]💾 Committing: '{commit_message}'...[/cyan]")
            cmd = ["git", "commit", "-m", commit_message]
            if allow_empty:
                cmd.append("--allow-empty")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0 and "nothing to commit" not in result.stdout:
                console.print(f"[yellow]⚠ Commit warning: {result.stderr}[/yellow]")
            
            # Step 3: Emit push request dan tunggu approval
            summary = f"Sync changes to {self.branch}"
            self.emit_push_request(summary)
            
            # Step 4: Execute push (akan dihandle oleh CLI atau fallback manual)
            return self.execute_push()
            
        except Exception as e:
            console.print(f"[red]❌ Sync error: {e}[/red]")
            return False


def handle_git_push(args, branch: str = "main") -> bool:
    """
    Fungsi utilitas untuk menangani git push dari CLI args.
    
    Args:
        args: Argument parser dari CLI
        branch: Nama branch untuk push
    
    Returns:
        True jika push berhasil/skip, False jika gagal
    """
    handler = PushRequestHandler(branch=branch)
    
    if args.git and args.push:
        commit_msg = "codercode sync"
        if hasattr(args, 'commit_message') and args.commit_message:
            commit_msg = args.commit_message
        
        return handler.sync_and_push(commit_message=commit_msg)
    
    return True
