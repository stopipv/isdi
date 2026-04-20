"""Flask application factory"""

from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

__all__ = ["create_app"]


def create_app(config=None):
    """Create and configure Flask application"""
    from isdi.config import get_config

    if config is None:
        config = get_config()

    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "web" / "templates"),
        static_folder=str(Path(__file__).parent / "web" / "static"),
    )

    # Configuration
    app.config["SECRET_KEY"] = config.FLASK_SECRET
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{config.database_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Store config in app
    app.config["ISDI_CONFIG"] = config

    # Initialize extensions
    from isdi.web import sa

    sa.init_app(app)

    try:
        from isdi.scanner.db import init_db

        init_db(app, sa, force=config.TEST)
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")

    # Register routes
    try:
        from isdi.web import init_routes

        init_routes(app)
    except Exception as e:
        print(f"Warning: Could not register routes: {e}")

        # Create a simple test route
        @app.route("/")
        def index():
            return f"""
            <html>
            <head><title>ISDI</title></head>
            <body>
                <h1>ISDI - Intimate Surveillance Detection Instrument</h1>
                <p>Server is running but web routes are not fully initialized.</p>
                <p>Data directory: {config.dirs['data']}</p>
                <p>Database: {config.database_path}</p>
            </body>
            </html>
            """

    return app
