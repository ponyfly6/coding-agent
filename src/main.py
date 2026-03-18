"""
Coding Agent - Powered by Vercel AI SDK

A multi-provider coding agent with tool calling capabilities.
"""

import os
import asyncio
import logging
from pathlib import Path

import yaml
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML

# Vercel AI SDK
import vercel_ai_sdk as ai

from . import tools

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}")
        return {}
    
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def get_model(config: dict):
    """Get the LLM model based on configuration.
    
    Supports:
    - AI Gateway (default): model="provider/model-name"
    - Direct OpenAI: OPENAI_API_KEY env var
    - Direct Anthropic: ANTHROPIC_API_KEY env var
    """
    model_str = config.get("model", "anthropic/claude-sonnet-4.6")
    
    # Check if using AI Gateway
    if "/" in model_str:
        provider, model_name = model_str.split("/", 1)
        
        # Use AI Gateway if API key is set
        gateway_key = os.getenv("AI_GATEWAY_API_KEY")
        if gateway_key:
            return ai.ai_gateway.GatewayModel(model=model_str)
        
        # Otherwise use direct provider
        if provider == "openai":
            return ai.openai.OpenAIModel(model=model_name)
        elif provider == "anthropic":
            return ai.anthropic.AnthropicModel(model=model_name)
        else:
            # Default to gateway format
            return ai.ai_gateway.GatewayModel(model=model_str)
    
    # Fallback
    return ai.ai_gateway.GatewayModel(model=model_str)


# --- Tool Definitions ---
# Wrap existing tools with @ai.tool decorator

@ai.tool
async def read_file(path: str) -> str:
    """Read the content of a file at the given path relative to the current working directory.
    
    Args:
        path: The relative path to the file from the current working directory.
    
    Returns:
        The content of the file as a string, or an error message.
    """
    return tools.read_file(path)


@ai.tool
async def list_files(directory: str) -> str:
    """List files in the specified directory relative to the current working directory.
    
    Args:
        directory: The relative path to the directory to list.
    
    Returns:
        A newline-separated list of file names, or an error message.
    """
    return tools.list_files(directory)


@ai.tool
async def edit_file(path: str, content: str) -> str:
    """Write or overwrite content to a file at the given path relative to the current working directory.
    
    Args:
        path: The relative path to the file to write.
        content: The content to write to the file.
    
    Returns:
        A success message or an error message.
    """
    return tools.edit_file(path, content)


@ai.tool
async def execute_bash_command(command: str) -> str:
    """Execute a whitelisted bash command in the current working directory.
    
    Allowed commands: ls, cat, git (add/status/commit/push/branch/checkout/merge/pull/fetch/reset/revert),
    grep, find, sed, awk, sort, uniq, wc, history, touch.
    
    Args:
        command: The full bash command string to execute.
    
    Returns:
        The standard output and standard error of the command, or an error message.
    """
    return tools.execute_bash_command(command)


@ai.tool
async def run_in_sandbox(command: str, image: str = "python:3.12-slim") -> str:
    """Execute a command inside a sandboxed Docker container.
    
    The sandbox's cwd is the directory where the agent is run from.
    The project directory is mounted at /app. Network access is disabled.
    
    Args:
        command: The command string to execute inside the container's /app directory.
        image: The Docker image to use. Defaults to 'python:3.12-slim'.
    
    Returns:
        The combined stdout/stderr from the container, or an error message.
    """
    return tools.run_in_sandbox(command, image=image)


@ai.tool
async def get_current_date_and_time(timezone: str = "America/Los_Angeles") -> str:
    """Get the current date and time as ISO 8601 string in the specified timezone.
    
    Args:
        timezone: The timezone string (e.g., 'America/Los_Angeles', 'UTC').
    
    Returns:
        The current date and time as an ISO 8601 string.
    """
    return tools.get_current_date_and_time(timezone)


@ai.tool
async def web_search(query: str, num_results: int = 10) -> str:
    """Search the web for information.
    
    Args:
        query: The search query.
        num_results: The number of results to return.
    
    Returns:
        Search results as a formatted string.
    """
    return tools.web_search(query, num_results)


@ai.tool
async def open_url(url: str) -> str:
    """Fetch and return the content of a URL.
    
    Args:
        url: The URL to fetch.
    
    Returns:
        The content of the URL or an error message.
    """
    return tools.open_url(url)


# List of all tools for the agent
AGENT_TOOLS = [
    read_file,
    list_files,
    edit_file,
    execute_bash_command,
    run_in_sandbox,
    get_current_date_and_time,
    web_search,
    open_url,
]


# --- Agent Definition ---

