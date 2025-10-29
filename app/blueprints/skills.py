import json
import re
from dataclasses import dataclass

from flask import Blueprint, render_template, request

bp = Blueprint("skills", __name__, url_prefix="/skills", static_folder="../static/")


@dataclass
class FESkill:
    nid: str
    name: str
    desc: str
    icon_class: str


SKILLS = {}
SKILL_CATS = {}


def convert_func(matchobj):
    if m := matchobj.group(1):
        return f'<span class="{make_valid_class_name(m)}-subIcon"></span>'
    return ""


def process_styled_text(raw_text) -> str:
    """
    Converts in-game desc tags to html. Note that this uses pico.css, so remember to change the
    classes to get proper colors.
    """
    new_text = raw_text
    replacements: tuple[
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
    ] = (
        (
            r"\<icon\>(.*?)\</\>",
            convert_func,
        ),
        (r"\<([^/]*?)\>(.*?)(\</\>)", r'<span class="pico-color-\1-500">\2</span>'),
        (r"{e:(.*?)}", r""),
        (r" \(<span class=\"pico-color-red-500\"></span>\)", r""),
        (r"\n", r"<br/>"),
    )
    for pattern, replacement in replacements:
        new_text = re.sub(pattern, replacement, new_text)
    return new_text


def make_valid_class_name(s):
    # Remove invalid characters and replace underscores with dashes and spaces with underscores
    cleaned_s = (
        "".join(c for c in s if c.isalnum() or c in (" ", "_", "-"))
        .replace("_", "-")
        .replace(" ", "_")
    )
    # Ensure it starts with a letter or underscore
    if cleaned_s and not cleaned_s[0].isalpha():
        cleaned_s = "xx" + cleaned_s
    # Convert to PascalCase (optional, but common for Python class names)
    parts = cleaned_s.split("_")
    pascal_case_name = "-".join(part.capitalize() for part in parts)
    return pascal_case_name


def init_lists() -> None:
    with bp.open_resource("../static/json/skills.json", "r") as fp:
        for data_entry in json.load(fp):
            new_skill_data = FESkill(
                nid=data_entry["nid"],
                name=data_entry["name"],
                desc=process_styled_text(data_entry["desc"]),
                icon_class=(
                    f"{make_valid_class_name(data_entry["nid"])}-icon {make_valid_class_name(data_entry["icon_nid"])}-icon"
                    if data_entry["icon_nid"]
                    else ""
                ),
            )
            SKILLS[data_entry["nid"]] = new_skill_data
    with bp.open_resource("../static/json/skills.category.json", "r") as fp:
        for skill_nid, skill_cat in json.load(fp).items():
            if skill_cat not in SKILL_CATS:
                SKILL_CATS[skill_cat] = {}
            SKILL_CATS[skill_cat][skill_nid] = {
                "nid": SKILLS[skill_nid].nid,
                "name": SKILLS[skill_nid].name,
            }


init_lists()


@bp.route("/")
def get_fe_skill_index() -> str:
    if skill_nid := request.args.get("skillSelect"):
        template = "skill_sheet.html.jinja2"
    else:
        skill_nid = "Frightening_Debuff"
        template = "skill_index.html.jinja2"
    return render_template(
        template, skill_data=SKILLS[skill_nid], skill_cats=SKILL_CATS
    )


@bp.route("/<string:fe_skill_nid>")
def get_fe_skill_sheet(fe_skill_nid="Frightening_Debuff") -> str:
    return render_template("skill_sheet.html.jinja2", skill_data=SKILLS[fe_skill_nid])
