from itertools import groupby

from flask import Blueprint, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models import Class, ClassCategory

bp = Blueprint(
    "classes",
    __name__,
    url_prefix="/classes",
)


@bp.route("/")
def get_fe_class_index() -> str:
    stmt = select(ClassCategory).order_by(ClassCategory.order_key)
    class_cats = db.session.execute(stmt).scalars().all()
    ordered_class_cats = groupby(class_cats, key=lambda x: x.type)
    selected_category = request.args.get("selectedCategory")
    return render_template(
        "class_index.html.jinja2",
        class_cats=ordered_class_cats,
        selected_category=selected_category,
    )


@bp.route("/categories")
def get_class_list():
    if not (class_cat_nid := request.args.get("classCategory")):
        class_cat_nid = "class_tier_t1"
    class_cat = db.get_or_404(ClassCategory, class_cat_nid)
    unordered_items = class_cat.classes
    if not (class_cat_sort := request.args.get("classSort")):
        class_cat_sort = "alpha_inc"
    grouped_classes = []
    sort_reverse = class_cat_sort.endswith("dec")
    if class_cat_sort.startswith("alpha_"):
        unordered_items.sort(key=lambda x: x.name[0].upper())
        for group_name, group_iterator in groupby(
            unordered_items, key=lambda x: x.name[0].upper()
        ):
            group_list = list(group_iterator)
            grouped_classes.append(
                {
                    "key": group_name,
                    "classes": sorted(group_list, key=lambda x: x.name),
                }
            )
        grouped_classes.sort(key=lambda x: x["key"], reverse=sort_reverse)

    return render_template(
        "class_index_list.jinja2",
        grouped_classes=grouped_classes,
    )


@bp.route("/<string:fe_class_nid>")
def get_fe_class_sheet(fe_class_nid="Eirika_Lord") -> str:
    class_data = db.get_or_404(Class, fe_class_nid)
    return render_template(
        "class_sheet.html.jinja2",
        class_data=class_data,
    )
