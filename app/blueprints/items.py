import json
from dataclasses import dataclass

from flask import Blueprint, render_template, request
from sqlalchemy import select

from app.blueprints.utils import get_comp, make_valid_class_name, process_styled_text
from app.extensions import db
from app.models import Item, Shop

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
    status_on_equip: list
    icon_class: str
    sub_items: list


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


def get_status_equip(data_entry) -> list:
    exclude: tuple = (
        "_hide",
        "_Penalty",
        "_Buff",
        "_Effect",
        "_Gain",
        "_Proc",
        "_Weapon",
        "_AOE_Splash",
        "Drench",
        "Avo_Ddg_",
        "Luckblade",  # TODO
    )
    wp_status = []
    if s1 := get_comp(data_entry, "status_on_equip", str):
        if not any(sub in s1 for sub in exclude):
            wp_status.append(s1)
    if s2 := get_comp(data_entry, "multi_status_on_equip", list):
        for entry in s2:
            if not any(sub in entry for sub in exclude):
                wp_status.append(entry)
    return wp_status


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
                value=get_comp(data_entry, "value", int),
                weapon_rank=get_comp(data_entry, "weapon_rank", str),
                weapon_type=get_comp(data_entry, "weapon_type", str),
                damage=get_comp(data_entry, "damage", int),
                weight=get_comp(data_entry, "weight", int),
                crit=get_comp(data_entry, "crit", int),
                hit=get_comp(data_entry, "hit", int),
                min_range=get_comp(data_entry, "min_range", int),
                max_range=get_comp(data_entry, "max_range", int),
                status_on_equip=get_status_equip(data_entry),
                target=target,
                icon_class=(
                    f"{make_valid_class_name(data_entry['nid'])}-item-icon {make_valid_class_name(data_entry['icon_nid'])}-icon"
                    if data_entry["icon_nid"]
                    else ""
                ),
                sub_items=get_comp(data_entry, "multi_item", list),
            )

    with bp.open_resource("../static/json/items.category.new.json", "r") as fp:
        for x, x_val in json.load(fp).items():
            ITEM_CATS[x] = x_val


init_lists()


@bp.route("/")
def get_fe_item_index() -> str:
    if item_nid := request.args.get("itemSelect"):
        template = "item_sheet.html.jinja2"
    else:
        item_nid = "Iron_Sword"
        template = "item_index.html.jinja2"
    item_data = db.get_or_404(Item, item_nid)
    return render_template(
        template,
        item_data=item_data,
        item_cats=ITEM_CATS,
    )


@bp.route("/<string:fe_item_nid>")
def get_fe_item_sheet(fe_item_nid="Iron_Sword_Test") -> str:
    item_data = db.get_or_404(Item, fe_item_nid)
    return render_template("item_sheet.html.jinja2", item_data=item_data)


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


@bp.route("/shops")
def get_shop_index() -> str:
    stmt = select(Shop).order_by(Shop.order_name.asc())
    shops = db.session.execute(stmt).scalars().all()
    if shop_nid := request.args.get("shopSelect"):
        template = "shop_sheet.html.jinja2"
    else:
        shop_nid = "Global IdeArmory"
        template = "shop_index.html.jinja2"
    shop_data = db.get_or_404(Shop, shop_nid)
    wtypes = set(x.weapon_type for x in shop_data.items)
    return render_template(template, shop_data=shop_data, shops=shops, wtypes=wtypes)


@bp.route("/shops/<string:shop_nid>")
def get_shop_sheet(shop_nid="Global IdeArmory") -> str:
    shop_data = db.get_or_404(Shop, shop_nid)
    wtypes = set(x.weapon_type for x in shop_data.items)
    return render_template("shop_sheet.html.jinja2", shop_data=shop_data, wtypes=wtypes)
