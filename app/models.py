from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Skill(db.Model):
    __tablename__ = "skills"
    nid: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    desc: Mapped[str]
    icon_class: Mapped[str]
    is_hidden: Mapped[bool]
    category_nid: Mapped[str] = mapped_column(ForeignKey("skill_categories.nid"))
    category: Mapped["SkillCategory"] = relationship()

    def __repr__(self) -> str:
        return f"Skill(nid={self.nid!r}, name={self.name!r}, desc={self.desc!r})"


class SkillCategory(db.Model):
    __tablename__ = "skill_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    def __repr__(self) -> str:
        return f"SkillCategory(nid={self.nid!r}, name={self.name!r})"
