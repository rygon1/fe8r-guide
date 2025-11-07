import json
from dataclasses import dataclass

from flask import Blueprint, render_template, request

from app.blueprints.classes import FEClass
from app.blueprints.utils import get_alt_name, process_styled_text

bp = Blueprint(
    "units",
    __name__,
    url_prefix="/units",
)


@dataclass
class FEUnit:
    nid: str
    name: str
    desc: str
    level: str
    base_class_nid: str
    base_class_data: FEClass
    affinity: str
    bases: dict
    growths: dict
    stat_cap_modifiers: dict
    starting_items: list
    learned_skills: list
    weapons: list
    portrait_nid: str


UNITS = {}
UNIT_CATS: dict = {
    "Vanilla": {},
    "Monsters": {},
    "Dragon's Gate": {},
}
CLASSES = {}
CLASS_PROMOS = {}
SUPPORTS = {}
AFFINITIES = {}


def _get_classes():
    with bp.open_resource("../static/json/classes.json", "r") as fp:
        for data_entry in sorted(json.load(fp), key=lambda x: x["tier"], reverse=True):
            CLASSES[data_entry["nid"]] = FEClass(
                nid=data_entry["nid"],
                name=data_entry["name"],
                alt_name=get_alt_name(data_entry["name"], data_entry["nid"]),
                desc=process_styled_text(data_entry["desc"]),
                tier=data_entry["tier"],
                tags=data_entry["tags"],
                bases=data_entry["bases"],
                growths=data_entry["growths"],
                growth_bonus=data_entry["growth_bonus"],
                promotion=data_entry["promotion"],
                max_stats=data_entry["max_stats"],
                learned_skills=[
                    x
                    for x in data_entry["learned_skills"]
                    if x and not x[1].endswith("_hide")
                ],
                weapons=[x for x, y in data_entry["wexp_gain"].items() if y[0]],
                icon_nid=data_entry["icon_nid"],
                icon_index=data_entry["icon_index"],
                map_sprite_nid=data_entry["map_sprite_nid"],
                combat_anim_nid=data_entry["combat_anim_nid"],
            )
    with bp.open_resource("../static/json/classes.promos.json", "r") as fp:
        for class_nid, class_promo_data in json.load(fp).items():
            if class_nid not in CLASS_PROMOS:
                CLASS_PROMOS[class_nid] = {"turns_from": [], "turns_into": []}
            CLASS_PROMOS[class_nid]["turns_into"] = [
                CLASSES[x] for x in class_promo_data["turns_into"]
            ]
            CLASS_PROMOS[class_nid]["turns_from"] = [
                CLASSES[x] for x in class_promo_data["turns_from"]
            ]


def fix_stat_cap_modifiers(old_scm: dict):
    new_scm = {}
    for statname in (
        "HP",
        "STR",
        "MAG",
        "SKL",
        "SPD",
        "LCK",
        "DEF",
        "RES",
        "CON",
        "MOV",
    ):
        if statname in old_scm:
            new_scm[statname] = old_scm[statname]
        else:
            new_scm[statname] = 0
    return new_scm


