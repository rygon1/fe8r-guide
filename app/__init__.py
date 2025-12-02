from flask import Flask, Response, render_template

from app.blueprints import classes, codex, items, skills, units
from app.config import Config
from app.extensions import db


def page_not_found(_):
    return render_template("404.html.jinja2"), 404


def internal_server_error(_):
    return render_template("500.html.jinja2"), 500


def currency_format(value):
    return f"{value:,}"


def growth_colors(value):
    color_ranges = [
        (10, "red-orange"),
        (20, "light-red"),
        (30, "pink-orange"),
        (40, "light-orange"),
        (50, "corn-yellow"),
        (60, "light-green"),
        (70, "olive-green"),
        (80, "soft-green"),
        (120, "yellow-green"),
        (160, "blue"),
        (200, "grey"),
        (250, "white"),
    ]

    for max_value, color in color_ranges:
        if value <= max_value:
            if value >= 0:
                return color
            return "yellow"
    return "red"


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)

    app.config.from_object(config_class)

    db.init_app(app)

    app.register_blueprint(units.bp)
    app.register_blueprint(items.bp)
    app.register_blueprint(skills.bp)
    app.register_blueprint(classes.bp)
    app.register_blueprint(codex.bp)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    app.jinja_env.filters["currency_format"] = currency_format
    app.jinja_env.filters["growth_colors"] = growth_colors

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return app.send_static_file("favicon.ico")

    @app.route("/")
    @app.route("/index")
    def index() -> str:
        return render_template("index.html.jinja2", h1_title="home")

    @app.route("/credits")
    def get_credits() -> str:
        return render_template("credits.html.jinja2")

    return app
