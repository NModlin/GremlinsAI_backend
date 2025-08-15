#!/usr/bin/env python3
"""
gremlinsAI CLI Tool

Command-line interface for interacting with the gremlinsAI platform.
Provides easy access to all API functionality from the terminal.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.json import JSON

# Add SDK to path if running from source
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk" / "python"))

try:
    from gremlins_ai import GremlinsAIClient
    from gremlins_ai.exceptions import GremlinsAIError
except ImportError:
    print("Error: gremlinsAI SDK not found. Please install it first:")
    print("pip install gremlins-ai")
    sys.exit(1)

console = Console()


class Config:
    """Configuration management for the CLI."""
    
    def __init__(self):
        self.config_file = Path.home() / ".gremlins_ai" / "config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "base_url": "http://localhost:8000",
            "api_key": None,
            "timeout": 30
        }
    
    def save_config(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()


config = Config()


def get_client() -> GremlinsAIClient:
    """Get configured gremlinsAI client."""
    return GremlinsAIClient(
        base_url=config.get("base_url"),
        api_key=config.get("api_key"),
        timeout=config.get("timeout", 30)
    )


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """gremlinsAI CLI - Command-line interface for the gremlinsAI platform."""
    pass


@cli.group()
def config_cmd():
    """Configuration management commands."""
    pass


@config_cmd.command("show")
def show_config():
    """Show current configuration."""
    table = Table(title="gremlinsAI Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in config.config.items():
        if key == "api_key" and value:
            value = f"{value[:8]}..." if len(value) > 8 else value
        table.add_row(key, str(value))
    
    console.print(table)


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key: str, value: str):
    """Set a configuration value."""
    config.set(key, value)
    console.print(f"✅ Set {key} = {value}", style="green")


@cli.group()
def agent():
    """Agent interaction commands."""
    pass


@agent.command("chat")
@click.argument("message")
@click.option("--conversation-id", "-c", help="Conversation ID to continue")
@click.option("--save", "-s", is_flag=True, help="Save conversation")
def agent_chat(message: str, conversation_id: Optional[str], save: bool):
    """Chat with the AI agent."""
    async def _chat():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Thinking...", total=None)
                
                async with get_client() as client:
                    response = await client.invoke_agent(
                        message,
                        conversation_id=conversation_id,
                        save_conversation=save
                    )
                
                progress.remove_task(task)
            
            # Display response
            console.print(Panel(
                response["output"],
                title="🤖 AI Response",
                border_style="blue"
            ))
            
            # Show metadata
            metadata = Table(show_header=False, box=None)
            metadata.add_row("Execution Time:", f"{response['execution_time']:.2f}s")
            if response.get("conversation_id"):
                metadata.add_row("Conversation ID:", response["conversation_id"])
            
            console.print(metadata)
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
        except Exception as e:
            console.print(f"❌ Unexpected error: {e}", style="red")
    
    asyncio.run(_chat())


@cli.group()
def conversation():
    """Conversation management commands."""
    pass


@conversation.command("list")
@click.option("--limit", "-l", default=10, help="Number of conversations to show")
@click.option("--offset", "-o", default=0, help="Offset for pagination")
def list_conversations(limit: int, offset: int):
    """List conversations."""
    async def _list():
        try:
            async with get_client() as client:
                conversations = await client.list_conversations(limit=limit, offset=offset)
            
            if not conversations:
                console.print("No conversations found.", style="yellow")
                return
            
            table = Table(title="Conversations")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Created", style="blue")
            table.add_column("Messages", style="magenta")
            
            for conv in conversations:
                table.add_row(
                    conv.id[:8] + "...",
                    conv.title or "Untitled",
                    conv.created_at.strftime("%Y-%m-%d %H:%M"),
                    str(conv.message_count or len(conv.messages))
                )
            
            console.print(table)
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_list())


@conversation.command("show")
@click.argument("conversation_id")
def show_conversation(conversation_id: str):
    """Show a specific conversation."""
    async def _show():
        try:
            async with get_client() as client:
                conv = await client.get_conversation(conversation_id)
            
            console.print(Panel(
                f"Title: {conv.title or 'Untitled'}\n"
                f"Created: {conv.created_at}\n"
                f"Messages: {len(conv.messages)}",
                title=f"Conversation {conv.id[:8]}...",
                border_style="blue"
            ))
            
            for msg in conv.messages:
                style = "green" if msg.role == "user" else "blue"
                console.print(Panel(
                    msg.content,
                    title=f"{msg.role.title()} - {msg.created_at.strftime('%H:%M:%S')}",
                    border_style=style
                ))
                
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_show())


@cli.group()
def document():
    """Document management commands."""
    pass


@document.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--title", "-t", help="Document title")
def upload_document(file_path: str, title: Optional[str]):
    """Upload a document."""
    async def _upload():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Uploading document...", total=None)
                
                async with get_client() as client:
                    doc = await client.upload_document(file_path, title=title)
                
                progress.remove_task(task)
            
            console.print(f"✅ Document uploaded successfully!", style="green")
            console.print(f"Document ID: {doc.id}")
            console.print(f"Title: {doc.title}")
            console.print(f"Size: {doc.file_size} bytes")
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_upload())


@document.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Number of results")
@click.option("--rag", is_flag=True, help="Use RAG for response generation")
def search_documents(query: str, limit: int, rag: bool):
    """Search documents."""
    async def _search():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Searching documents...", total=None)
                
                async with get_client() as client:
                    results = await client.search_documents(
                        query, limit=limit, use_rag=rag
                    )
                
                progress.remove_task(task)
            
            if not results["results"]:
                console.print("No documents found.", style="yellow")
                return
            
            # Show RAG response if available
            if rag and results.get("rag_response"):
                console.print(Panel(
                    results["rag_response"],
                    title="🧠 RAG Response",
                    border_style="green"
                ))
            
            # Show search results
            table = Table(title="Search Results")
            table.add_column("Document", style="cyan")
            table.add_column("Score", style="green")
            table.add_column("Content Preview", style="blue")
            
            for result in results["results"]:
                content_preview = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                table.add_row(
                    result["title"],
                    f"{result['score']:.3f}",
                    content_preview
                )
            
            console.print(table)
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_search())


@cli.group()
def system():
    """System information and health commands."""
    pass


@system.command("health")
def system_health():
    """Check system health."""
    async def _health():
        try:
            async with get_client() as client:
                health = await client.get_system_health()
            
            # Overall status
            status_color = "green" if health.status == "healthy" else "red"
            console.print(Panel(
                f"Status: {health.status.upper()}\n"
                f"Version: {health.version}\n"
                f"Uptime: {health.uptime:.1f}s\n"
                f"Active Tasks: {health.active_tasks}",
                title="System Health",
                border_style=status_color
            ))
            
            # Component status
            table = Table(title="Components")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            
            for component in health.components:
                status = "✅ Available" if component.available else "❌ Unavailable"
                table.add_row(component.name, status)
            
            console.print(table)
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_health())


@system.command("info")
def system_info():
    """Get system information."""
    async def _info():
        try:
            async with get_client() as client:
                info = await client.get_realtime_info()
            
            console.print(JSON.from_data(info))
            
        except GremlinsAIError as e:
            console.print(f"❌ Error: {e}", style="red")
    
    asyncio.run(_info())


@cli.command("interactive")
def interactive_mode():
    """Start interactive chat mode."""
    console.print(Panel(
        "Welcome to gremlinsAI Interactive Mode!\n"
        "Type your messages and press Enter to chat.\n"
        "Type 'quit' or 'exit' to leave.",
        title="🤖 Interactive Mode",
        border_style="blue"
    ))
    
    conversation_id = None
    
    async def _interactive():
        nonlocal conversation_id
        
        async with get_client() as client:
            while True:
                try:
                    message = console.input("\n[bold green]You:[/bold green] ")
                    
                    if message.lower() in ['quit', 'exit', 'bye']:
                        console.print("👋 Goodbye!", style="blue")
                        break
                    
                    if not message.strip():
                        continue
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console
                    ) as progress:
                        task = progress.add_task("Thinking...", total=None)
                        
                        response = await client.invoke_agent(
                            message,
                            conversation_id=conversation_id,
                            save_conversation=True
                        )
                        
                        progress.remove_task(task)
                    
                    # Update conversation ID for continuity
                    conversation_id = response.get("conversation_id")
                    
                    console.print(f"[bold blue]AI:[/bold blue] {response['output']}")
                    
                except KeyboardInterrupt:
                    console.print("\n👋 Goodbye!", style="blue")
                    break
                except GremlinsAIError as e:
                    console.print(f"❌ Error: {e}", style="red")
                except Exception as e:
                    console.print(f"❌ Unexpected error: {e}", style="red")
    
    asyncio.run(_interactive())


if __name__ == "__main__":
    cli()
