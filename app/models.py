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

item_category_assoc = Table(
    "item_category_assoc",
    db.metadata,
    Column("item_nid", ForeignKey("items.nid"), primary_key=True),
    Column("category_nid", ForeignKey("item_categories.nid"), primary_key=True),
)


class Item(db.Model):
    __tablename__ = "items"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    value: Mapped[int]
    weapon_rank: Mapped[str]
    weapon_rank_order_key: Mapped[str]
    weapon_type: Mapped[str]
    target: Mapped[str]
    damage: Mapped[int]
    weight: Mapped[int]
    crit: Mapped[int]
    hit: Mapped[int]
    min_range: Mapped[int]
    max_range: Mapped[int]
    icon_class: Mapped[str]
    categories: Mapped[list["ItemCategory"]] = relationship(
        secondary=item_category_assoc,
        back_populates="items",
    )

    sub_items = relationship(
        "Item",
        secondary=sub_item_assoc,
        primaryjoin=(sub_item_assoc.c.super_item_nid == nid),
        secondaryjoin=(sub_item_assoc.c.sub_item_nid == nid),
        backref="super_items",
    )
    status_on_equip = relationship(
        "Skill",
        secondary=item_skill_assoc,
        backref="items",
    )

    def __repr__(self) -> str:
        return f"Item(nid={self.nid!r}, name={self.name!r}, desc={self.desc!r})"


class ItemCategory(db.Model):
    __tablename__ = "item_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_key: Mapped[int]

    items: Mapped[list["Item"]] = relationship(
        secondary=item_category_assoc,
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"ItemCategory(nid={self.nid!r}, name={self.name!r})"


shop_item_assoc = Table(
    "shop_item_assoc",
    db.metadata,
    Column("shop_nid", String, ForeignKey("shops.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)


class Shop(db.Model):
    __tablename__ = "shops"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_name: Mapped[str]
    abbr_name: Mapped[str]

    items = relationship(
        "Item",
        secondary=shop_item_assoc,
        backref="shops",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"Shop(nid={self.nid!r}, name={self.name!r}, type={self.type!r})"


arsenal_item_assoc = Table(
    "arsenal_item_assoc",
    db.metadata,
    Column("arsenal_nid", String, ForeignKey("arsenals.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)


class Arsenal(db.Model):
    __tablename__ = "arsenals"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    arsenal_owner_nid: Mapped[int]
    icon_class: Mapped[str]

    items = relationship(
        "Item",
        secondary=arsenal_item_assoc,
        backref="arsenals",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"Arsenal(nid={self.nid!r}, name={self.name!r}, arsenal_owner_nid={self.arsenal_owner_nid!r})"
