#!/usr/bin/python3
import argparse
import re
from functools import reduce
from pathlib import Path

from sqlalchemy import Column, ForeignKey, String, Table, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app.blueprints.utils import (
    get_comp,
    load_json_data,
    log_execution_step,
    make_valid_class_name,
    pad_digits_in_string,
    process_styled_text,
)


class Base(DeclarativeBase):
    pass


class Skill(Base):
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


class SkillCategory(Base):
    __tablename__ = "skill_categories"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    def __repr__(self) -> str:
        return f"SkillCategory(nid={self.nid!r}, name={self.name!r})"


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


class Item(Base):
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
        backref="super_items",
    )
    status_on_equip = relationship(
        "Skill",
        secondary=item_skill_assoc,
        backref="items",
    )

    def __repr__(self) -> str:
        return f"Item(nid={self.nid!r}, name={self.name!r}, desc={self.desc!r})"


shop_item_assoc = Table(
    "shop_item_assoc",
    Base.metadata,
    Column("shop_nid", String, ForeignKey("shops.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)


class Shop(Base):
    __tablename__ = "shops"
    nid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    order_name: Mapped[str]

    items = relationship(
        "Item",
        secondary=shop_item_assoc,
        backref="shops",
        uselist=True,
    )

    def __repr__(self) -> str:
        return f"Shop(nid={self.nid!r}, name={self.name!r}, type={self.type!r})"


@log_execution_step
def _get_skill_categories(session: Session, json_dir: Path) -> dict[str, str]:
    """
    Processes skill categories, creates SkillCategory objects, adds them to the
    session, and returns a mapping dictionary.
    """
    skill_cats = {}
    new_skill_categories = []

    category_map = load_json_data(json_dir / "skills.category.json")

    for skill_nid, category_nid in category_map.items():
        skill_cats[skill_nid] = category_nid

        if category_nid not in (x.nid for x in new_skill_categories):
            if category_nid.startswith("MyUnit/T"):
                tier = category_nid.split("/T")[1]
                name = f"Feats (Tier {tier})"
            else:
                name = category_nid

            new_skill_categories.append(SkillCategory(nid=category_nid, name=name))

    session.add_all(new_skill_categories)
    return skill_cats


def remove_lt_tags(orig_str: str):
    new_str = re.sub(r"<\w+[^>]*>.*?((</\w+>)|/>)", "", orig_str, flags=re.DOTALL)
    new_str = re.sub(r"\([ \t\r\n]*\)|\s*\[[ \t\r\n]*\]|\s*\{[ \t\r\n]*\}", "", new_str)
    return new_str


@log_execution_step
def _add_skills(session: Session, skill_cats: dict[str, str], json_dir: Path) -> None:
    """
    Loads skill data from JSON files, creates Skill objects, and adds them to the session.
    """
    new_skills = []
    # for skill_json in (json_dir / "skills").glob("*.json"):
    for skill_json in [json_dir / "skills.json"]:
        for data_entry in load_json_data(skill_json):
            icon_nid = data_entry.get("icon_nid")
            icon_class = (
                f"{make_valid_class_name(data_entry.get('nid'))}-skill-icon "
                f"{make_valid_class_name(icon_nid)}-icon"
                if icon_nid
                else ""
            )

            new_skills.append(
                Skill(
                    nid=data_entry.get("nid"),
                    # name=process_styled_text(data_entry("name")), # TODO change to this when everything is migrated
                    name=remove_lt_tags(data_entry.get("name")),
                    desc=process_styled_text(data_entry.get("desc")),
                    icon_class=icon_class.strip(),
                    is_hidden=get_comp(data_entry, "hidden", bool),
                    category_nid=skill_cats.get(data_entry.get("nid"), "Misc"),
                )
            )
    session.add_all(new_skills)


def _process_item_target(components: list) -> str:
    """Extracts the item target string from the components list."""
    for comp in components:
        if isinstance(comp, list) and comp and comp[0].startswith("target"):
            return comp[0].split("_")[1].title()
    return ""


@log_execution_step
def _add_main_items(session: Session, json_dir: Path) -> None:
    """
    Loads item data, creates Item objects, and links them to associated Skill objects.
    """
    # for item_json in (json_dir / "items").glob("*.json"):
    for item_json in [json_dir / "items.json"]:
        for data_entry in load_json_data(item_json):
            icon_nid = data_entry.get("icon_nid")
            icon_class = (
                f"{make_valid_class_name(data_entry.get("nid"))}-item-icon "
                f"{make_valid_class_name(icon_nid)}-icon"
                if icon_nid
                else ""
            )

            new_item = Item(
                nid=data_entry.get("nid"),
                name=process_styled_text(data_entry.get("name")),
                desc=process_styled_text(data_entry.get("desc")),
                value=get_comp(data_entry, "value", int),
                weapon_rank=get_comp(data_entry, "weapon_rank", str),
                weapon_type=get_comp(data_entry, "weapon_type", str),
                damage=get_comp(data_entry, "damage", int),
                weight=get_comp(data_entry, "weight", int),
                crit=get_comp(data_entry, "crit", int),
                hit=get_comp(data_entry, "hit", int),
                min_range=get_comp(data_entry, "min_range", int),
                max_range=get_comp(data_entry, "max_range", int),
                target=_process_item_target(data_entry.get("components")),
                icon_class=icon_class.strip(),
            )
            session.add(new_item)

            if skill_nids := get_comp(data_entry, "multi_desc_skill", list):
                session.flush()
                all_skills = session.scalars(
                    select(Skill).where(Skill.nid.in_(skill_nids))
                ).all()

                unique_skills_by_name = {}
                for skill in all_skills:
                    if skill.name not in unique_skills_by_name or len(skill.desc) > len(
                        unique_skills_by_name[skill.name].desc
                    ):
                        unique_skills_by_name[skill.name] = skill

                # 3. Get the list of selected skills (the values from the dictionary)
                skills_to_add = list(unique_skills_by_name.values())

                try:
                    new_item.status_on_equip.extend(skills_to_add)
                except IntegrityError:
                    print(
                        "Skipping existing entry or handling M2M relationship IntegrityError."
                    )

    session.flush()


@log_execution_step
def _add_sub_items(session: Session, json_dir: Path) -> None:
    item_data = load_json_data(json_dir / "items.json")

    for data_entry in item_data:
        if sub_items_nids := get_comp(data_entry, "multi_item", list):
            if super_item := session.get(Item, data_entry.get("nid")):
                sub_items = session.scalars(
                    select(Item).where(Item.nid.in_(sub_items_nids))
                ).all()
                super_item.sub_items.extend(sub_items)

    session.flush()


def _process_shop_name(nids: list[str]) -> tuple[str, str]:
    """Cleans up, formats, and determines the final shop name and type."""
    substrings_to_remove = ["Armory", "SecretShop", "Vendor"]

    cleaned_nids = [
        reduce(lambda text, sub: text.replace(sub, ""), substrings_to_remove, s)
        for s in nids
    ]

    if "SecretShop" in nids[0]:
        shop_type = "Secret Shop"
    elif "Armory" in nids[0]:
        shop_type = "Armory"
    else:
        shop_type = "Vendor"

    shop_name_parts = (
        (
            f"Chapter {x}"
            if x and x[0].isdigit()
            else " ".join(re.split(r"(?=[A-Z])", x))
        )
        for x in cleaned_nids
    )

    shop_name = " / ".join(shop_name_parts)
    shop_name = shop_name.replace(shop_type, "").replace("Global", "")
    shop_name += " " + shop_type
    shop_name = " ".join(shop_name.split()).strip()

    return shop_name, shop_type


@log_execution_step
def _add_shops(session: Session, json_dir: Path) -> None:
    """
    Loads event data, groups events, creates Shop objects, and links items.
    """
    events_data = load_json_data(json_dir / "events.json")
    sorted_events = sorted(events_data, key=lambda x: x.get("nid"))

    shops_map = {}

    for data_entry in sorted_events:
        if data_entry.get("nid").endswith(
            ("Vendor", "SecretShop", "Armory")
        ) and "Dragons_Gate" not in data_entry.get("nid"):
            shop_items_source = [
                x.split(";")[2].split(",")
                for x in data_entry.get("_source", [])
                if x.startswith("shop;")
            ]

            if not shop_items_source:
                continue

            shop_items_key = tuple(sorted(shop_items_source[0]))

            if shop_items_key not in shops_map:
                shops_map[shop_items_key] = []
            shops_map[shop_items_key].append(data_entry)

    for shop_items_tuple, shops_group in shops_map.items():
        nid_strings = [x.get("nid") for x in shops_group]

        orig_shop_nids = sorted(nid_strings, key=lambda x: pad_digits_in_string(x, 2))

        shop_nid = "_".join(orig_shop_nids).replace(" ", "_")
        shop_name, shop_type = _process_shop_name(orig_shop_nids)

        new_shop = Shop(
            nid=shop_nid,
            name=shop_name,
            type=shop_type,
            order_name=pad_digits_in_string(shop_nid, 2),
        )
        session.add(new_shop)

        session.flush()
        items_to_add = session.scalars(
            select(Item).where(Item.nid.in_(shop_items_tuple))
        ).all()

        if items_to_add:
            new_shop.items.extend(items_to_add)

    session.flush()


@log_execution_step
def _add_dragons_gate_shop(session: Session) -> None:
    """
    Adds the specific "Dragon's Gate" shop and links all items with an '_DG' suffix.
    """
    dragon_gate_nid = "Dragon_Gate_Vendor"
    new_shop = Shop(
        nid=dragon_gate_nid,
        name="Dragon's Gate (Anna)",
        type="Vendor",
        order_name="Z_Dragon_Gate",
    )
    session.add(new_shop)

    stmt = select(Item).where(Item.nid.endswith("_DG"))
    result_items = session.execute(stmt).scalars().all()

    session.flush()

    if result_items:
        new_shop.items.extend(result_items)


def add_to_db(json_dir: Path) -> None:
    """
    Orchestrates the extraction, transformation, and loading (ETL) of game data
    from JSON files into the SQLite database.

    This function performs the following operations:
    1.  Initializes the SQLite database connection and resets the schema (drop/create).
    2.  Loads and processes Skill Categories and Skills, establishing relationships.
    3.  Loads Items and links them to their intrinsic Skills (e.g., status effects).
    4.  Establishes recursive sub-item relationships (e.g., promotional items).
    5.  Processes and groups Shop events to create Shop entities with inventories.
    6.  Creates the special "Dragon's Gate" shop with designated items.

    Parameters:
        json_dir (Path): The directory path containing the source JSON files.

    Returns:
        None: The function commits changes directly to the database.
    """
    db_path = Path(__file__).resolve().parent / "app/fe8r-guide.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")

    print(f"--- Initializing Database at {db_path} ---")
    print(f"--- Loading JSON data from {json_dir} ---")

    with Session(engine) as session:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        skill_cats = _get_skill_categories(session, json_dir)
        _add_skills(session, skill_cats, json_dir)
        session.flush()

        _add_main_items(session, json_dir)
        session.commit()

        _add_sub_items(session, json_dir)
        session.commit()

        _add_shops(session, json_dir)
        session.commit()

        _add_dragons_gate_shop(session)
        session.commit()

    print("--- Database Population Complete ---")


def main():
    parser = argparse.ArgumentParser(description="Populate database from JSON files.")
    parser.add_argument(
        "json_dir", type=Path, help="Path to the directory containing JSON files"
    )
    args = parser.parse_args()

    if not args.json_dir.exists():
        print(f"Error: Directory '{args.json_dir}' does not exist.")
        return

    add_to_db(args.json_dir)


if __name__ == "__main__":
    main()
