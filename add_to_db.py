#!/usr/bin/python3
import argparse
import re
from functools import reduce
from pathlib import Path

from sqlalchemy import Column, ForeignKey, String, Table, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app.blueprints.utils import (
    DataEntry,
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


item_category_assoc = Table(
    "item_category_assoc",
    Base.metadata,
    Column("item_nid", ForeignKey("items.nid"), primary_key=True),
    Column("category_nid", ForeignKey("item_categories.nid"), primary_key=True),
)


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
        return f"Item(nid={self.nid!r}, name={self.name!r}, desc={self.desc!r})"


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
    abbr_name: Mapped[str]

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
    for data_entry in load_json_data(json_dir / "skills.json"):
        icon_nid = data_entry.get("icon_nid")
        icon_class = (
            f"{make_valid_class_name(data_entry.get('nid'))}-skill-icon "
            f"{make_valid_class_name(icon_nid)}-icon"
            if icon_nid
            else ""
        )

        new_skills.append(
            Skill(
                nid=data_entry["nid"],
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
def _add_item_categories(session: Session):

    new_cats = [
        ("wtype_Accessory", "Item Type", "Accessories"),
        ("wtype_HeldItem", "Item Type", "Held Items"),
        ("wtype_Sword", "Item Type", "Swords"),
        ("wtype_Axe", "Item Type", "Axes"),
        ("wtype_Lance", "Item Type", "Lances"),
        ("wtype_Bow", "Item Type", "Bows"),
        ("wtype_Staff", "Item Type", "Staves"),
        ("wtype_Anima", "Item Type", "Anima Tomes"),
        ("wtype_Dark", "Item Type", "Dark Tomes"),
        ("wtype_Light", "Item Type", "Light Tomes"),
        ("wstype_Dagger", "Weapon Subtype", "Daggers"),
        ("wstype_Blade", "Weapon Subtype", "Blades"),
        ("wstype_Warhammer", "Weapon Subtype", "Warhammers"),
        ("wstype_Greatlance", "Weapon Subtype", "Greatlances"),
        ("etype_Fire", "Element", "Fire"),
        ("etype_Wind", "Element", "Wind"),
        ("etype_Water", "Element", "Water"),
        ("etype_Thunder", "Element", "Thunder"),
        ("etype_Dark", "Element", "Dark"),
        ("etype_Light", "Element", "Light"),
        ("etype_Ice", "Element", "Ice"),
        ("etype_Earth", "Element", "Earth"),
    ]

    session.add_all(
        [
            ItemCategory(nid=x[0], name=x[2], type=x[1], order_key=idx)
            for idx, x in enumerate(new_cats)
        ]
    )


def _set_item_categories(session: Session, data_entry: DataEntry) -> list:
    categories = []
    wstypes = (
        "Dagger",
        "Blade",
        "Warhammer",
        "Greatlance",
    )

    if wtype_cat := session.get(
        ItemCategory, f"wtype_{get_comp(data_entry, "weapon_type", str)}"
    ):
        categories.append(wtype_cat)
    elif get_comp(data_entry, "equippable_accessory", bool):
        categories.append(session.get(ItemCategory, "wtype_Accessory"))
    elif get_comp(data_entry, "status_on_hold", str) or get_comp(
        data_entry, "multi_status_on_hold", list
    ):
        categories.append(session.get(ItemCategory, "wtype_HeldItem"))

    if item_tags := get_comp(data_entry, "item_tags", list):
        for element in [x for x in item_tags if x not in wstypes]:
            if etype_cat := session.get(ItemCategory, f"etype_{element}"):
                categories.append(etype_cat)
        for wstype in [x for x in item_tags if x in wstypes]:
            if wstype_cat := session.get(ItemCategory, f"wstype_{wstype}"):
                categories.append(wstype_cat)
    if "Quick_Knife" in get_comp(data_entry, "status_on_equip", list):
        if is_dagger := session.get(ItemCategory, "wstype_Dagger"):
            categories.append(is_dagger)

    return categories


def get_status(data_entry: DataEntry) -> list[str]:
    exclude: tuple[str, ...] = (
        "_hide",
        "_Penalty",
        "_Gain",
        "_Proc",
        "_Weapon",
        "_AOE_Splash",
        "_Boss",
        "Avo_Ddg_",
        "_Buff",
    )
    """
    Extracts unique, non-excluded status names from various component fields of an entry.

    :param data_entry: The item data entry to process.
    :type data_entry: DataEntry
    :returns: A list of unique status names associated with the item, excluding any in EXCLUDE.
    :rtype: list[str]
    """
    excluded_substrings: tuple[str, ...] = exclude
    wp_status: set[str] = set()

    single_status_comps: tuple[str, ...] = ("status_on_equip", "status_on_hit")
    multi_status_comps: tuple[str, ...] = ("multi_status_on_equip", "statuses_on_hit")

    # Process single status components
    for comp_name in single_status_comps:
        status: str = get_comp(data_entry, comp_name, str)
        if status and not any(sub in status for sub in excluded_substrings):
            wp_status.add(status)

    # Process multi-status components
    for comp_name in multi_status_comps:
        statuses: list[str] = get_comp(data_entry, comp_name, list)
        for status_entry in statuses:
            if status_entry and not any(
                sub in status_entry for sub in excluded_substrings
            ):
                wp_status.add(status_entry)

    return list(wp_status)


@log_execution_step
def _add_main_items(session: Session, json_dir: Path) -> None:
    """
    Loads item data, creates Item objects, and links them to associated Skill objects.
    """
    rank_values = {
        "": -1,
        "Prf": 0,
        "E": 1,
        "D": 2,
        "C": 3,
        "B": 4,
        "A": 5,
        "S": 6,
        "SS": 7,
        "SSS": 8,
        "X": 9,
    }

    for data_entry in load_json_data(json_dir / "items.json"):
        icon_nid = data_entry.get("icon_nid")
        icon_class = (
            f"{make_valid_class_name(data_entry.get("nid"))}-item-icon "
            f"{make_valid_class_name(icon_nid)}-icon"
            if icon_nid
            else ""
        )
        if not (weapon_type := get_comp(data_entry, "weapon_type", str)):
            weapon_type = "Misc"
        if (
            not (weapon_rank := get_comp(data_entry, "weapon_rank", str))
            and weapon_type != "Misc"
            and get_comp(data_entry, "prf_unit", list)
        ):
            weapon_rank = "Prf"
        weapon_rank_order_key = rank_values.get(weapon_rank, 10)
        categories = _set_item_categories(session, data_entry)
        new_item = Item(
            nid=data_entry["nid"],
            name=remove_lt_tags(data_entry.get("name")),
            desc=process_styled_text(data_entry.get("desc")),
            value=get_comp(data_entry, "value", int),
            weapon_rank=weapon_rank,
            weapon_rank_order_key=weapon_rank_order_key,
            weapon_type=weapon_type,
            damage=get_comp(data_entry, "damage", int),
            weight=get_comp(data_entry, "weight", int),
            crit=get_comp(data_entry, "crit", int),
            hit=get_comp(data_entry, "hit", int),
            min_range=get_comp(data_entry, "min_range", int),
            max_range=get_comp(data_entry, "max_range", int),
            target=_process_item_target(data_entry.get("components")),
            icon_class=icon_class.strip(),
            categories=categories,
        )
        session.add(new_item)
        # Change to this when items.json is updated to have mult_desc
        """ if skill_nids := get_comp(data_entry, "multi_desc_skill", list):
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
                ) """
        if skill_nids := get_status(data_entry):
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
    abbr_name_map = {
        "9A_Armory_10B_Armory_Global_BethroenArmory_Global_PortKirisArmory": "Bethroen / Port Kiris",
        "9A_Vendor_10B_Vendor_Global_BethroenVendor_Global_PortKirisVendor": "Bethroen / Port Kiris",
        "12A_Vendor_12B_Vendor_Global_CaerPelynVendor_Global_TaizelVendor": "Caer Pelyn / Taizel",
        "14A_SecretShop_Global_JehannaHallSecretShop": "Jehanna Hall",
        "14B_SecretShop_Global_GradoKeepSecretShop": "Grado Keep",
        "15A_Vendor_15B_Vendor_Global_JehannaHallVendor": "Jehanna Hall",
        "17A_Armory_17B_Armory_Global_NarubeRiverArmory": "Narube River",
        "17A_Vendor_17B_Vendor_Global_NarubeRiverVendor": "Narube River",
        "2_Armory_Global_IdeArmory": "Ide",
        "5_Armory_Global_SerafewArmory": "Serafew",
        "5_Vendor_Global_SerafewVendor": "Serafew",
        "Global_RaustenCourtArmory": "Rausten Court",
        "Global_RaustenCourtSecretShop": "Rausten Court",
        "Global_RaustenCourtVendor": "Rausten Court",
        "Dragon_Gate_Vendor": "Dragon's Gate",
    }

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
            abbr_name=abbr_name_map[shop_nid],
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
        abbr_name="Dragon's Gate",
    )
    session.add(new_shop)

    stmt = select(Item).where(Item.nid.endswith("_DG"))
    result_items = session.execute(stmt).scalars().all()

    session.flush()

    if result_items:
        new_shop.items.extend(result_items)


arsenal_item_assoc = Table(
    "arsenal_item_assoc",
    Base.metadata,
    Column("arsenal_nid", String, ForeignKey("arsenals.nid"), primary_key=True),
    Column("item_nid", String, ForeignKey("items.nid"), primary_key=True),
)


class Arsenal(Base):
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


@log_execution_step
def _add_arsenals(session: Session, json_dir: Path) -> None:

    excluded_units = {"_Plushie", "Orson", "Orson_Evil", "Davius_Old", "MyUnit"}
    arsenal_marks = {"_Arsenal", "bending", "_Studies", "_Stash", "Shiro_Grimoire"}
    arsenal_exclude = {"Davius_Arsenal_Old"}

    items_list = load_json_data(json_dir / "items.json")
    # all_items_map = {x["nid"]: x for x in items_list}  # Quick lookup

    items_cat = load_json_data(json_dir / "items.category.json")
    item_end_exclude = ("_Old", "_Multi", "_Warp_2", "_Warp")

    special_item_arsenal_map = {
        "Lunar_Brace": "Eirikas_Arsenal",
        "Solar_Brace": "Ephraims_Arsenal",
        "Dragonstone": "Myrrh_Arsenal",
    }
    # Add arsenals
    for data_entry in items_list:
        nid = data_entry["nid"]
        icon_nid = data_entry["icon_nid"]
        icon_class = (
            f"{make_valid_class_name(data_entry.get("nid"))}-item-icon "
            f"{make_valid_class_name(icon_nid)}-icon"
            if icon_nid
            else ""
        )
        if nid in arsenal_exclude:
            continue

        if any(nid.endswith(mark) for mark in arsenal_marks):
            prf_unit = get_comp(data_entry, "prf_unit", list)
            if prf_unit and prf_unit[0] not in excluded_units:
                new_arsenal = Arsenal(
                    nid=data_entry["nid"],
                    name=data_entry["name"],
                    desc=process_styled_text(data_entry.get("desc", "")),
                    arsenal_owner_nid=prf_unit[0],
                    icon_class=icon_class.strip(),
                )
                session.add(new_arsenal)
                session.flush()
    new_arsenal = Arsenal(
        nid="Myrrh_Arsenal",
        name="Myrrh's Arsenal",
        desc=process_styled_text(
            "Arsenal of a Manakete.\n<red>Prof:</><icon>Monster</>"
        ),
        arsenal_owner_nid="Myrrh",
        icon_class="Dragonstone-item-icon Neutral-icon",
    )
    session.add(new_arsenal)
    session.flush()

    # Append items to corresponding
    current_arsenal = None
    current_item = None
    for item_nid, item_cat in items_cat.items():
        if not (current_item := session.get(Item, item_nid)):
            continue
        # Special Items
        if item_nid in ("Dragonstone", "Solar_Brace", "Lunar_Brace"):
            if current_arsenal := session.get(
                Arsenal, special_item_arsenal_map[item_nid]
            ):
                current_arsenal.items.append(current_item)
                session.flush()
                continue

        # Standard Logic
        if not item_cat.startswith("Personal Weapons"):
            continue

        # if item_nid in arsenal_nid_list or item_nid.endswith(item_end_exclude):
        if item_nid.endswith(item_end_exclude):
            continue

        if not current_item.desc:
            continue

        prf_unit = item_cat.split("/")[1]
        if prf_unit == "Davius Old":
            continue
        if prf_unit == "Lindsey" and item_nid.endswith("_D"):
            continue
        if prf_unit == "Azuth" and item_nid.endswith("_A"):
            continue

        # Name normalization
        if prf_unit == "L'arachel":
            prf_unit = "Larachel"
        elif prf_unit == "Pro":
            prf_unit = "ProTagonist"

        # Determine specific arsenal nid
        stmt = select(Arsenal).filter(Arsenal.arsenal_owner_nid == prf_unit)
        # Units with 1 arsenal
        if len(possible_arsenals := session.scalars(stmt).all()) == 1:
            current_arsenal = possible_arsenals[0]
            if current_item.nid == current_arsenal.nid:
                continue

            current_arsenal.items.append(current_item)
            session.flush()
        # Units with multiple arsenals
        elif len(possible_arsenals) > 1:
            if prf_unit == "ProTagonist":
                if item_nid in (
                    "Airbending",
                    "Earthbending",
                    "Firebending",
                    "Waterbending",
                ):
                    continue
                if item_nid.startswith("Air"):
                    current_arsenal = session.get(Arsenal, "Airbending")
                elif item_nid.startswith("Earth"):
                    current_arsenal = session.get(Arsenal, "Earthbending")
                elif item_nid.startswith("Fire"):
                    current_arsenal = session.get(Arsenal, "Firebending")
                elif item_nid.startswith("Water"):
                    current_arsenal = session.get(Arsenal, "Waterbending")
                else:
                    continue
                if current_arsenal:
                    current_arsenal.items.append(current_item)
            elif prf_unit == "Tana":
                if item_nid in ("Tanas_Stash", "Tanas_Arsenal"):
                    continue
                if "_Buff" in item_nid or "_Heal" in item_nid:
                    current_arsenal = session.get(Arsenal, "Tanas_Stash")
                else:
                    current_arsenal = session.get(Arsenal, "Tanas_Arsenal")
                if current_arsenal:
                    current_arsenal.items.append(current_item)

    session.flush()


def add_to_db(json_dir: Path) -> None:
    """
    Loads game data from JSON files into the SQLite database.

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

        _add_item_categories(session)
        _add_main_items(session, json_dir)
        session.commit()

        _add_sub_items(session, json_dir)
        session.commit()

        _add_shops(session, json_dir)
        session.commit()

        _add_dragons_gate_shop(session)
        session.commit()

        _add_arsenals(session, json_dir)
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
