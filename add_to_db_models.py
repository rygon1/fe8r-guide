from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


item_skill_assoc = Table(
    "item_skill_assoc",
    Base.metadata,
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
    Column("skill_nid", String, ForeignKey("skills.nid"), primary_key=True),
)

sub_item_assoc = Table(
    "sub_item_assoc",
    Base.metadata,
    Column("super_item_nid", String, ForeignKey("items.nid"), primary_key=True),
    Column("sub_item_nid", String, ForeignKey("items.nid"), primary_key=True),
)

item_category_assoc = Table(
    "item_category_assoc",
    Base.metadata,
    Column("item_nid", ForeignKey("items.nid"), primary_key=True),
    Column("category_nid", ForeignKey("item_categories.nid"), primary_key=True),
)

skill_category_assoc = Table(
    "skill_category_assoc",
    Base.metadata,
    Column("skill_nid", ForeignKey("skills.nid"), primary_key=True),
    Column("category_nid", ForeignKey("skill_categories.nid"), primary_key=True),
)

shop_item_assoc = Table(
    "shop_item_assoc",
    Base.metadata,
    Column("shop_nid", String, ForeignKey("shops.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)

class_turns_into_assoc = Table(
    "class_turns_into_assoc",
    Base.metadata,
    Column("base_class_nid", String, ForeignKey("classes.nid"), primary_key=True),
    Column("target_class_nid", String, ForeignKey("classes.nid"), primary_key=True),
)

class_category_assoc = Table(
    "class_category_assoc",
    Base.metadata,
    Column("class_nid", String, ForeignKey("classes.nid"), primary_key=True),
    Column(
        "category_nid", String, ForeignKey("class_categories.nid"), primary_key=True
    ),
)
unit_category_assoc = Table(
    "unit_category_assoc",
    Base.metadata,
    Column("unit_nid", String, ForeignKey("units.nid"), primary_key=True),
    Column("category_nid", String, ForeignKey("unit_categories.nid"), primary_key=True),
)
unit_support_assoc = Table(
    "unit_support_assoc",
    Base.metadata,
    Column("unit_id", String, ForeignKey("units.nid"), primary_key=True),
    Column("support_id", String, ForeignKey("units.nid"), primary_key=True),
)

arsenal_item_assoc = Table(
    "arsenal_item_assoc",
    Base.metadata,
    Column("arsenal_nid", String, ForeignKey("arsenals.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)

unit_item_assoc = Table(
    "unit_item_assoc",
    Base.metadata,
    Column("unit_nid", String, ForeignKey("units.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)

class_weapon_assoc = Table(
    "class_weapon_assoc",
    Base.metadata,
    Column("class_nid", String, ForeignKey("classes.nid"), primary_key=True),
    Column("weapon_nid", String, ForeignKey("weapons.nid"), primary_key=True),
)


class ClassSkillAssociation(Base):
    __tablename__ = "class_skill_assoc"

    class_nid: Mapped[str] = mapped_column(ForeignKey("classes.nid"), primary_key=True)
    skill_nid: Mapped[str] = mapped_column(ForeignKey("skills.nid"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)

    class_with_skill: Mapped["Class"] = relationship(back_populates="learned_skills")
    skill: Mapped["Skill"] = relationship(back_populates="class_associations")

    def __repr__(self) -> str:
        return f"ClassSkillAssociation(class_nid={self.class_nid!r}, skill_nid={self.skill_nid!r}, level={self.level!r})"


class UnitSkillAssociation(Base):
    __tablename__ = "unit_skill_assoc"

    unit_nid: Mapped[str] = mapped_column(ForeignKey("units.nid"), primary_key=True)
    skill_nid: Mapped[str] = mapped_column(ForeignKey("skills.nid"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer)

    units_with_skill: Mapped["Unit"] = relationship(back_populates="learned_skills")
    skill: Mapped["Skill"] = relationship(back_populates="unit_associations")

    def __repr__(self) -> str:
        return f"UnitSkillAssociation(unit_nid={self.unit_nid!r}, skill_nid={self.skill_nid!r}, level={self.level!r})"


class Skill(Base):
    __tablename__ = "skills"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    icon_class: Mapped[str]
    is_hidden: Mapped[bool]

    categories: Mapped[list["SkillCategory"]] = relationship(
        secondary=skill_category_assoc,
        back_populates="skills",
    )
    unit_associations: Mapped[list["UnitSkillAssociation"]] = relationship(
        back_populates="skill"
    )
    class_associations: Mapped[list["ClassSkillAssociation"]] = relationship(
        back_populates="skill"
    )

    def __repr__(self) -> str:
        return f"Skill(nid={self.nid!r}, name={self.name!r})"


class SkillCategory(Base):
    __tablename__ = "skill_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_key: Mapped[int]

    skills: Mapped[list["Skill"]] = relationship(
        secondary=skill_category_assoc,
        back_populates="categories",
    )

    def __repr__(self) -> str:
        return f"SkillCategory(nid={self.nid!r}, name={self.name!r})"


class Weapon(Base):
    __tablename__ = "weapons"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    icon_class: Mapped[str]

    def __repr__(self) -> str:
        return f"Weapon(nid={self.nid!r}, name={self.name!r})"


class Item(Base):
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
        return f"Item(nid={self.nid!r}, name={self.name!r})"


class ItemCategory(Base):
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


class Shop(Base):
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


class Arsenal(Base):
    __tablename__ = "arsenals"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    icon_class: Mapped[str]

    arsenal_owner_nid: Mapped[str] = mapped_column(
        ForeignKey("units.nid"), nullable=True
    )
    arsenal_owner: Mapped["Unit"] = relationship(back_populates="arsenals")

    items = relationship(
        "Item",
        secondary=arsenal_item_assoc,
        backref="arsenals",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"Arsenal(nid={self.nid!r}, name={self.name!r}, arsenal_owner_nid={self.arsenal_owner_nid!r})"


class Affinity(Base):
    """Represents an Affinity (e.g., Fire, Thunder) that a Unit can have."""

    __tablename__ = "affinities"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    bonus: Mapped[list] = mapped_column(JSON)
    icon_class: Mapped[str]

    units: Mapped[list["Unit"]] = relationship(back_populates="affinity")

    def __repr__(self) -> str:
        return f"Affinity(nid={self.nid!r}, name={self.name!r})"


class UnitCategory(Base):
    __tablename__ = "unit_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_key: Mapped[int]

    units: Mapped[list["Unit"]] = relationship(
        secondary=unit_category_assoc, back_populates="categories"
    )

    def __repr__(self) -> str:
        return f"UnitCategory(nid={self.nid!r}, name={self.name!r})"


class Unit(Base):
    __tablename__ = "units"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    level: Mapped[int]
    portrait_nid: Mapped[str]

    base_class_nid: Mapped[str] = mapped_column(
        ForeignKey("classes.nid"), nullable=True
    )
    base_class: Mapped["Class"] = relationship(back_populates="units")

    affinity_nid: Mapped[str] = mapped_column(ForeignKey("affinities.nid"))
    affinity: Mapped["Affinity"] = relationship(back_populates="units")

    bases: Mapped[dict] = mapped_column(JSON)
    growths: Mapped[dict] = mapped_column(JSON)
    stat_cap_modifiers: Mapped[dict] = mapped_column(JSON)

    quotes: Mapped[dict] = mapped_column(JSON)
    portraits: Mapped[dict] = mapped_column(JSON)

    categories: Mapped[list["UnitCategory"]] = relationship(
        secondary=unit_category_assoc, back_populates="units"
    )
    starting_items: Mapped[list["Item"]] = relationship(
        secondary=unit_item_assoc, backref="units"
    )
    learned_skills: Mapped[list["UnitSkillAssociation"]] = relationship(
        back_populates="units_with_skill"
    )

    supports: Mapped[list["Unit"]] = relationship(
        secondary=unit_support_assoc,
        primaryjoin=(nid == unit_support_assoc.c.unit_id),
        secondaryjoin=(nid == unit_support_assoc.c.support_id),
        backref="supported_by",
    )

    arsenals: Mapped[list["Arsenal"]] = relationship(back_populates="arsenal_owner")

    def __repr__(self) -> str:
        return f"Unit(nid={self.nid!r}, name={self.name!r})"


class ClassCategory(Base):
    __tablename__ = "class_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_key: Mapped[int]

    classes: Mapped[list["Class"]] = relationship(
        secondary=class_category_assoc, back_populates="categories"
    )

    def __repr__(self) -> str:
        return f"ClassCategory(nid={self.nid!r}, name={self.name!r})"


class Class(Base):
    __tablename__ = "classes"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    desc: Mapped[str]
    tier: Mapped[int]
    max_level: Mapped[int]
    alt_name: Mapped[str]

    bases: Mapped[dict] = mapped_column(JSON)
    growths: Mapped[dict] = mapped_column(JSON)
    growth_bonus: Mapped[dict] = mapped_column(JSON)
    max_stats: Mapped[dict] = mapped_column(JSON)
    promotion: Mapped[dict] = mapped_column(JSON)

    map_sprite_nid: Mapped[str]

    units: Mapped[list["Unit"]] = relationship(back_populates="base_class")
    categories: Mapped[list["ClassCategory"]] = relationship(
        secondary=class_category_assoc, back_populates="classes"
    )
    learned_skills: Mapped[list["ClassSkillAssociation"]] = relationship(
        back_populates="class_with_skill"
    )

    turns_into: Mapped[list["Class"]] = relationship(
        secondary=class_turns_into_assoc,
        primaryjoin=(class_turns_into_assoc.c.base_class_nid == nid),
        secondaryjoin=(class_turns_into_assoc.c.target_class_nid == nid),
        backref="promotes_from",
    )

    weapons: Mapped[list["Weapon"]] = relationship(
        secondary=class_weapon_assoc,
        backref="classes",
    )

    def __repr__(self) -> str:
        return f"Class(nid={self.nid!r}, name={self.name!r})"
