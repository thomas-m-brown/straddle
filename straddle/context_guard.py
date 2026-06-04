import json
import os

def guard_context(messages, max_tokens=16384):
    # If context is under 80% (approx 13k tokens), do nothing
    current_tokens = sum((len(m.get("content", "") or "") + 3) // 4 for m in messages)
    if current_tokens < (max_tokens * 0.8):
        return messages

    # Hybrid compression: 
    # 1. Summarize old messages, keep last 5
    # 2. Archive older messages to json
    
    compressed = messages[-5:]
    archived = messages[:-5]
    
    archive_path = os.path.expanduser("~/.hermes/kanban/logs/context_archive.json")
    with open(archive_path, "a") as f:
        json.dump(archived, f)
        
    return compressed
