import json
import re

from flask import Blueprint, render_template

from app.blueprints.utils import process_styled_text

bp = Blueprint("codex", __name__, url_prefix="/codex", static_folder="../static/")

MECHANICS = {}
ACHIEVEMENTS = {}


def fix_break(old_txt: str):
    return re.sub(r"\n<green>", "\n\n<green>", old_txt)


def init_lists() -> None:
    with bp.open_resource("../static/json/lore.json", "r") as fp:
        for data_entry in json.load(fp):
            if data_entry["category"] == "Guide" and not data_entry["nid"].endswith(
                "_Achievements"
            ):
                MECHANICS[data_entry["nid"]] = {
                    "name": data_entry["name"],
                    "title": data_entry["title"],
                    "text": process_styled_text(data_entry["text"]),
                }
            elif data_entry["nid"].endswith("_Achievements"):
                ACHIEVEMENTS[data_entry["nid"]] = {
                    "name": data_entry["name"],
                    "title": data_entry["title"],
                    "text": process_styled_text(fix_break(data_entry["text"])),
                }


init_lists()


@bp.route("/")
def get_codex_index() -> str:
    return render_template("codex_index.html.jinja2")


@bp.route("/mechanics")
def get_codex_mechanics() -> str:
    return render_template("codex_mechanics.html.jinja2", mechanics=MECHANICS)


@bp.route("/achievements")
def get_codex_achievements() -> str:
    return render_template("codex_achievements.html.jinja2", achievements=ACHIEVEMENTS)
