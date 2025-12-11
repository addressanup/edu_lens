#!/usr/bin/env python3
"""
Claude Agents Orchestration System - Command Line Interface.

This module provides the CLI for running and managing the orchestration system.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.config import ConfigManager
from orchestrator.logger import LoggerManager

console = Console()


def print_banner() -> None:
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║       Claude Agents Orchestration System v1.0.0-alpha         ║
║                                                               ║
║        Multi-Agent AI Platform for Software Delivery          ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


@click.group()
@click.version_option(version="1.0.0-alpha", prog_name="Claude Agents Orchestrator")
@click.option("--debug/--no-debug", default=False, help="Enable debug mode")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
@click.pass_context
def main(ctx: click.Context, debug: bool, config: Optional[str]) -> None:
    """Claude Agents Orchestration System - CLI.

    A multi-agent AI platform for end-to-end software project delivery.
    """
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["config_path"] = config

    # Initialize configuration
    config_manager = ConfigManager()
    if config:
        config_manager.load_from_file(config)
    ctx.obj["config"] = config_manager


@main.command()
@click.option("--project", "-p", required=True, help="Project name or description")
@click.option("--spec-file", "-s", type=click.Path(exists=True), help="Path to project specification file")
@click.option("--resume", "-r", type=str, help="Resume from checkpoint ID")
@click.option("--dry-run/--no-dry-run", default=False, help="Validate without executing")
@click.option("--output-dir", "-o", type=click.Path(), default="./output", help="Output directory for generated files")
@click.pass_context
def run(
    ctx: click.Context,
    project: str,
    spec_file: Optional[str],
    resume: Optional[str],
    dry_run: bool,
    output_dir: str
) -> None:
    """Run the orchestration pipeline for a project.

    Examples:

        # Start a new project
        cao run --project "E-commerce Platform"

        # Use a specification file
        cao run --project "My App" --spec-file ./spec.yaml

        # Resume from checkpoint
        cao run --project "My App" --resume checkpoint_abc123

        # Dry run (validate only)
        cao run --project "My App" --dry-run
    """
    print_banner()

    config_manager: ConfigManager = ctx.obj["config"]
    logger = LoggerManager(config_manager)

    console.print(f"\n[bold green]Starting orchestration for:[/bold green] {project}")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]\n")

    if resume:
        console.print(f"[cyan]Resuming from checkpoint:[/cyan] {resume}\n")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Import orchestrator here to avoid circular imports
        from orchestrator.orchestrator import ClaudeAgentsOrchestrator

        # Initialize orchestrator
        orchestrator = ClaudeAgentsOrchestrator(
            config=config_manager,
            logger=logger,
            output_dir=output_path
        )

        # Run the pipeline
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing orchestrator...", total=None)

            # Run async orchestration
            if resume:
                result = asyncio.run(orchestrator.resume_from_checkpoint(resume))
            elif spec_file:
                result = asyncio.run(orchestrator.run_from_spec(spec_file, dry_run=dry_run))
            else:
                result = asyncio.run(orchestrator.run(project, dry_run=dry_run))

            progress.update(task, description="Pipeline completed!")

        # Display results
        if result.success:
            console.print("\n[bold green]Pipeline completed successfully![/bold green]")
            console.print(f"Output directory: {output_path.absolute()}")
            if result.deployment_package:
                console.print(f"Deployment package: {result.deployment_package}")
        else:
            console.print("\n[bold red]Pipeline failed![/bold red]")
            console.print(f"Error: {result.error_message}")
            if result.checkpoint_id:
                console.print(f"\n[yellow]Resume with:[/yellow] cao run --project \"{project}\" --resume {result.checkpoint_id}")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        logger.error("CLI", f"Orchestration failed: {str(e)}")
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check system status and health.

    Verifies connectivity to all required services and displays
    current system health.
    """
    print_banner()

    config_manager: ConfigManager = ctx.obj["config"]

    console.print("\n[bold]System Health Check[/bold]\n")

    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Check services
    checks = [
        ("PostgreSQL", "DATABASE_URL"),
        ("Redis", "REDIS_URL"),
        ("Claude CLI", "CLAUDE_CLI_PATH"),
        ("MCP Servers", "MCP_ENABLED"),
    ]

    for service, config_key in checks:
        try:
            value = config_manager.get(config_key)
            if value:
                # Perform actual health check here
                table.add_row(service, "[green]OK[/green]", str(value)[:50])
            else:
                table.add_row(service, "[yellow]Not Configured[/yellow]", "-")
        except Exception as e:
            table.add_row(service, "[red]Error[/red]", str(e)[:50])

    console.print(table)


