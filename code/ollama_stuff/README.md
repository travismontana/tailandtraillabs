# Ollama Tools

CLI and Web interface for Ollama with conversation memory and advanced features.

## Files

- `ollama_chat.py` - CLI script with conversation memory
- `ollama_web.py` - Web interface
- `templates/index.html` - Web UI template

## Installation

```bash
# Install dependencies
pip3 install fastapi uvicorn python-multipart jinja2 requests pyyaml

# Make scripts executable
chmod +x ollama_chat.py ollama_web.py
```

## Quick Start

### CLI Usage

```bash
# Basic chat
./ollama_chat.py --convo game1 --prompt "What do you see?" --image board.jpg

# With prompt file and JSON extraction
./ollama_chat.py -c cards -f card_prompt.txt -i card.jpg -j -o card.json

# Batch processing
./ollama_chat.py --batch /data/cards --batch-pattern "*.jpg" -f prompt.txt -j

# List models
./ollama_chat.py --list-models

# View conversation history
./ollama_chat.py --show game1
```

### Web Interface

```bash
# Start web server
./ollama_web.py --host 0.0.0.0 --port 8080

# Access at http://localhost:8080
```

## Configuration

Create `~/.ollama_chat.yaml`:

```yaml
host: groth.abode.tailandtraillabs.org:11434
model: qwen2-vl:7b
history_count: 10
conversations_dir: /data/twat/conversations
timeout: 120
```

## Data Directories

The tools use these directories:

- `~/.ollama_conversations/` - CLI conversation history
- `/data/twat/conversations/` - Web conversation history
- `/data/twat/uploads/` - Uploaded files
- `/data/twat/prompts/` - Prompt templates

## Features

### CLI Script
- Conversation memory (auto-loads context)
- Batch image processing
- JSON extraction and validation
- Retry logic
- System prompts
- Multiple images support
- Streaming responses
- Temperature control

### Web Interface
- Model selection from Ollama
- Conversation management
- Image upload
- Prompt templates
- History viewing
- JSON extraction/validation
- System prompts
- Temperature control

## Example Prompts

Create prompts in `/data/twat/prompts/`:

```
# Card Extraction
# Extract Dune Imperium card data to JSON
Convert this Dune Imperium card into JSON with format:
{
  "card_name": "...",
  "cost": 0,
  "description": "..."
}
```

## Environment Variables

- `OLLAMA_HOST` - Default Ollama host
- `OLLAMA_MODEL` - Default model
- `OLLAMA_HISTORY_COUNT` - Default history count

## Systemd Service

```ini
[Unit]
Description=Ollama Web Interface
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ollama_tools
ExecStart=/usr/bin/python3 /path/to/ollama_tools/ollama_web.py --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

## License

MIT
