# Straddle: An Autonomous Infrastructure Layer for Hermes

Straddle is a unified infrastructure layer for [Hermes Agent](https://hermes-agent.nousresearch.com). It provides a robust backend gateway for automated task execution, persistent system prompts, and a centralized maintenance control panel that integrates directly into your Hermes WebUI.

## Why I built this

I run Open WebUI, custom scripts, and various API clients — all pointing at Ollama on a local server. Each client needed its own configuration, system prompt, and endpoint. When I updated the system prompt I had to update it everywhere. When I wanted to add email context to responses, every client needed separate integration.

Straddle solves that by sitting between every client and Ollama: one address, one system prompt to edit, one place to add context enrichment. All clients get the same behavior without any per-client config.

---

## 🚀 Easy Install
Run the automated installer:
```bash
curl -fsSL https://raw.githubusercontent.com/thomas-m-brown/straddle/main/install.sh | bash
```

---

## 🛠 Features
- **Autonomous Loop:** Automatically dispatches Kanban tasks to agent workers.
- **Context Guard:** Hybrid compression logic (Summarize + Archive) ensures you stay within the 16k context window.
- **Maintenance Panel:** A persistent control panel injected directly into your Hermes WebUI sidebar.
- **Distributed Worker Nodes:** Offload RAG embeddings to secondary machines (e.g., Ideapad) to save Tower VRAM.

---

## 🔧 Troubleshooting
If the Maintenance Panel or updates don't appear after installation, your browser is likely serving cached assets:
1. **Hard Refresh:** 
   - **Mac:** `Cmd + Shift + R`
   - **Windows/Linux:** `Ctrl + F5`
2. **Clear Cache:** If a hard refresh fails, clear your browser's site data/cache for the Tailscale address, then restart your browser.

---

## Requirements
- Python 3.10+
- Node.js (for WebUI rebuild)
- Tailscale (for distributed worker nodes)
- Ollama
