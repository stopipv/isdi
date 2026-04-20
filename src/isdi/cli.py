"""Command-line interface for ISDI"""

import sys
import webbrowser
from threading import Timer
from pathlib import Path

import click

__all__ = ["main", "cli"]


@click.group()
@click.version_option(version="1.0.2")
def cli():
    """ISDI - Intimate Surveillance Detection Instrument

    A privacy and security scanner for mobile devices.
    """
    pass


@cli.command()
@click.option(
    "--host",
    default=None,
    help="Host to bind to (default: 127.0.0.1 in debug, 0.0.0.0 in production)",
)
@click.option("--port", type=int, default=None, help="Port to bind to (default: 6200)")
@click.option("--debug/--no-debug", default=False, help="Enable debug mode")
@click.option("--test", "test_mode", is_flag=True, help="Run in test mode")
@click.option("--no-browser", is_flag=True, help="Do not open browser automatically")
def run(host, port, debug, test_mode, no_browser):
    """Run the ISDI web server"""
    from isdi.config import get_config
    from isdi.app import create_app

    # Determine environment
    if test_mode:
        env = "test"
    elif debug:
        env = "development"
    else:
        env = "production"

    config = get_config(env)

    # Override from command line
    final_host = host or config.host
    final_port = port or config.port

    # Create app
    app = create_app(config)

    # Open browser after short delay
    if not no_browser and not debug and not test_mode:

        def open_browser():
            webbrowser.open(f"http://{final_host}:{final_port}")

        Timer(1.5, open_browser).start()

    click.echo(f"🔍 Starting ISDI on http://{final_host}:{final_port}")
    click.echo(f'📁 Data directory: {config.dirs["data"]}')
    click.echo(f"📊 Database: {config.database_path}")

    if test_mode:
        click.echo("🧪 Running in TEST mode")
    elif debug:
        click.echo("🐛 Running in DEBUG mode")

    # Setup logging
    config.setup_logger()

    # Run the app
    app.run(
        host=final_host,
        port=final_port,
        debug=config.DEBUG,
        use_reloader=config.DEBUG,
        reloader_type=(
            "stat" if config.DEBUG else None
        ),  # Use stat-based reloader for better reliability
        extra_files=None,
    )


@cli.command()
def info():
    """Show configuration and directory information"""
    from isdi.config import get_config

    config = get_config()

    click.echo("ISDI Configuration:")
    click.echo(f"  Environment: {config.env}")
    click.echo(f"\nDirectories:")
    click.echo(f'  Data: {config.dirs["data"]}')
    click.echo(f'  Config: {config.dirs["config"]}')
    click.echo(f'  Cache: {config.dirs["cache"]}')
    click.echo(f"\nData Locations:")
    click.echo(f"  Database: {config.database_path}")
    click.echo(f"  Scans: {config.scans_dir}")
    click.echo(f"  Reports: {config.reports_dir}")
    click.echo(f"  Dumps: {config.dumps_dir}")
    click.echo(f"  Logs: {config.logs_dir}")
    click.echo(f"\nPackage Data:")
    click.echo(f"  Location: {config.package_data}")
    click.echo(f"  Stalkerware DB: {config.stalkerware_path}")


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to reset all data?")
def reset():
    """Reset all user data (scans, reports, database)"""
    import shutil
    from isdi.config import get_config

    config = get_config()

    click.echo("Resetting data...")

    # Remove data directories
    for dir_path in [
        config.scans_dir,
        config.reports_dir,
        config.dumps_dir,
        config.phone_dumps_dir,
    ]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True)
            click.echo(f"  ✓ Cleared {dir_path.name}/")

    # Remove database
    if config.database_path.exists():
        config.database_path.unlink()
        click.echo(f"  ✓ Deleted database")

    # Remove cache
    if config.dirs["cache"].exists():
        shutil.rmtree(config.dirs["cache"])
        config.dirs["cache"].mkdir(parents=True)
        click.echo(f"  ✓ Cleared cache")

    click.echo("\n✓ All data has been reset")


@cli.command()
def paths():
    """Show all configured paths"""
    from isdi.config import get_config
    import json

    config = get_config()

    paths_dict = {
        "directories": {k: str(v) for k, v in config.dirs.items()},
        "data": {
            "database": str(config.database_path),
            "scans": str(config.scans_dir),
            "reports": str(config.reports_dir),
            "dumps": str(config.dumps_dir),
            "logs": str(config.logs_dir),
        },
        "package": {
            "data": str(config.package_data),
            "stalkerware": str(config.stalkerware_path),
        },
        "secrets": {
            "pii_key": str(config.pii_key_file),
            "flask_secret": str(config.flask_secret_file),
        },
    }

    click.echo(json.dumps(paths_dict, indent=2))


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
