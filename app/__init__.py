from flask import Flask, Response, render_template

from app.blueprints import items, units


def page_not_found(e):
    return render_template("404.html.jinja2"), 404


def internal_server_error(e):
    return render_template("500.html.jinja2"), 500


def create_app() -> Flask:

    app = Flask(__name__)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return app.send_static_file("favicon.ico")

    @app.route("/")
    @app.route("/index")
    def index() -> str:
        return render_template("index.html.jinja2", h1_title="home")

    app.register_blueprint(units.bp)
    app.register_blueprint(items.bp)

    return app
