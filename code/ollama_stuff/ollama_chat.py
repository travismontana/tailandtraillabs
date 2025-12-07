#!/usr/bin/env python3
"""
ollama_chat.py - Conversation-aware Ollama client

Usage:
    ./ollama_chat.py --convo game1 --prompt "What pieces are visible?" --image board.jpg
    ./ollama_chat.py --convo game1 --prompt-file prompt.txt --json-extract -o output.json
    ./ollama_chat.py --batch /data/cards --batch-pattern "*.jpg" --json-extract
    ./ollama_chat.py --list-models
    echo "What's 2+2?" | ./ollama_chat.py --convo math --stdin
"""

import argparse
import json
import requests
import base64
import yaml
import sys
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Configuration defaults
DEFAULT_HOST = "groth.abode.tailandtraillabs.org:11434"
DEFAULT_MODEL = "qwen2-vl:7b"
DEFAULT_HISTORY_COUNT = 10
DEFAULT_TIMEOUT = 120
DEFAULT_TEMPERATURE = None  # Use model default
HISTORY_DIR = Path.home() / ".ollama_conversations"
DEFAULT_CONFIG_FILE = Path.home() / ".ollama_chat.yaml"

class Config:
    """Configuration manager with support for file, env vars, and CLI args"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config = {}
        
        # Load from config file if exists
        if config_file and config_file.exists():
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value, checking env vars first, then config file, then default"""
        import os
        
        # Check environment variable (uppercase with OLLAMA_ prefix)
        env_key = f"OLLAMA_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val
        
        # Check config file
        if key in self.config:
            return self.config[key]
        
        # Return default
        return default

def extract_json(text: str) -> str:
    """Extract JSON object/array from text, stripping markdown/conversational wrapper"""
    # Try to find JSON in markdown code blocks first
    json_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text)
    if json_block:
        return json_block.group(1).strip()
    
    # Try to find raw JSON object or array
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if json_match:
        return json_match.group(1).strip()
    
    # If no JSON found, return original
    return text

