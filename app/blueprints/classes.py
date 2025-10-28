import json
import re
from dataclasses import dataclass

from flask import Blueprint, render_template, request

bp = Blueprint(
    "classes",
    __name__,
    url_prefix="/classes",
)


@dataclass
class FEStat:
    hp: int
    str: int
    mag: int
    skl: int
    spd: int
    lck: int
    df: int
    res: int
    con: int
    mov: int


def add_fe_stat(stat1: FEStat, stat2: FEStat) -> FEStat:
    return FEStat(
        hp=stat1.hp + stat2.hp,
        str=stat1.str + stat2.str,
        mag=stat1.mag + stat2.mag,
        skl=stat1.skl + stat2.skl,
        spd=stat1.spd + stat2.spd,
        lck=stat1.lck + stat2.lck,
        df=stat1.df + stat2.df,
        res=stat1.res + stat2.res,
        con=stat1.con + stat2.con,
        mov=stat1.mov + stat2.mov,
    )


def to_fe_stat(stat_data: dict) -> FEStat:
    try:
        return FEStat(
            hp=stat_data["HP"],
            str=stat_data["STR"],
            mag=stat_data["MAG"],
            skl=stat_data["SKL"],
            spd=stat_data["SPD"],
            lck=stat_data["LCK"],
            df=stat_data["DEF"],
            res=stat_data["RES"],
            con=stat_data["CON"],
            mov=stat_data["MOV"],
        )
    except KeyError:
        return FEStat(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


@dataclass
class FEClass:
    nid: str
    name: str
    desc: str
    tier: int
    turns_into: list
    tags: list
    bases: FEStat
    growths: FEStat
    growth_bonus: FEStat
    promotion: FEStat
    max_stats: FEStat
    learned_skills: list
    wexp_gain: list
    icon_nid: str
    icon_index: str
    map_sprite_nid: str
    combat_anim_nid: str


CLASSES = {}
CLASS_CATS: dict = {
    "Trainee/Untiered": {},
    "Tier 1": {},
    "Tier 2": {},
    "Tier 3": {},
}


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


def init_lists() -> None:
    print("Initializing lists ...")
    with bp.open_resource("../static/json/classes.json", "r") as fp:
        for data_entry in sorted(json.load(fp), key=lambda x: x["tier"], reverse=True):
            CLASSES[data_entry["nid"]] = FEClass(
                nid=data_entry["nid"],
                name=data_entry["name"],
                desc=process_styled_text(data_entry["desc"]),
                tier=data_entry["tier"],
                turns_into=[CLASSES[x] for x in data_entry["turns_into"] if x],
                tags=data_entry["tags"],
                bases=to_fe_stat(data_entry["bases"]),
                growths=to_fe_stat(data_entry["growths"]),
                growth_bonus=to_fe_stat(data_entry["growth_bonus"]),
                promotion=to_fe_stat(data_entry["promotion"]),
                max_stats=to_fe_stat(data_entry["max_stats"]),
                learned_skills=data_entry["learned_skills"],
                wexp_gain=data_entry["wexp_gain"],
                icon_nid=data_entry["icon_nid"],
                icon_index=data_entry["icon_index"],
                map_sprite_nid=data_entry["map_sprite_nid"],
                combat_anim_nid=data_entry["combat_anim_nid"],
            )
    for class_nid, class_data in CLASSES.items():
        match (class_data.tier):
            case 1:
                class_cat = CLASS_CATS["Tier 1"]
            case 2:
                class_cat = CLASS_CATS["Tier 2"]
            case 3:
                class_cat = CLASS_CATS["Tier 3"]
            case _:
                class_cat = CLASS_CATS["Trainee/Untiered"]

        class_cat[class_nid] = {"name": class_data.name, "nid": class_data.nid}


init_lists()


@bp.route("/")
def get_fe_class_index() -> str:
    if class_nid := request.args.get("classSelect"):
        template = "class_sheet.html.jinja2"
    else:
        class_nid = "Eirika_Lord"
        template = "class_index.html.jinja2"
    return render_template(
        template, class_data=CLASSES[class_nid], class_cats=CLASS_CATS
    )


@bp.route("/<string:fe_class_nid>")
def get_fe_class_sheet(fe_class_nid="Eirika_Lord") -> str:
    return render_template(
        "class_sheet.html.jinja2",
        class_data=CLASSES[fe_class_nid],
    )
