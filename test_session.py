# test_session.py
from coder_cli import save_session, load_session, SESSION_FILE
import os

print(f"Session file: {SESSION_FILE}")
print(f"File exists: {os.path.exists(SESSION_FILE)}")

# Test save
test_chat_id = "0fee7a04-181e-459f-a89f-8117f4d63547"
test_parent_id = "test-parent-123"

print(f"\nSaving: chat={test_chat_id[:8]}, parent={test_parent_id}")
save_session(test_chat_id, test_parent_id)

print(f"\nFile exists after save: {os.path.exists(SESSION_FILE)}")
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE) as f:
        print(f"Content:\n{f.read()}")

# Test load
loaded_chat, loaded_parent = load_session()
print(f"\nLoaded: chat={loaded_chat}, parent={loaded_parent}")