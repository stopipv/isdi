"""Web interface modules"""

from flask_sqlalchemy import SQLAlchemy

# Global app reference for legacy code
app = None

# SQLAlchemy instance
sa = SQLAlchemy()


def init_routes(flask_app):
    """Initialize all routes"""
    global app
    app = flask_app

    # Import all view modules - they'll register their routes via @app.route decorators
    try:
        from isdi.web.view import (
            index,
            consult,
            scan,
            instructions,
            control,
            details,
            privacy,
            error,
            results,
            save,
        )
    except Exception as e:
        print(f"Warning: Could not load all view modules: {e}")
        import traceback

        traceback.print_exc()

        # Capture exception details for closure
        exc_error = str(e)
        exc_traceback = traceback.format_exc()

        # Create minimal fallback route
        @flask_app.route("/")
        def index_fallback():
            return f"""
            <html>
            <head><title>ISDI</title></head>
            <body>
                <h1>ISDI - Intimate Surveillance Detection Instrument</h1>
                <p><strong>Error loading web interface:</strong> {exc_error}</p>
                <p>The server is running but some routes failed to load.</p>
                <hr>
                <pre>{exc_traceback}</pre>
            </body>
            </html>
            """


__all__ = ["init_routes", "app", "sa"]