def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars ≈ 1 token)"""
    return len(text) // 4

class ConversationManager:
    """Manages conversation history and interactions with Ollama"""
    
    def __init__(
        self,
        convo_id: str,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        history_count: int = DEFAULT_HISTORY_COUNT,
        history_dir: Path = HISTORY_DIR,
        timeout: int = DEFAULT_TIMEOUT,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        verbose: bool = False,
        debug: bool = False
    ):
        self.convo_id = convo_id
        self.model = model
        self.ollama_url = f"http://{host}/api/generate"
        self.ollama_host = host
        self.history_count = history_count
        self.timeout = timeout
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.debug = debug
        self.history_file = history_dir / f"{convo_id}.json"
        history_dir.mkdir(exist_ok=True)
    
    def load_history(self) -> str:
        """Load conversation history and format for context"""
        if not self.history_file.exists():
            return ""
        
        with open(self.history_file, 'r') as f:
            history = json.load(f)
        
        # Take last N interactions based on history_count
        recent = history[-self.history_count:] if self.history_count > 0 else []
        
        if not recent:
            return ""
        
        # Format as context
        context = "Previous conversation:\n"
        for exchange in recent:
            context += f"\nUser: {exchange['prompt']}\n"
            context += f"Assistant: {exchange['response']}\n"
        
        return context
    
    def save_interaction(self, prompt: str, response: str, had_images: int = 0):
        """Append this interaction to history"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append({
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'response': response,
            'model': self.model,
            'had_images': had_images
        })
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def ask(
        self,
        prompt: str,
        image_paths: Optional[List[Path]] = None,
        stream: bool = False
    ) -> str:
        """Send prompt to Ollama with conversation history"""
        
        # Load previous context
        history_context = self.load_history()
        
        # Build full prompt with system prompt if provided
        full_prompt = ""
        if self.system_prompt:
            full_prompt += f"System: {self.system_prompt}\n\n"
        
        if history_context:
            full_prompt += f"{history_context}\n\n"
        
        full_prompt += f"User: {prompt}\nAssistant:"
        
        # Build request payload
        payload = {
            'model': self.model,
            'prompt': full_prompt,
            'stream': stream
        }
        
        # Add temperature if specified
        if self.temperature is not None:
            payload['options'] = {'temperature': self.temperature}
        
        # Add images if provided
        if image_paths:
            images = []
            for image_path in image_paths:
                if not image_path.exists():
                    raise FileNotFoundError(f"Image not found: {image_path}")
                
                with open(image_path, 'rb') as img:
                    encoded = base64.b64encode(img.read()).decode()
                    images.append(encoded)
            payload['images'] = images
        
        if self.verbose:
            print(f"→ Sending to {self.ollama_url}", file=sys.stderr)
            print(f"→ Model: {self.model}", file=sys.stderr)
            if image_paths:
                print(f"→ Images: {len(image_paths)}", file=sys.stderr)
            if self.temperature is not None:
                print(f"→ Temperature: {self.temperature}", file=sys.stderr)
            print(f"→ Context tokens: ~{estimate_tokens(full_prompt)}", file=sys.stderr)
        
        if self.debug:
            debug_payload = payload.copy()
            if 'images' in debug_payload:
                debug_payload['images'] = [f"<base64 image {i+1}>" for i in range(len(debug_payload['images']))]
            print(f"→ Full payload:\n{json.dumps(debug_payload, indent=2)}", file=sys.stderr)
        
        # Call Ollama
        try:
            if stream:
                return self._stream_response(payload, prompt, image_paths)
            else:
                response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                ai_response = result['response']
                
                if self.verbose:
                    print(f"← Response tokens: ~{estimate_tokens(ai_response)}", file=sys.stderr)
                
                # Save this interaction
                self.save_interaction(prompt, ai_response, had_images=len(image_paths) if image_paths else 0)
                
                return ai_response
                
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}")
    
    def _stream_response(self, payload: dict, prompt: str, image_paths: Optional[List[Path]]) -> str:
        """Handle streaming response"""
        full_response = ""
        
        try:
            response = requests.post(
                self.ollama_url,
                json=payload,
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        text = chunk['response']
                        print(text, end='', flush=True)
                        full_response += text
            
            print()  # Final newline
            
            # Save interaction
            self.save_interaction(prompt, full_response, had_images=len(image_paths) if image_paths else 0)
            
            return full_response
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Streaming request failed: {e}")

def list_models(host: str, timeout: int = 10) -> List[Dict[str, Any]]:
    """List available models from Ollama host"""
    url = f"http://{host}/api/tags"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json().get('models', [])
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to list models from {host}: {e}")

def process_single_request(
    manager: ConversationManager,
    prompt: str,
    image_paths: Optional[List[Path]],
    args: argparse.Namespace
) -> str:
    """Process a single request with retry logic"""
    
    for attempt in range(args.retries + 1):
        try:
            if args.verbose and attempt > 0:
                print(f"→ Retry attempt {attempt}/{args.retries}", file=sys.stderr)
            
            response = manager.ask(prompt, image_paths, stream=args.stream)
            
            # Extract JSON if requested
            if args.json_extract:
                response = extract_json(response)
            
            # Validate JSON if requested
            if args.validate_json:
                try:
                    json.loads(response)
                except json.JSONDecodeError as e:
                    if args.retry_on_invalid_json and attempt < args.retries:
                        if args.verbose:
                            print(f"← Invalid JSON, retrying: {e}", file=sys.stderr)
                        time.sleep(1)
                        continue
                    raise ValueError(f"Invalid JSON: {e}")
            
            return response
            
        except Exception as e:
            if attempt < args.retries:
                if args.verbose:
                    print(f"← Error, retrying: {e}", file=sys.stderr)
                time.sleep(1)
                continue
            raise
    
    raise RuntimeError("Max retries exceeded")

def batch_process(
    args: argparse.Namespace,
    config: Config,
    prompt: str,
    system_prompt: Optional[str]
) -> None:
    """Process multiple images in batch mode"""
    
    batch_dir = Path(args.batch)
    if not batch_dir.is_dir():
        print(f"Error: {args.batch} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Find all matching images
    image_files = sorted(batch_dir.glob(args.batch_pattern))
    if not image_files:
        print(f"No files matching {args.batch_pattern} in {args.batch}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing {len(image_files)} files...", file=sys.stderr)
    
    # Process each image
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Processing {image_path.name}...", file=sys.stderr)
        
        # Create manager for this image (reuse convo or create unique?)
        convo_id = args.convo or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        manager = ConversationManager(
            convo_id=convo_id,
            model=args.model,
            host=args.host,
            history_count=0,  # No history in batch mode
            history_dir=Path(config.get('conversations_dir', HISTORY_DIR)),
            timeout=args.timeout,
            temperature=args.temperature,
            system_prompt=system_prompt,
            verbose=args.verbose,
            debug=args.debug
        )
        
        try:
            response = process_single_request(manager, prompt, [image_path], args)
            
            # Determine output path
            if args.output:
                # Use template: {name} gets replaced with image basename
                output_path = Path(args.output.replace('{name}', image_path.stem))
            else:
                output_path = image_path.with_suffix('.json')
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response)
            
            print(f"✓ Saved to {output_path}", file=sys.stderr)
            
        except Exception as e:
            print(f"✗ Failed: {e}", file=sys.stderr)
            if not args.batch_continue_on_error:
                sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Production-grade conversation-aware Ollama client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s --convo game1 --prompt "What do you see?" --image board.jpg
  
  # With config and advanced options
  %(prog)s -c game1 -f prompt.txt -i card.jpg -j -o card.json --validate-json
  
  # Batch processing
  %(prog)s --batch /data/cards --batch-pattern "*.jpg" -f card_prompt.txt -j -o "/data/output/{name}.json"
  
  # Streaming with system prompt
  %(prog)s -c chat --system "You are a helpful assistant" --prompt "Hello" --stream
  
  # Using stdin
  echo "What is 2+2?" | %(prog)s --convo math --stdin
  
  # List available models
  %(prog)s --list-models

Environment variables:
  OLLAMA_HOST              Default Ollama host
  OLLAMA_MODEL             Default model
  OLLAMA_HISTORY_COUNT     Default history count
  OLLAMA_CONVERSATIONS_DIR Conversation storage directory
        """
    )
    
    # Configuration
    parser.add_argument('--config',
                       type=Path,
                       help=f'Config file (default: {DEFAULT_CONFIG_FILE})')
    
    # Core arguments
    parser.add_argument('--convo', '-c',
                       help='Conversation ID (creates new or continues existing)')
    parser.add_argument('--prompt', '-p',
                       help='Your prompt/question')
    parser.add_argument('--prompt-file', '-f',
                       type=Path,
                       help='Read prompt from file')
    parser.add_argument('--stdin',
                       action='store_true',
                       help='Read prompt from stdin')
    
    # Model and host
    parser.add_argument('--model', '-m',
                       default=DEFAULT_MODEL,
                       help=f'Ollama model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--host',
                       default=DEFAULT_HOST,
                       help=f'Ollama host:port (default: {DEFAULT_HOST})')
    
    # System prompt
    parser.add_argument('--system',
                       help='System prompt/instructions for the model')
    parser.add_argument('--system-file',
                       type=Path,
                       help='Read system prompt from file')
    
    # Images
    parser.add_argument('--image', '-i',
                       type=Path,
                       help='Path to image file (for vision models)')
    parser.add_argument('--images',
                       nargs='+',
                       type=Path,
                       help='Multiple image files')
    
    # History control
    parser.add_argument('--history-count', '-n',
                       type=int,
                       default=DEFAULT_HISTORY_COUNT,
                       help=f'Number of previous interactions to include (default: {DEFAULT_HISTORY_COUNT}, 0 for none)')
    
    # Output options
    parser.add_argument('--output', '-o',
                       help='Save response to file (use {name} in batch mode for dynamic naming)')
    parser.add_argument('--append',
                       action='store_true',
                       help='Append to output file instead of overwriting')
    parser.add_argument('--json-extract', '-j',
                       action='store_true',
                       help='Extract only JSON from response')
    parser.add_argument('--validate-json',
                       action='store_true',
                       help='Validate JSON before saving')
    
    # Model parameters
    parser.add_argument('--temperature', '-t',
                       type=float,
                       help='Sampling temperature (0.0-2.0, lower=more deterministic)')
    parser.add_argument('--timeout',
                       type=int,
                       default=DEFAULT_TIMEOUT,
                       help=f'Request timeout in seconds (default: {DEFAULT_TIMEOUT})')
    
    # Retry logic
    parser.add_argument('--retries',
                       type=int,
                       default=0,
                       help='Number of retries on failure')
    parser.add_argument('--retry-on-invalid-json',
                       action='store_true',
                       help='Retry if JSON validation fails')
    
    # Batch processing
    parser.add_argument('--batch',
                       type=Path,
                       help='Process multiple images from directory')
    parser.add_argument('--batch-pattern',
                       default='*.jpg',
                       help='File pattern for batch mode (default: *.jpg)')
    parser.add_argument('--batch-continue-on-error',
                       action='store_true',
                       help='Continue batch processing on error')
    
    # Display options
    parser.add_argument('--stream',
                       action='store_true',
                       help='Stream response in real-time')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Show request/response details')
    parser.add_argument('--debug',
                       action='store_true',
                       help='Show full request payload')
    parser.add_argument('--show-tokens',
                       action='store_true',
                       help='Show estimated token counts')
    
    # Utility commands
    parser.add_argument('--list', '-l',
                       action='store_true',
                       help='List all conversation IDs')
    parser.add_argument('--show', '-s',
                       help='Show history for a conversation ID')
    parser.add_argument('--clear',
                       help='Clear/delete a conversation history')
    parser.add_argument('--list-models',
                       action='store_true',
                       help='List available models on Ollama host')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Show what would be sent without sending')
    
    args = parser.parse_args()
    
    # Load configuration
    config_file = args.config or DEFAULT_CONFIG_FILE
    config = Config(config_file if config_file.exists() else None)
    
    # Apply config defaults
    if not args.model or args.model == DEFAULT_MODEL:
        args.model = config.get('model', args.model or DEFAULT_MODEL)
    if not args.host or args.host == DEFAULT_HOST:
        args.host = config.get('host', args.host or DEFAULT_HOST)
    if args.history_count == DEFAULT_HISTORY_COUNT:
        args.history_count = int(config.get('history_count', args.history_count))
    if args.timeout == DEFAULT_TIMEOUT:
        args.timeout = int(config.get('timeout', args.timeout))
    
    conversations_dir = Path(config.get('conversations_dir', HISTORY_DIR))
    conversations_dir.mkdir(exist_ok=True)
    
    # Handle utility commands
    if args.list_models:
        try:
            models = list_models(args.host)
            print("\nAvailable models on", args.host)
            for model in models:
                name = model.get('name', 'unknown')
                size = model.get('size', 0)
                size_gb = size / (1024**3)
                modified = model.get('modified_at', 'unknown')
                print(f"  {name:30s} {size_gb:6.1f} GB  {modified}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        return 0
    
    if args.list:
        if not conversations_dir.exists():
            print("No conversations found.")
            return 0
        
        convos = sorted(conversations_dir.glob("*.json"))
        if not convos:
            print("No conversations found.")
            return 0
        
        print("\nConversations:")
        for convo_file in convos:
            convo_id = convo_file.stem
            with open(convo_file, 'r') as f:
                history = json.load(f)
            last_time = history[-1]['timestamp'] if history else "unknown"
            count = len(history)
            print(f"  {convo_id:25s} {count:4d} messages  {last_time}")
        return 0
    
    if args.show:
        history_file = conversations_dir / f"{args.show}.json"
        if not history_file.exists():
            print(f"No conversation found: {args.show}")
            return 1
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        print(f"\n=== Conversation: {args.show} ===\n")
        for exchange in history:
            print(f"[{exchange['timestamp']}] Model: {exchange['model']}")
            print(f"User: {exchange['prompt']}")
            print(f"Assistant: {exchange['response']}")
            if exchange.get('had_images', 0) > 0:
                print(f"(included {exchange['had_images']} image(s))")
            if args.show_tokens:
                tokens = estimate_tokens(exchange['prompt'] + exchange['response'])
                print(f"Tokens: ~{tokens}")
            print("-" * 80)
        return 0
    
    if args.clear:
        history_file = conversations_dir / f"{args.clear}.json"
        if history_file.exists():
            history_file.unlink()
            print(f"Cleared conversation: {args.clear}")
        else:
            print(f"No conversation found: {args.clear}")
        return 0
    
    # Build prompt from various sources
    prompt = None
    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        if not args.prompt_file.exists():
            print(f"Prompt file not found: {args.prompt_file}", file=sys.stderr)
            return 1
        prompt = args.prompt_file.read_text().strip()
    elif args.stdin:
        prompt = sys.stdin.read().strip()
    
    # Build system prompt
    system_prompt = None
    if args.system:
        system_prompt = args.system
    elif args.system_file:
        if not args.system_file.exists():
            print(f"System prompt file not found: {args.system_file}", file=sys.stderr)
            return 1
        system_prompt = args.system_file.read_text().strip()
    
    # Handle batch mode
    if args.batch:
        if not prompt:
            print("Error: --prompt, --prompt-file, or --stdin required for batch mode", file=sys.stderr)
            return 1
        
        batch_process(args, config, prompt, system_prompt)
        return 0
    
    # Normal single request mode - validate requirements
    if not args.convo:
        print("Error: --convo required (unless using --list/--show/--clear/--list-models)", file=sys.stderr)
        return 1
    
    if not prompt:
        print("Error: --prompt, --prompt-file, or --stdin required", file=sys.stderr)
        return 1
    
    # Collect images
    image_paths = []
    if args.image:
        image_paths.append(args.image)
    if args.images:
        image_paths.extend(args.images)
    
    # Create conversation manager
    manager = ConversationManager(
        convo_id=args.convo,
        model=args.model,
        host=args.host,
        history_count=args.history_count,
        history_dir=conversations_dir,
        timeout=args.timeout,
        temperature=args.temperature,
        system_prompt=system_prompt,
        verbose=args.verbose,
        debug=args.debug
    )
    
    # Dry run mode
    if args.dry_run:
        print("=== DRY RUN MODE ===", file=sys.stderr)
        print(f"Conversation: {args.convo}", file=sys.stderr)
        print(f"Model: {args.model}", file=sys.stderr)
        print(f"Host: {args.host}", file=sys.stderr)
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}", file=sys.stderr)
        if system_prompt:
            print(f"System: {system_prompt[:100]}..." if len(system_prompt) > 100 else f"System: {system_prompt}", file=sys.stderr)
        if image_paths:
            print(f"Images: {[str(p) for p in image_paths]}", file=sys.stderr)
        print(f"History count: {args.history_count}", file=sys.stderr)
        return 0
    
    # Process request
    try:
        response = process_single_request(manager, prompt, image_paths or None, args)
        
        # Handle output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if args.append else 'w'
            with open(output_path, mode) as f:
                f.write(response)
                if args.append:
                    f.write('\n')
            
            if args.verbose:
                print(f"✓ Saved to {output_path}", file=sys.stderr)
        else:
            print(response)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main() or 0)
