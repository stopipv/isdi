from isdi.web import app


@app.route("/error")
def get_nothing():
    """Route for intentional error."""
    return "foobar"  # intentional non-existent variable
