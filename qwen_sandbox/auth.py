"""
Authentication module for Qwen account login
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path.home() / ".qwen_sandbox"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


class QwenAuth:
    """Handle Qwen account authentication"""
    
    def __init__(self):
        self.api_url = os.getenv("QWEN_API_URL", "https://api.qwen.ai")
        self.api_key = os.getenv("QWEN_API_KEY")
        self.config_dir = CONFIG_DIR
        self.credentials_file = CREDENTIALS_FILE
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login with Qwen account credentials
        
        Args:
            username: Qwen account username/email
            password: Qwen account password
            
        Returns:
            dict: Authentication response with token and user info
        """
        try:
            # In a real implementation, this would call the Qwen API
            # For demo purposes, we'll simulate the login
            response = {
                "success": True,
                "token": self._generate_token(username),
                "user": {
                    "username": username,
                    "email": username,
                    "id": hashlib.md5(username.encode()).hexdigest()[:16]
                },
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            # Save credentials
            self._save_credentials(response)
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_token(self, username: str) -> str:
        """Generate a session token"""
        timestamp = datetime.now().isoformat()
        data = f"{username}:{timestamp}:{os.urandom(16).hex()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _save_credentials(self, credentials: Dict[str, Any]):
        """Save credentials to file"""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Retrieve saved credentials"""
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            
            # Check if token is expired
            expires_at = datetime.fromisoformat(credentials.get("expires_at", ""))
            if datetime.now() > expires_at:
                self.logout()
                return None
                
            return credentials
        except Exception:
            return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        credentials = self.get_credentials()
        return credentials is not None and credentials.get("success", False)
    
    def logout(self):
        """Clear saved credentials"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
    
    def get_token(self) -> Optional[str]:
        """Get current authentication token"""
        credentials = self.get_credentials()
        if credentials:
            return credentials.get("token")
        return None
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        credentials = self.get_credentials()
        if credentials:
            return credentials.get("user")
        return None
