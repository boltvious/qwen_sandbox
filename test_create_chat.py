# test_create_chat.py
from client import build_client
from coder_cli import DEFAULT_ENV_ID, DEFAULT_REPO, _url
import json

client = build_client()

# Variasi payload yang umum dipakai platform coding AI
payloads = [
    # V1: Minimal
    {"chat_id": "test-1", "title": "Test", "env_id": DEFAULT_ENV_ID},
    
    # V2: Dengan meta
    {
        "chat_id": "test-2",
        "title": "Test",
        "env_id": DEFAULT_ENV_ID,
        "meta": {"repo_info": DEFAULT_REPO, "env_info": {"env_name": "qwen_sandbox"}}
    },
    
    # V3: Dengan chat_type
    {
        "chat_id": "test-3",
        "title": "Test",
        "env_id": DEFAULT_ENV_ID,
        "chat_type": "code",
        "meta": {"repo_info": DEFAULT_REPO}
    },
    
    # V4: Tanpa chat_id (server generate)
    {
        "title": "Test",
        "env_id": DEFAULT_ENV_ID,
        "meta": {"repo_info": DEFAULT_REPO}
    }
]

endpoints = [
    "/coder/api/v2/chats/",
    "/coder/api/v2/chats/new",
    "/coder/api/v2/task/new",
    "/coder/api/v2/chats"
]

for ep in endpoints:
    for i, payload in enumerate(payloads, 1):
        try:
            r = client.post(_url(ep), json=payload)
            print(f"{ep} + V{i}: {r.status_code} | {r.text[:200]}")
            if r.status_code in (200, 201):
                print(f"  ✅ SUCCESS! Payload V{i} jalan di {ep}")
                print(f"  Response: {r.json()}")
        except Exception as e:
            print(f"{ep} + V{i}: ERROR {e}")