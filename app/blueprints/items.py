import json
import re
from dataclasses import dataclass

from flask import Blueprint, render_template, request

bp = Blueprint("items", __name__, url_prefix="/items", static_folder="../static/")


@dataclass
class FEItem:
    nid: str
    name: str
    desc: str
    value: int
    weapon_rank: str
    weapon_type: str
    target: str
    damage: int
    weight: int
    crit: int
    hit: int
    min_range: int
    max_range: int
    icon_class: str


@dataclass
class FEUnit:
    nid: str
    name: str


ITEMS = {}
ITEM_CATS = {}
UNITS = {}
ARSENAL_UNITS = {}
with bp.open_resource("../static/json/arsenals.json", "r") as f:
    ARSENALS = json.load(f)


def get_comp(data_entry, comp_name: str):
    if comp_entry := [x for x in data_entry["components"] if x[0] == comp_name]:
        if comp_entry[0][1] is None:
            return 1
        return comp_entry[0][1]
    return 0


def get_comp_str(data_entry, comp_name: str):
    if comp_entry := [x for x in data_entry["components"] if x[0] == comp_name]:
        if comp_entry[0][1] is None:
            return " "
        return comp_entry[0][1]
    return ""


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
    # Remove invalid characters and replace spaces with underscores
    cleaned_s = "".join(c for c in s if c.isalnum() or c == " ").replace(" ", "_")

    # Ensure it starts with a letter or underscore
    if cleaned_s and not cleaned_s[0].isalpha() and cleaned_s[0] != "_":
        cleaned_s = "_" + cleaned_s

    # Convert to PascalCase (optional, but common for Python class names)
    parts = cleaned_s.split("_")
    pascal_case_name = "".join(part.capitalize() for part in parts)

    if pascal_case_name[0] in "1234567890":
        pascal_case_name = "x" + pascal_case_name

    return pascal_case_name


def init_lists() -> None:
    with bp.open_resource("../static/json/units.json", "r") as fp:
        for unit_data in json.load(fp):
            UNITS[unit_data["nid"]] = {
                "name": unit_data["name"],
                "nid": unit_data["nid"],
            }
    with bp.open_resource("../static/json/units.category.json", "r") as fp:
        for unit_nid, unit_cat in json.load(fp).items():
            if unit_nid in ARSENALS:
                if unit_cat in ARSENAL_UNITS:
                    ARSENAL_UNITS[unit_cat].append(
                        {"nid": unit_nid, "name": UNITS[unit_nid]["name"]}
                    )
                else:
                    ARSENAL_UNITS[unit_cat] = [
                        {"nid": unit_nid, "name": UNITS[unit_nid]["name"]}
                    ]
    with bp.open_resource("../static/json/items.json", "r") as fp:
        for data_entry in json.load(fp):
            if target := [
                x for x in data_entry["components"] if x[0].startswith("target")
            ]:
                target = target[0][0].split("_")[1].title()
            else:
                target = ""
            ITEMS[data_entry["nid"]] = FEItem(
                nid=data_entry["nid"],
                name=data_entry["name"],
                desc=process_styled_text(data_entry["desc"]),
                value=(
                    get_comp(data_entry, "value")
                    if get_comp(data_entry, "value")
                    else 0
                ),
                weapon_rank=get_comp_str(data_entry, "weapon_rank"),
                weapon_type=get_comp_str(data_entry, "weapon_type"),
                damage=(
                    get_comp(data_entry, "damage")
                    if get_comp(data_entry, "damage")
                    else 0
                ),
                weight=(
                    get_comp(data_entry, "weight")
                    if get_comp(data_entry, "weight")
                    else 0
                ),
                crit=(
                    get_comp(data_entry, "crit") if get_comp(data_entry, "crit") else 0
                ),
                hit=(get_comp(data_entry, "hit") if get_comp(data_entry, "hit") else 0),
                min_range=(
                    get_comp(data_entry, "min_range")
                    if get_comp(data_entry, "min_range")
                    else 0
                ),
                max_range=(
                    get_comp(data_entry, "max_range")
                    if get_comp(data_entry, "max_range")
                    else 0
                ),
                target=target,
                icon_class=(
                    f"{make_valid_class_name(data_entry["nid"])}-icon {make_valid_class_name(data_entry["icon_nid"])}-icon"
                    if data_entry["icon_nid"]
                    else ""
                ),
            )
    # Make item categories
    ITEM_CATS["Dragon's Gate"] = {
        x: x_val for x, x_val in ITEMS.items() if x.endswith("_DG")
    }


init_lists()


@bp.route("/")
def get_fe_item_index() -> str:
    if item_id := request.args.get("itemSelect"):
        template = "item_sheet.html.jinja2"
    else:
        item_id = "Iron_Sword"
        template = "item_index.html.jinja2"
    return render_template(
        template,
        item_data=ITEMS[item_id],
        item_cats=ITEM_CATS,
    )


@bp.route("/<string:fe_item_nid>")
def get_fe_item_sheet(fe_item_nid="Iron_Sword_Test") -> str:
    fe_item_data = ITEMS[fe_item_nid]
    return render_template("item_sheet.html.jinja2", item_data=fe_item_data)


@bp.route("/arsenals")
def get_fe_arsenal() -> str:
    if fe_unit_nid := request.args.get("unitSelect"):
        template = "arsenal_sheet.html.jinja2"
    else:
        fe_unit_nid = "Eirika"
        template = "arsenal_index.html.jinja2"
    return render_template(
        template,
        unit_data=UNITS[fe_unit_nid],
        unit_arsenals=ARSENALS[fe_unit_nid],
        arsenal_units=ARSENAL_UNITS,
    )


@bp.route("/arsenals/<string:fe_unit_nid>")
def get_fe_arsenal_sheet(fe_unit_nid="Artur") -> str:
    return render_template(
        "arsenal_sheet.html.jinja2",
        unit_data=UNITS[fe_unit_nid],
        unit_arsenals=ARSENALS[fe_unit_nid],
        arsenal_units=ARSENAL_UNITS,
    )
