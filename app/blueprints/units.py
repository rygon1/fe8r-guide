from itertools import groupby

from flask import Blueprint, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models import Class, Unit, UnitCategory

bp = Blueprint(
    "units",
    __name__,
    url_prefix="/units",
)


@bp.route("/")
def get_fe_unit_index() -> str:
    stmt = select(UnitCategory).order_by(UnitCategory.order_key)
    unit_cats = db.session.execute(stmt).scalars().all()
    ordered_unit_cats = groupby(unit_cats, key=lambda x: x.type)
    selected_category = request.args.get("selectedCategory")
    return render_template(
        "unit_index.html.jinja2",
        unit_cats=ordered_unit_cats,
        selected_category=selected_category,
    )


@bp.route("/categories")
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
    if not (view := request.args.get("view")):
        view = "list"
    return render_template(
        "unit_index_list.jinja2", grouped_units=grouped_units, view=view
    )


@bp.route("/<string:fe_unit_nid>")
def get_fe_unit_sheet(fe_unit_nid="Eirika") -> str:
    unit_data = db.get_or_404(Unit, fe_unit_nid)
    return render_template(
        "unit_sheet.html.jinja2",
        unit_data=unit_data,
    )


@bp.route("/<string:fe_unit_nid>/classes")
def get_fe_unit_class(fe_unit_nid="Eirika", fe_class_nid="Eirika_Lord") -> str:
    if fe_class_nid := request.args.get("unitClassSelect"):
        pass
    else:
        fe_class_nid = "Eirika_Lord"
    return render_template(
        "unit_class_sheet.html.jinja2",
        unit_data=db.get_or_404(Unit, fe_unit_nid),
        class_data=db.get_or_404(Class, fe_class_nid),
    )