@main.command()
@click.option("--checkpoint-id", "-c", required=True, help="Checkpoint ID to inspect")
@click.pass_context
def inspect(ctx: click.Context, checkpoint_id: str) -> None:
    """Inspect a checkpoint.

    Shows details about a saved checkpoint including state,
    progress, and any errors.
    """
    print_banner()

    config_manager: ConfigManager = ctx.obj["config"]

    console.print(f"\n[bold]Checkpoint Details: {checkpoint_id}[/bold]\n")

    try:
        from orchestrator.state_manager import StateStore

        state_store = StateStore(config_manager.get("DATABASE_URL"))
        checkpoint = state_store.get_checkpoint(checkpoint_id)

        if not checkpoint:
            console.print(f"[red]Checkpoint not found: {checkpoint_id}[/red]")
            sys.exit(1)

        # Display checkpoint info
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("ID", checkpoint.id)
        table.add_row("Project", checkpoint.project_name)
        table.add_row("Phase", str(checkpoint.current_phase))
        table.add_row("Status", checkpoint.status)
        table.add_row("Created", str(checkpoint.created_at))
        table.add_row("Updated", str(checkpoint.updated_at))

        console.print(table)

        if checkpoint.error_message:
            console.print(f"\n[red]Error:[/red] {checkpoint.error_message}")

    except Exception as e:
        console.print(f"[red]Error loading checkpoint:[/red] {str(e)}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option("--all/--latest", default=False, help="List all checkpoints or just latest")
@click.pass_context
def checkpoints(ctx: click.Context, all: bool) -> None:
    """List available checkpoints.

    Shows saved checkpoints that can be resumed.
    """
    print_banner()

    config_manager: ConfigManager = ctx.obj["config"]

    console.print("\n[bold]Available Checkpoints[/bold]\n")

    try:
        from orchestrator.state_manager import StateStore

        state_store = StateStore(config_manager.get("DATABASE_URL"))
        checkpoint_list = state_store.list_checkpoints(limit=None if all else 10)

        if not checkpoint_list:
            console.print("[yellow]No checkpoints found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Project")
        table.add_column("Phase", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Created")

        for cp in checkpoint_list:
            status_style = {
                "completed": "green",
                "failed": "red",
                "in_progress": "yellow",
            }.get(cp.status, "white")

            table.add_row(
                cp.id[:12] + "...",
                cp.project_name[:20],
                str(cp.current_phase),
                f"[{status_style}]{cp.status}[/{status_style}]",
                str(cp.created_at)[:19]
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing checkpoints:[/red] {str(e)}")
        if ctx.obj["debug"]:
            console.print_exception()
        sys.exit(1)


@main.command()
@click.option("--host", default="localhost", help="Server host")
@click.option("--port", default=8080, help="Server port")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int) -> None:
    """Start the orchestrator API server.

    Launches a REST API server for programmatic access to
    the orchestration system.
    """
    print_banner()

    console.print(f"\n[bold]Starting API Server[/bold]")
    console.print(f"Host: {host}")
    console.print(f"Port: {port}")
    console.print("\n[yellow]API server not yet implemented[/yellow]")
    console.print("Use CLI commands for now.\n")


@main.command()
@click.pass_context
def agents(ctx: click.Context) -> None:
    """List available agents and their capabilities."""
    print_banner()

    console.print("\n[bold]Available Agents[/bold]\n")

    agent_info = [
        ("Concept Designer", "Phase 1", "Requirements analysis, architecture decisions, tech stack selection"),
        ("MCP Engineer", "Phase 2", "External data integration via MCP servers, schema transformation"),
        ("Integration Engineer", "Phase 3", "Infrastructure provisioning, CI/CD setup, cloud configuration"),
        ("Backend Engineer", "Phase 4", "API design, database integration, server-side code generation"),
        ("Frontend Engineer", "Phase 4", "UI components, state management, responsive design"),
        ("Security Engineer", "Phase 5", "SAST scanning, OWASP validation, secret detection"),
        ("QA Engineer", "Phase 5", "Test generation, integration testing, coverage analysis"),
        ("DevOps Engineer", "Phase 6", "Deployment scripts, Kubernetes manifests, monitoring"),
    ]

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan")
    table.add_column("Phase", justify="center")
    table.add_column("Capabilities")

    for name, phase, capabilities in agent_info:
        table.add_row(name, phase, capabilities)

    console.print(table)


@main.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate configuration and environment.

    Checks that all required configuration is present and valid.
    """
    print_banner()

    config_manager: ConfigManager = ctx.obj["config"]

    console.print("\n[bold]Configuration Validation[/bold]\n")

    # Required settings
    required = [
        ("DATABASE_URL", "Database connection string"),
        ("REDIS_URL", "Redis connection string"),
        ("LOG_LEVEL", "Logging level"),
        ("CONTEXT_BUDGET", "Token budget"),
    ]

    # Optional settings
    optional = [
        ("GITHUB_TOKEN", "GitHub API token"),
        ("SUPABASE_URL", "Supabase project URL"),
        ("TF_CLOUD_TOKEN", "Terraform Cloud token"),
    ]

    all_valid = True

    console.print("[bold cyan]Required Settings:[/bold cyan]")
    for key, description in required:
        value = config_manager.get(key)
        if value:
            console.print(f"  [green]✓[/green] {key}: configured")
        else:
            console.print(f"  [red]✗[/red] {key}: missing ({description})")
            all_valid = False

    console.print("\n[bold cyan]Optional Settings:[/bold cyan]")
    for key, description in optional:
        value = config_manager.get(key)
        if value:
            console.print(f"  [green]✓[/green] {key}: configured")
        else:
            console.print(f"  [yellow]○[/yellow] {key}: not configured ({description})")

    console.print()
    if all_valid:
        console.print("[bold green]All required configuration is valid![/bold green]")
    else:
        console.print("[bold red]Some required configuration is missing![/bold red]")
        console.print("Copy .env.example to .env and configure the missing values.")
        sys.exit(1)


if __name__ == "__main__":
    main()
