from sqlalchemy import Column, ForeignKey, String, Table
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


item_skill_assoc = Table(
    "item_skill_assoc",
    db.metadata,
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
    Column("skill_nid", String, ForeignKey("skills.nid"), primary_key=True),
)
sub_item_assoc = Table(
    "sub_item_assoc",
    db.metadata,
    Column("super_item_nid", String, ForeignKey("items.nid"), primary_key=True),
    Column("sub_item_nid", String, ForeignKey("items.nid"), primary_key=True),
)


class Item(db.Model):
    __tablename__ = "items"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    value: Mapped[int]
    weapon_rank: Mapped[str]
    weapon_type: Mapped[str]
    target: Mapped[str]
    damage: Mapped[int]
    weight: Mapped[int]
    crit: Mapped[int]
    hit: Mapped[int]
    min_range: Mapped[int]
    max_range: Mapped[int]
    icon_class: Mapped[str]

    sub_items = relationship(
        "Item",
        secondary=sub_item_assoc,
        primaryjoin=(sub_item_assoc.c.super_item_nid == nid),
        secondaryjoin=(sub_item_assoc.c.sub_item_nid == nid),
        backref="super_item",
    )
    status_on_equip = relationship(
        "Skill",
        secondary=item_skill_assoc,
        backref="items",
    )

    def __repr__(self) -> str:
        return f"Item(nid={self.nid!r}, name={self.name!r}, desc={self.desc!r})"
