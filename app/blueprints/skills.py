from itertools import groupby

from flask import Blueprint, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models import Skill, SkillCategory

bp = Blueprint("skills", __name__, url_prefix="/skills", static_folder="../static/")


@bp.route("/")
def get_fe_skill_index() -> str:
    stmt = select(SkillCategory).order_by(SkillCategory.order_key)
    skill_cats = db.session.execute(stmt).scalars().all()
    ordered_skill_cats = groupby(skill_cats, key=lambda x: x.type)
    selected_category = request.args.get("selectedCategory")
    return render_template(
        "skill_index.html.jinja2",
        skill_cats=ordered_skill_cats,
        selected_category=selected_category,
    )


@bp.route("/categories")
def get_skill_list():
    if not (skill_cat_nid := request.args.get("skillCategory")):
        skill_cat_nid = "feat_t1"
    skill_cat = db.get_or_404(SkillCategory, skill_cat_nid)
    unordered_items = skill_cat.skills
    if not (skill_cat_sort := request.args.get("skillSort")):
        skill_cat_sort = "alpha_inc"
    grouped_skills = []
    sort_reverse = skill_cat_sort.endswith("dec")
    if skill_cat_sort.startswith("alpha_"):
        unordered_items.sort(key=lambda x: x.name[0].upper())
        for group_name, group_iterator in groupby(
            unordered_items, key=lambda x: x.name[0].upper()
        ):
            group_list = list(group_iterator)
            grouped_skills.append(
                {
                    "key": group_name,
                    "skills": sorted(group_list, key=lambda x: x.name),
                }
            )
        grouped_skills.sort(key=lambda x: x["key"], reverse=sort_reverse)
    if not (view := request.args.get("view")):
        view = "list"

    return render_template(
        "skill_index_list.jinja2", grouped_skills=grouped_skills, view=view
    )


@bp.route("/<string:fe_skill_nid>")
def get_fe_skill_sheet(fe_skill_nid="Frightening_Debuff") -> str:
    skill_data = db.get_or_404(Skill, fe_skill_nid)
    return render_template("skill_sheet.html.jinja2", skill_data=skill_data)
