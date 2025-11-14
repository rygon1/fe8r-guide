from flask import Blueprint, render_template, request

from app.extensions import db
from app.models import Skill, SkillCategory

bp = Blueprint("skills", __name__, url_prefix="/skills", static_folder="../static/")


def _get_skill_cats():
    skill_cats = {}
    for entry in db.session.execute(
        db.select(SkillCategory)
        .where(SkillCategory.nid.startswith("MyUnit/T"))
        .order_by(SkillCategory.nid)
    ).scalars():
        print(entry)
        skill_cats[entry.name] = {
            x.nid: x.name
            for x in db.session.execute(
                db.select(Skill)
                .where(Skill.category_nid == entry.nid)
                .order_by(Skill.name)
            ).scalars()
        }
    return skill_cats


@bp.route("/")
def get_fe_skill_index() -> str:
    if skill_nid := request.args.get("skillSelect"):
        template = "skill_sheet.html.jinja2"
    else:
        skill_nid = "Frightening_Debuff"
        template = "skill_index.html.jinja2"
    skill_data = db.get_or_404(Skill, skill_nid)
    return render_template(
        template, skill_data=skill_data, skill_cats=_get_skill_cats()
    )


@bp.route("/<string:fe_skill_nid>")
def get_fe_skill_sheet(fe_skill_nid="Frightening_Debuff") -> str:
    skill_data = db.get_or_404(Skill, fe_skill_nid)
    return render_template("skill_sheet.html.jinja2", skill_data=skill_data)
