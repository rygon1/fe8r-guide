import json
from itertools import groupby

from flask import Blueprint, abort, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models import Arsenal, Item, ItemCategory, Shop, UnitCategory

bp = Blueprint("items", __name__, url_prefix="/items", static_folder="../static/")


UNITS = {}
ARSENAL_UNITS = {}
with bp.open_resource("../static/json/arsenals.json", "r") as f:
    ARSENALS = json.load(f)


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


init_lists()


@bp.route("/")
def get_fe_item_index() -> str:
    stmt = select(ItemCategory).order_by(ItemCategory.order_key)
    item_cats = db.session.execute(stmt).scalars().all()
    ordered_item_cats = groupby(item_cats, key=lambda x: x.type)
    selected_category = request.args.get("selectedCategory")
    return render_template(
        "item_index.html.jinja2",
        item_cats=ordered_item_cats,
        selected_category=selected_category,
    )


@bp.route("/categories")
def get_item_list():
    if not (item_cat_nid := request.args.get("itemCategory")):
        item_cat_nid = "wtype_Sword"
    item_cat = db.get_or_404(ItemCategory, item_cat_nid)
    unordered_items = item_cat.items
    if not (item_cat_sort := request.args.get("itemSort")):
        item_cat_sort = "wrank_inc"
    grouped_items = []
    sort_reverse = item_cat_sort.endswith("dec")
    if item_cat_sort.startswith("wrank_"):
        unordered_items.sort(key=lambda x: x.weapon_rank)
        for group_name, group_iterator in groupby(
            unordered_items, key=lambda x: x.weapon_rank
        ):
            group_list = list(group_iterator)
            order_key = int(group_list[0].weapon_rank_order_key)
            grouped_items.append(
                {
                    "key": group_name,
                    "order": order_key,
                    "items": sorted(group_list, key=lambda x: x.name),
                }
            )
        grouped_items.sort(key=lambda x: x["order"], reverse=sort_reverse)
    elif item_cat_sort.startswith("alpha_"):
        unordered_items.sort(key=lambda x: x.name[0].upper())
        for group_name, group_iterator in groupby(
            unordered_items, key=lambda x: x.name[0].upper()
        ):
            group_list = list(group_iterator)
            grouped_items.append(
                {
                    "key": group_name,
                    "items": sorted(group_list, key=lambda x: x.name),
                }
            )
        grouped_items.sort(key=lambda x: x["key"], reverse=sort_reverse)
    if not (view := request.args.get("view")):
        view = "list"
    return render_template(
        "item_index_list.jinja2", grouped_items=grouped_items, view=view
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
    stmt = select(Arsenal).where(Arsenal.arsenal_owner_nid == fe_unit_nid)
    unit_arsenals = db.session.execute(stmt).scalars().all()
    if not unit_arsenals:
        abort(404)
    return render_template(
        template,
        unit_arsenals=unit_arsenals,
        arsenal_units=ARSENAL_UNITS,
    )


@bp.route("/arsenals/categories")
def get_unit_list():
    if not (unit_cat_nid := request.args.get("unitCategory")):
        unit_cat_nid = "Eirika"
    unit_cat = db.get_or_404(UnitCategory, unit_cat_nid)
    unordered_items = unit_cat.units
    if not (unit_cat_sort := request.args.get("unitSort")):
        unit_cat_sort = "alpha_inc"
    grouped_units = []
    sort_reverse = unit_cat_sort.endswith("dec")
    if unit_cat_sort.startswith("alpha_"):
        unordered_items.sort(key=lambda x: x.name[0].upper())
        for group_name, group_iterator in groupby(
            unordered_items, key=lambda x: x.name[0].upper()
        ):
            group_list = list(group_iterator)
            grouped_units.append(
                {
                    "key": group_name,
                    "units": sorted(group_list, key=lambda x: x.name),
                }
            )
        grouped_units.sort(key=lambda x: x["key"], reverse=sort_reverse)

    return render_template(
        "arsenal_index_list.jinja2",
        grouped_units=grouped_units,
    )


@bp.route("/arsenals/<string:fe_unit_nid>")
def get_fe_arsenal_sheet(fe_unit_nid="Eirika") -> str:
    stmt = select(Arsenal).where(Arsenal.arsenal_owner_nid == fe_unit_nid)
    unit_arsenals = db.session.execute(stmt).scalars().all()
    return render_template(
        "arsenal_sheet.html.jinja2",
        unit_data=UNITS[fe_unit_nid],
        unit_arsenals=unit_arsenals,
    )


@bp.route("/shops")
def get_shop_index() -> str:
    stmt = select(Shop).order_by(Shop.order_name.asc())
    shops = db.session.execute(stmt).scalars().all()
    if shop_nid := request.args.get("shopSelect"):
        template = "shop_sheet.html.jinja2"
    else:
        shop_nid = "2_Armory_Global_IdeArmory"
        template = "shop_index.html.jinja2"
    shop_data = db.get_or_404(Shop, shop_nid)
    wtypes = set(x.weapon_type for x in shop_data.items)
    return render_template(template, shop_data=shop_data, shops=shops, wtypes=wtypes)


@bp.route("/shops/<string:shop_nid>")
def get_shop_sheet(shop_nid="2_Armory_Global_IdeArmory") -> str:
    shop_data = db.get_or_404(Shop, shop_nid)
    wtypes = set(x.weapon_type for x in shop_data.items)
    return render_template("shop_sheet.html.jinja2", shop_data=shop_data, wtypes=wtypes)
