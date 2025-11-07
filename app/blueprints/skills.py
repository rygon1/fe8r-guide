import json
from dataclasses import dataclass

from flask import Blueprint, render_template, request

from app.blueprints.utils import make_valid_class_name, process_styled_text

bp = Blueprint("skills", __name__, url_prefix="/skills", static_folder="../static/")


@dataclass
class FESkill:
    nid: str
    name: str
    desc: str
    icon_class: str


SKILLS = {}
SKILL_CATS = {
    "Feats (Tier 1)": {},
    "Feats (Tier 2)": {},
    "Feats (Tier 3)": {},
}


def init_lists() -> None:
    with bp.open_resource("../static/json/skills.json", "r") as fp:
        for data_entry in json.load(fp):
            new_skill_data = FESkill(
                nid=data_entry["nid"],
                name=data_entry["name"],
                desc=process_styled_text(data_entry["desc"]),
                icon_class=(
                    f"{make_valid_class_name(data_entry["nid"])}-icon {make_valid_class_name(data_entry["icon_nid"])}-icon"
                    if data_entry["icon_nid"]
                    else ""
                ),
            )
            SKILLS[data_entry["nid"]] = new_skill_data
    with bp.open_resource("../static/json/skills.category.json", "r") as fp:
        for skill_nid, _ in json.load(fp).items():
            if skill_nid[-3:-1] == "_T" and "_Pair_Up" not in skill_nid:
                feat_tier = skill_nid[-1]
                SKILL_CATS[f"Feats (Tier {feat_tier})"][skill_nid] = {
                    "nid": SKILLS[skill_nid].nid,
                    "name": SKILLS[skill_nid].name,
                }


init_lists()


@bp.route("/")
def get_fe_skill_index() -> str:
    if skill_nid := request.args.get("skillSelect"):
        template = "skill_sheet.html.jinja2"
    else:
        skill_nid = "Frightening_Debuff"
        template = "skill_index.html.jinja2"
    return render_template(
        template, skill_data=SKILLS[skill_nid], skill_cats=SKILL_CATS
    )


@bp.route("/<string:fe_skill_nid>")
def get_fe_skill_sheet(fe_skill_nid="Frightening_Debuff") -> str:
    return render_template("skill_sheet.html.jinja2", skill_data=SKILLS[fe_skill_nid])
