"""TAE CLI tool for development and operations.

Usage:
    tae benchmark            - Run performance benchmarks
    tae health-check         - Verify all dependencies
    tae validate-config      - Check environment configuration
    tae seed-test-data       - Populate test scenarios

Install:
    pip install -e .  # Development mode
    tae --help
"""

import typer
import asyncio
from typing import Optional, Annotated
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer(
    name="tae",
    help="Team Alignment Engine CLI - Developer tools and operations",
)

console = Console()


@app.command()
def benchmark(
    workload: Annotated[str, typer.Option(help="Workload type: standard, heavy, stress")] = "standard",
    duration: Annotated[int, typer.Option(help="Duration in seconds")] = 60,
    output: Annotated[Optional[str], typer.Option(help="Output file for results")] = None,
):
    """
    Run performance benchmarks against representative workloads.

    Measures request latency, throughput, and resource usage under various loads.
    """
    from src.cli.commands.benchmark import run_benchmark

    console.print(f"[bold blue]TAE Benchmark Tool[/bold blue]")
    console.print(f"Workload: {workload}, Duration: {duration}s\n")

    try:
        results = asyncio.run(run_benchmark(workload, duration))

        # Display results table
        table = Table(title="Benchmark Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for metric, value in results.items():
            table.add_row(metric, str(value))

        console.print(table)

        # Save to file if requested
        if output:
            import json
            from pathlib import Path
            output_path = Path(output)
            output_path.write_text(json.dumps(results, indent=2))
            console.print(f"\n[green]Results saved to {output}[/green]")

        # Exit with failure if performance below threshold
        if results.get("p95_latency_ms", 0) > 1000:
            console.print("[red]⚠ Performance below threshold (p95 > 1000ms)[/red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Benchmark failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def health_check(
    deep: Annotated[bool, typer.Option(help="Perform deep health check")] = False,
    json_output: Annotated[bool, typer.Option(help="Output as JSON")] = False,
):
    """
    Verify all dependencies (Redis, PostgreSQL, external services).

    Checks connectivity and response times for all TAE dependencies.
    """
    from src.cli.commands.health import check_health

    if not json_output:
        console.print("[bold blue]TAE Health Check[/bold blue]\n")

    try:
        health_status = asyncio.run(check_health(deep=deep))

        if json_output:
            import json
            print(json.dumps(health_status, indent=2))
        else:
            # Display health status
            for component, status in health_status.items():
                if status["status"] == "healthy":
                    console.print(f"✓ {component}: [green]{status['status']}[/green]")
                elif status["status"] == "degraded":
                    console.print(f"⚠ {component}: [yellow]{status['status']}[/yellow]")
                else:
                    console.print(f"✗ {component}: [red]{status['status']}[/red]")

                if "latency_ms" in status:
                    console.print(f"  Latency: {status['latency_ms']}ms")

        # Exit with failure if any component unhealthy
        if any(s["status"] == "unhealthy" for s in health_status.values()):
            if not json_output:
                console.print("\n[red]Health check failed[/red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"[red]Health check error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate_config(
    env: Annotated[str, typer.Option(help="Environment: development, staging, production")] = "development",
):
    """
    Check environment configuration for missing or invalid settings.

    Validates all required environment variables and configuration files.
    """
    from src.cli.commands.validate import validate_configuration

    console.print(f"[bold blue]TAE Configuration Validator[/bold blue]")
    console.print(f"Environment: {env}\n")

    try:
        validation_results = validate_configuration(env)

        # Display validation results
        for category, checks in validation_results.items():
            console.print(f"\n[bold]{category}:[/bold]")
            for check in checks:
                status = "✓" if check["valid"] else "✗"
                color = "green" if check["valid"] else "red"
                console.print(f"  {status} {check['name']}: [{color}]{check['message']}[/{color}]")

        # Exit with failure if any validation failed
        all_valid = all(
            all(check["valid"] for check in checks)
            for checks in validation_results.values()
        )

        if not all_valid:
            console.print("\n[red]Configuration validation failed[/red]")
            raise typer.Exit(code=1)
        else:
            console.print("\n[green]✓ Configuration valid[/green]")

    except Exception as e:
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def seed_test_data(
    scenario: Annotated[str, typer.Option(help="Scenario: default, complex, stress")] = "default",
    clear_existing: Annotated[bool, typer.Option(help="Clear existing data first")] = False,
):
    """
    Populate test scenarios for local development.

    Creates sample sessions, profiles, options, and decisions for testing.
    """
    from src.cli.commands.seed import seed_database

    console.print(f"[bold blue]TAE Test Data Seeder[/bold blue]")
    console.print(f"Scenario: {scenario}\n")

    if clear_existing:
        console.print("[yellow]Clearing existing data...[/yellow]")

    try:
        results = asyncio.run(seed_database(scenario, clear_existing))

        # Display seeding results
        table = Table(title="Seeding Results")
        table.add_column("Entity", style="cyan")
        table.add_column("Count", style="green")

        for entity, count in results.items():
            table.add_row(entity, str(count))

        console.print(table)
        console.print("\n[green]✓ Test data seeded successfully[/green]")

    except Exception as e:
        console.print(f"[red]Seeding failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def version():
    """Show TAE version information."""
    from src.config import settings

    console.print(f"[bold]Team Alignment Engine[/bold]")
    console.print(f"Version: {settings.service_version}")
    console.print(f"Environment: {settings.environment}")


if __name__ == "__main__":
    app()
