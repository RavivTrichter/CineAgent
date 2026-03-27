"""CineAssist — Interactive CLI chat client."""

import sys

import click
import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)

DEFAULT_API_URL = "http://localhost:8001"


def _api_call(
    method: str, url: str, path: str, **kwargs
) -> dict | list | None:
    """Make an HTTP call to the Assistant API."""
    try:
        resp = getattr(httpx, method)(f"{url}{path}", timeout=60.0, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        error_console.print(
            f"[red]API error:[/red] {e.response.status_code} — {e.response.text}"
        )
        return None
    except httpx.ConnectError:
        error_console.print(
            f"[red]Cannot connect to backend at {url}[/red]\n"
            "Make sure the Assistant API is running (make assistant)."
        )
        return None
    except httpx.RequestError as e:
        error_console.print(f"[red]Request error:[/red] {e}")
        return None


def _render_confidence(confidence: str | None) -> str:
    """Return a Rich-formatted confidence badge."""
    if confidence == "verified":
        return "[green]VERIFIED[/green] — backed by API data"
    elif confidence == "mixed":
        return "[yellow]MIXED[/yellow] — partially verified"
    elif confidence == "general":
        return "[blue]GENERAL KNOWLEDGE[/blue]"
    return ""


def _render_response(data: dict, debug: bool) -> None:
    """Render an assistant response to the terminal."""
    console.print()
    console.print(Markdown(data["text"]))

    badge = _render_confidence(data.get("confidence"))
    if badge:
        console.print(f"\n  {badge}")

    if debug:
        thinking = data.get("thinking")
        if thinking:
            console.print(
                Panel(thinking, title="Thinking", border_style="dim", expand=False)
            )

        tool_calls = data.get("tool_calls_made", [])
        if tool_calls:
            table = Table(title="Tool Calls", show_lines=True)
            table.add_column("Tool", style="cyan")
            table.add_column("Input", style="dim")
            for tc in tool_calls:
                name = tc.get("name", str(tc)) if isinstance(tc, dict) else str(tc)
                inp = str(tc.get("input", "")) if isinstance(tc, dict) else ""
                table.add_row(name, inp[:120])
            console.print(table)

    console.print()


@click.group()
@click.version_option(version="1.0.0", prog_name="CineAssist CLI")
def cli() -> None:
    """CineAssist — Your intelligent film assistant (CLI)."""


@cli.command()
@click.option("--api-url", default=DEFAULT_API_URL, help="Assistant API base URL.")
def health(api_url: str) -> None:
    """Check if the Assistant API is running."""
    data = _api_call("get", api_url, "/health")
    if data:
        console.print(f"[green]OK[/green] — {data}")
    else:
        sys.exit(1)


@cli.command("list")
@click.option("--api-url", default=DEFAULT_API_URL, help="Assistant API base URL.")
def list_conversations(api_url: str) -> None:
    """List past conversations."""
    conversations = _api_call("get", api_url, "/conversations")
    if conversations is None:
        sys.exit(1)

    if not conversations:
        console.print("[dim]No conversations yet.[/dim]")
        return

    table = Table(title="Conversations")
    table.add_column("ID", style="dim", max_width=36)
    table.add_column("Title", style="bold")
    table.add_column("Updated", style="cyan")

    for conv in conversations:
        table.add_row(
            conv["id"],
            conv.get("title") or "Untitled",
            conv.get("updated_at", ""),
        )

    console.print(table)


@cli.command()
@click.argument("conversation_id")
@click.option("--api-url", default=DEFAULT_API_URL, help="Assistant API base URL.")
def delete(conversation_id: str, api_url: str) -> None:
    """Delete a conversation by ID."""
    result = _api_call("delete", api_url, f"/conversations/{conversation_id}")
    if result:
        console.print(f"[green]Deleted[/green] conversation {conversation_id}")
    else:
        sys.exit(1)


@cli.command()
@click.option("--api-url", default=DEFAULT_API_URL, help="Assistant API base URL.")
@click.option("--debug/--no-debug", default=False, help="Show thinking and tool calls.")
@click.option("--conversation-id", "-c", default=None, help="Resume an existing conversation.")
def chat(api_url: str, debug: bool, conversation_id: str | None) -> None:
    """Start an interactive chat session."""
    # Create or resume conversation
    if conversation_id:
        data = _api_call("get", api_url, f"/conversations/{conversation_id}")
        if not data:
            sys.exit(1)
        title = data.get("title") or "Untitled"
        console.print(f"[dim]Resuming conversation:[/dim] {title}")

        # Show existing messages
        for msg in data.get("messages", []):
            role = msg["role"]
            if role == "user":
                console.print(f"\n[bold cyan]You:[/bold cyan] {msg['content']}")
            elif role == "assistant":
                console.print(f"\n[bold green]CineAssist:[/bold green]")
                console.print(Markdown(msg["content"]))
    else:
        result = _api_call("post", api_url, "/conversations")
        if not result:
            sys.exit(1)
        conversation_id = result["id"]
        console.print(f"[dim]New conversation: {conversation_id}[/dim]")

    console.print(
        Panel(
            "Type your message and press Enter. Use [bold]Ctrl+C[/bold] or [bold]quit[/bold] to exit.",
            title="CineAssist Chat",
            border_style="cyan",
        )
    )

    # Chat loop
    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]You:[/bold cyan] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("quit", "exit", "/quit", "/exit"):
            console.print("[dim]Goodbye![/dim]")
            break

        with console.status("[dim]Thinking...[/dim]"):
            data = _api_call(
                "post",
                api_url,
                f"/conversations/{conversation_id}/messages",
                json={"message": user_input},
            )

        if data:
            console.print("[bold green]CineAssist:[/bold green]")
            _render_response(data, debug)
        else:
            console.print("[red]Failed to get a response. Try again.[/red]")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
