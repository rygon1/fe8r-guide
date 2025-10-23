import json
from dataclasses import dataclass

from flask import Blueprint, render_template, request

bp = Blueprint(
    "units",
    __name__,
    url_prefix="/units",
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


@dataclass
class FEUnit:
    nid: str
    name: str
    desc: str
    level: str
    base_class_data: FEClass | None
    affinity: str
    bases: FEStat
    growths: FEStat
    stat_caps: FEStat
    stat_cap_modifiers: FEStat
    portrait_nid: str


FE_UNITS: list[FEUnit] = []
FE_CLASSES: list[FEClass] = []
FE_UNITS_CAT: dict = {
    "Vanilla": [],
    "Monsters": [],
    "Dragon Gate": [],
}


def get_fe_class_from_nid(fe_class_nid: str) -> FEClass | None:
    for entry in FE_CLASSES:
        if entry.nid == fe_class_nid:
            return entry
    return None


def get_fe_unit_from_nid(fe_unit_nid: str) -> FEUnit | None:
    for entry in FE_UNITS:
        if entry.nid == fe_unit_nid:
            return entry
    return None


def init_lists() -> None:
    print("Initializing lists ...")
    with bp.open_resource("../static/json/classes.json", "r") as fp:
        for data_entry in sorted(json.load(fp), key=lambda x: x["tier"], reverse=True):
            FE_CLASSES.append(
                FEClass(
                    nid=data_entry["nid"],
                    name=data_entry["name"],
                    desc=data_entry["desc"],
                    tier=data_entry["tier"],
                    turns_into=(
                        [get_fe_class_from_nid(x) for x in data_entry["turns_into"]]
                        if data_entry["turns_into"]
                        else data_entry["turns_into"]
                    ),
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
            )
    with bp.open_resource("../static/json/units.json", "r") as fp:
        for data_entry in json.load(fp):
            stat_caps: FEStat = FEStat(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            for classdata in FE_CLASSES:
                if classdata.nid == data_entry["klass"]:
                    stat_caps = classdata.max_stats
            FE_UNITS.append(
                FEUnit(
                    nid=data_entry["nid"],
                    name=data_entry["name"],
                    desc=data_entry["desc"],
                    level=data_entry["level"],
                    base_class_data=get_fe_class_from_nid(data_entry["klass"]),
                    affinity=data_entry["affinity"],
                    bases=to_fe_stat(data_entry["bases"]),
                    growths=to_fe_stat(data_entry["growths"]),
                    stat_caps=add_fe_stat(
                        to_fe_stat(data_entry["stat_cap_modifiers"]), stat_caps
                    ),
                    stat_cap_modifiers=to_fe_stat(data_entry["stat_cap_modifiers"]),
                    portrait_nid=data_entry["portrait_nid"],
                )
            )

    with bp.open_resource("../static/json/units.category.json", "r") as fp:
        for unit_nid, unit_cat in json.load(fp).items():
            if unit_cat in FE_UNITS_CAT and (
                unit_data := get_fe_unit_from_nid(unit_nid)
            ):
                FE_UNITS_CAT[unit_cat].append((unit_data.name, unit_data.nid))


init_lists()


# @bp.route("/")
@bp.route("/<string:fe_unit_nid>")
def get_fe_unit(fe_unit_nid="Eirika") -> str:
    fe_unit_data: FEUnit | None = get_fe_unit_from_nid(fe_unit_nid)
    return render_template(
        "unit_sheet.html.jinja2", unit_data=fe_unit_data, unit_cats=FE_UNITS_CAT
    )


@bp.route("/classes")
def get_fe_class() -> str:
    fe_class_nid = request.args.get("FEClassNid")
    fe_unit_nid = request.args.get("FEUnitNid")
    return render_template(
        "class_sheet.html.jinja2",
        class_data=get_fe_class_from_nid(fe_class_nid),
        unit_data=get_fe_unit_from_nid(fe_unit_nid),
    )