def init_lists() -> None:
    print("Initializing units ...")
    _get_classes()

    with bp.open_resource("../static/json/units.json", "r") as fp:
        for data_entry in json.load(fp):
            UNITS[data_entry["nid"]] = FEUnit(
                nid=data_entry["nid"],
                name=data_entry["name"],
                desc=process_styled_text(data_entry["desc"]),
                level=data_entry["level"],
                base_class_nid=data_entry["klass"],
                base_class_data=CLASSES[data_entry["klass"]],
                affinity=data_entry["affinity"],
                bases=data_entry["bases"],
                growths=data_entry["growths"],
                stat_cap_modifiers=fix_stat_cap_modifiers(
                    data_entry["stat_cap_modifiers"]
                ),
                starting_items=[x[0] for x in data_entry["starting_items"]],
                learned_skills=[
                    x
                    for x in data_entry["learned_skills"]
                    if x and not x[1].endswith("_hide")
                ],
                weapons=[x for x, y in data_entry["wexp_gain"].items() if y[0]],
                portrait_nid=data_entry["portrait_nid"],
            )

    with bp.open_resource("../static/json/units.category.json", "r") as fp:
        exclude_unit = ("_Plushie", "Orson", "Orson_Evil", "Davius_Old", "MyUnit")
        for unit_nid, unit_cat in json.load(fp).items():
            if unit_nid not in exclude_unit:
                unit_data = UNITS[unit_nid]
                if unit_cat in UNIT_CATS:
                    UNIT_CATS[unit_cat][unit_data.nid] = unit_data.name
                elif unit_cat == "Dragon Gate":
                    UNIT_CATS["Dragon's Gate"][unit_data.nid] = unit_data.name
    with bp.open_resource("../static/json/affinities.json", "r") as fp:
        for data_entry in json.load(fp):
            AFFINITIES[data_entry["nid"]] = {}
            for key, val in data_entry.items():
                if key != "bonus":
                    AFFINITIES[data_entry["nid"]][key] = val
                else:
                    AFFINITIES[data_entry["nid"]][key] = []
                    for bonus_data in val:
                        AFFINITIES[data_entry["nid"]][key].append(
                            {
                                "RANK": bonus_data["support_rank"],
                                "ATK": bonus_data["damage"],
                                "DEF": bonus_data["resist"],
                                "HIT": bonus_data["accuracy"],
                                "AVOID": bonus_data["avoid"],
                                "CRIT": bonus_data["crit"],
                                "DODGE": bonus_data["dodge"],
                                "ATK SPD": bonus_data["attack_speed"],
                                "DEF SPD": bonus_data["defense_speed"],
                            }
                        )

    with bp.open_resource("../static/json/support_pairs.json", "r") as fp:
        for data_entry in json.load(fp):
            if data_entry["unit1"] not in SUPPORTS:
                SUPPORTS[data_entry["unit1"]] = {}
            SUPPORTS[data_entry["unit1"]][data_entry["unit2"]] = {
                "name": UNITS[data_entry["unit2"]].name,
                "affinity": AFFINITIES[UNITS[data_entry["unit2"]].affinity],
            }
            if data_entry["unit2"] not in SUPPORTS:
                SUPPORTS[data_entry["unit2"]] = {}
            SUPPORTS[data_entry["unit2"]][data_entry["unit1"]] = {
                "name": UNITS[data_entry["unit1"]].name,
                "affinity": AFFINITIES[UNITS[data_entry["unit1"]].affinity],
            }


init_lists()


@bp.route("/")
def get_fe_unit_index() -> str:
    if unit_nid := request.args.get("unitSelect"):
        template = "unit_sheet.html.jinja2"
    else:
        unit_nid = "Eirika"
        template = "unit_index.html.jinja2"
    return render_template(
        template,
        unit_data=UNITS[unit_nid],
        unit_promos=CLASS_PROMOS[UNITS[unit_nid].base_class_nid],
        unit_cats=UNIT_CATS,
        unit_supports=SUPPORTS[unit_nid] if unit_nid in SUPPORTS else [],
    )


@bp.route("/<string:fe_unit_nid>")
def get_fe_unit_sheet(fe_unit_nid="Eirika") -> str:
    return render_template(
        "unit_sheet.html.jinja2",
        unit_data=UNITS[fe_unit_nid],
        unit_promos=CLASS_PROMOS[UNITS[fe_unit_nid].base_class_nid],
        unit_supports=SUPPORTS[fe_unit_nid] if fe_unit_nid in SUPPORTS else [],
    )


@bp.route("/<string:fe_unit_nid>/classes")
def get_fe_unit_class(fe_unit_nid="Eirika", fe_class_nid="Eirika_Lord") -> str:
    if fe_class_nid := request.args.get("unitClassSelect"):
        pass
    else:
        fe_class_nid = "Eirika_Lord"
    return render_template(
        "unit_class_sheet.html.jinja2",
        unit_data=UNITS[fe_unit_nid],
        class_data=CLASSES[fe_class_nid],
        class_promo_data=CLASS_PROMOS[fe_class_nid],
    )