async def coding_agent(llm, query: str):
    """The main coding agent loop.
    
    Uses stream_loop for automatic tool calling until completion.
    """
    system_prompt = """You are an expert coding assistant. You help users with:
- Reading, writing, and editing code files
- Executing bash commands (whitelisted)
- Running code in sandboxed Docker containers
- Answering programming questions

Always be helpful, precise, and safe. When editing files, show the changes clearly.
Use the sandbox for running untrusted or experimental code."""

    return await ai.stream_loop(
        llm,
        messages=ai.make_messages(
            system=system_prompt,
            user=query,
        ),
        tools=AGENT_TOOLS,
    )


# --- CLI Interface ---

class CodeAgent:
    """Interactive coding agent with CLI interface."""
    
    def __init__(self, config: dict):
        self.config = config
        self.llm = get_model(config)
        self.verbose = config.get("verbose", False)
        self.conversation_history: list[ai.Message] = []
        
    def _get_prompt_message(self):
        """Get the dynamic prompt message."""
        return HTML('<ansiblue>🔵 You</ansiblue>: ')
    
    def _get_bottom_toolbar(self):
        """Get the bottom toolbar."""
        model = self.config.get("model", "unknown")
        return HTML(f'<ansigray>Model: {model} │ [Alt+Enter] Submit │ [Ctrl+D] Quit</ansigray>')
    
    def _create_session(self) -> PromptSession:
        """Create the prompt session."""
        kb = KeyBindings()
        
        @kb.add('enter')
        def _(event):
            """Enter creates a new line."""
            event.current_buffer.insert_text('\n')
        
        @kb.add('escape', 'enter')
        def _(event):
            """Alt+Enter submits."""
            event.current_buffer.validate_and_handle()
        
        @kb.add('c-d')
        def _(event):
            """Ctrl+D to quit on empty line."""
            if not event.current_buffer.text.strip():
                event.app.exit()
        
        return PromptSession(
            message=self._get_prompt_message,
            multiline=True,
            key_bindings=kb,
            history=InMemoryHistory(),
            bottom_toolbar=self._get_bottom_toolbar,
        )
    
    async def run_agent_loop(self, user_input: str):
        """Run the full agent loop with automatic tool calling."""
        if self.verbose:
            print(f"\n⏳ Running agent loop with model: {self.config.get('model', 'unknown')}")
        
        try:
            async for msg in ai.run(coding_agent, self.llm, user_input):
                if msg.text_delta:
                    print(msg.text_delta, end="", flush=True)
            print()  # Newline after streaming
        except Exception as e:
            logger.error(f"Error in agent loop: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
    
    def run(self):
        """Run the interactive agent."""
        print("\n🚀 Coding Agent (Vercel AI SDK)")
        print(f"   Model: {self.config.get('model', 'unknown')}")
        print("\n📝 Commands:")
        print("   • Type your message and press [Alt+Enter] to send")
        print("   • Press [Ctrl+D] on empty line to quit")
        print("   • Type '/help' for more commands")
        print()
        
        session = self._create_session()
        
        # Create a single event loop for the session
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while True:
                try:
                    user_input = session.prompt().strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle special commands
                    if user_input.lower() in ("/exit", "/quit", "/q"):
                        print("\n👋 Goodbye!")
                        break
                    
                    if user_input.lower() == "/help":
                        self._print_help()
                        continue
                    
                    if user_input.lower() == "/reset":
                        self.conversation_history = []
                        print("\n🔄 Conversation reset.")
                        continue
                    
                    # Process message using the event loop
                    print("\n🟢 Agent: ", end="")
                    loop.run_until_complete(self.run_agent_loop(user_input))
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error: {e}", exc_info=True)
                    print(f"\n❌ Error: {e}")
        finally:
            loop.close()
    
    def _print_help(self):
        """Print help message."""
        print("""
📚 Available Commands:
   /help     - Show this help message
   /exit     - Exit the agent
   /quit     - Exit the agent
   /reset    - Reset conversation history

🔧 Available Tools:
   • read_file - Read file contents
   • list_files - List directory contents
   • edit_file - Write/overwrite files
   • execute_bash_command - Run whitelisted bash commands
   • run_in_sandbox - Execute code in Docker sandbox
   • get_current_date_and_time - Get current time
   • web_search - Search the web
   • open_url - Fetch URL content
""")


def main():
    """Main entry point."""
    # Load environment variables
    dotenv_path = Path.home() / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
    
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(config_path)
    
    # Check for API keys
    has_key = any([
        os.getenv("AI_GATEWAY_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("GOOGLE_API_KEY"),
    ])
    
    if not has_key:
        print("⚠️ Warning: No API key found. Set one of:")
        print("   - AI_GATEWAY_API_KEY (recommended)")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - GOOGLE_API_KEY")
        print()
    
    # Run agent
    agent = CodeAgent(config)
    agent.run()


if __name__ == "__main__":
    main()