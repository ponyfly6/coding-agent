# 🤖 Coding Agent (Vercel AI SDK)

A Python-based interactive coding agent powered by the Vercel AI SDK, supporting multiple LLM providers.

## ✨ Features

- **Multi-Provider Support**: Use any LLM via AI Gateway or direct API
  - Anthropic (Claude)
  - OpenAI (GPT)
  - Google (Gemini)
  - And more...
- **Interactive Chat**: Engage in conversations with the AI
- **File Operations**: Read, list, and modify files
- **Command Execution**: Run whitelisted shell commands
- **Sandboxed Execution**: Safely run code in Docker containers
- **Tool Calling**: Automatic tool execution via AI SDK

## 🛠️ Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/voxmenthe/coding-agent.git
   cd coding-agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```
   
   Or with Poetry:
   ```bash
   poetry install
   ```

3. **Set up API Key:**
   
   Option A - AI Gateway (recommended):
   ```bash
   export AI_GATEWAY_API_KEY="your_gateway_key"
   ```
   
   Option B - Direct provider:
   ```bash
   export ANTHROPIC_API_KEY="your_key"  # For Claude
   # or
   export OPENAI_API_KEY="your_key"     # For GPT
   # or
   export GOOGLE_API_KEY="your_key"     # For Gemini
   ```

4. **Configure model** (optional):
   
   Edit `src/config.yaml`:
   ```yaml
   model: "anthropic/claude-sonnet-4.6"  # or "openai/gpt-4o", "google/gemini-2.5-pro"
   ```

5. **(Optional) Docker for Sandbox:**
   ```bash
   docker pull python:3.12-slim
   ```

## ▶️ Running the Agent

```bash
coding-agent
```

## 📝 Usage

- Type your requests at the `🔵 You:` prompt
- Press `Alt+Enter` to send messages
- Press `Ctrl+D` to quit

### Commands

- `/help` - Show available commands
- `/reset` - Reset conversation history
- `/exit` or `/quit` - Exit the agent

### Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `list_files` | List directory contents |
| `edit_file` | Write/overwrite files |
| `execute_bash_command` | Run whitelisted bash commands |
| `run_in_sandbox` | Execute code in Docker sandbox |
| `get_current_date_and_time` | Get current time |
| `web_search` | Search the web |
| `open_url` | Fetch URL content |

### Example

```
🔵 You: Read the file src/main.py and explain what it does

🟢 Agent: I'll read the file for you...
[Uses read_file tool]

This file implements a coding agent using the Vercel AI SDK...
```

## 🔧 Configuration

Edit `src/config.yaml`:

```yaml
# Model selection (provider/model format for AI Gateway)
model: "anthropic/claude-sonnet-4.6"

# Agent settings
verbose: false
default_thinking_budget: 256

# Sandbox settings
sandbox_image: "python:3.12-slim"
sandbox_memory_limit: "512m"
```

## 📋 Requirements

- Python 3.12+
- Docker (optional, for sandbox)
- API key for your chosen provider