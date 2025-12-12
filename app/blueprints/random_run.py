import random

from flask import Blueprint, render_template, request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Class, ClassCategory, Unit, UnitCategory

bp = Blueprint(
    "random_run", __name__, url_prefix="/random-run", static_folder="../static/"
)


@bp.route("/")
def get_random_run_index() -> str:
    return render_template(
        "random_run_index.html.jinja2",
    )


@bp.route("/generate", methods=["POST"])
def get_random_run_output() -> str:
    input_form = {}
    for input_name in (
        "lord",
        "num_units",
        "final_class_only",
        "unique_classes",
        "add_thief",
        "add_flier",
        "add_support",
        "include_monsters",
        "include_dg",
    ):
        input_form[input_name] = request.form.get(input_name)
    units = []
    if input_form["lord"] == "Random":
        units.append(db.get_or_404(Unit, random.choice(("Eirika", "Ephraim"))))
    else:
        units.append(db.get_or_404(Unit, input_form["lord"]))
    is_lord = or_(Unit.nid == "Eirika", Unit.nid == "Ephraim")
    units_remaining = int(input_form["num_units"]) - 1
    unit_categories_to_include = []
    unit_categories_to_include.append("Vanilla")
    if input_form["include_monsters"]:
        unit_categories_to_include.append("Monsters")
    if input_form["include_dg"]:
        unit_categories_to_include.append("Dragon Gate")
    include_unit_cat_conditions = or_(
        UnitCategory.nid == cat_name for cat_name in unit_categories_to_include
    )
    include_unit_cat_filter = Unit.categories.any(include_unit_cat_conditions)
    if input_form["add_thief"]:
        class_name_condition = or_(
            Class.name == "Thief", Class.name == "Pirate", Class.name == "Outlaw"
        )

        stmt = (
            select(Unit)
            .join(Unit.base_class)
            .where(
                and_(
                    class_name_condition,
                    include_unit_cat_filter,
                    # Unit.nid != "Dozla",
                    # Unit.nid != "Rennac",
                )
            )
            .options(joinedload(Unit.base_class))
        )

        target_units = db.session.scalars(stmt).all()
        units.append(random.choice(target_units))
        units_remaining -= 1

    if input_form["add_flier"]:
        category_condition = Class.categories.any(
            ClassCategory.nid == "class_cat_flying"
        )
        stmt = (
            select(Unit)
            .join(Unit.base_class)
            .where(and_(category_condition, include_unit_cat_filter))
            .options(joinedload(Unit.base_class).selectinload(Class.categories))
        )

        flying_units = db.session.scalars(stmt).all()
        units.append(random.choice(flying_units))
        units_remaining -= 1

    if input_form["add_support"]:
        category_condition = Class.categories.any(
            ClassCategory.nid == "class_cat_support"
        )
        stmt = (
            select(Unit)
            .join(Unit.base_class)
            .where(and_(category_condition, include_unit_cat_filter))
            .options(joinedload(Unit.base_class).selectinload(Class.categories))
        )

        flying_units = db.session.scalars(stmt).all()
        units.append(random.choice(flying_units))
        units_remaining -= 1

    stmt = (
        select(Unit)
        .where(and_(include_unit_cat_filter, ~is_lord))
        .order_by(func.random())
        .limit(units_remaining)
    )

    random_units = db.session.scalars(stmt).all()
    units += random_units
    output_map = {}
    for unit in units:
        output_map[unit.nid] = [unit.base_class]
        if unit.base_class.turns_into:
            nxt_promo = random.choice(unit.base_class.turns_into)
            output_map[unit.nid].append(nxt_promo)
            if nxt_promo.turns_into:
                nxt_nxt_promo = random.choice(nxt_promo.turns_into)
                output_map[unit.nid].append(nxt_nxt_promo)
                if nxt_nxt_promo.turns_into:
                    fin_promo = random.choice(nxt_nxt_promo.turns_into)
                    output_map[unit.nid].append(fin_promo)

    return render_template(
        "random_run_output.html.jinja2", units=units, output_map=output_map
    )
