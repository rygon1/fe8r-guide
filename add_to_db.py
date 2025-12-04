#!/usr/bin/python3
import argparse
import re
from functools import reduce
from pathlib import Path

from sqlalchemy import create_engine, func, not_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
)

from add_to_db_models import (
    Affinity,
    Arsenal,
    Base,
    Class,
    ClassCategory,
    ClassSkillAssociation,
    Item,
    ItemCategory,
    Shop,
    Skill,
    SkillCategory,
    Unit,
    UnitCategory,
    UnitSkillAssociation,
    Weapon,
)
from app.blueprints.utils import (
    DataEntry,
    get_alt_name,
    get_comp,
    load_json_data,
    log_execution_step,
    make_valid_class_name,
    pad_digits_in_string,
    process_styled_text,
)

STAT_KEYS = ["HP", "STR", "MAG", "SKL", "SPD", "LCK", "DEF", "RES", "CON", "MOV"]


def _get_tier_category(data_entry):
    """Determines the tier category of an entry."""
    exclude_substr = ("_Pair_Up",)
    if data_entry.get("nid").endswith(("_T1", "_T2", "_T3")) and all(
        (substr not in data_entry.get("nid")) for substr in exclude_substr
    ):
        if data_entry.get("nid").endswith("_T1"):
            return "feat_t1"
        if data_entry.get("nid").endswith("_T2"):
            return "feat_t2"
        if data_entry.get("nid").endswith("_T3"):
            return "feat_t3"
    return ""


def is_skill_filtered(nid):
    """Checks if a skill's nid meets the filtering criteria."""
    if not nid:
        return False
    ends_with_tier = nid.endswith(("_T1", "_T2", "_T3"))
    has_pair_up = "_Pair_Up" in nid
    return ends_with_tier and not has_pair_up


def _set_skill_categories(session, data_entry):
    """Determines and retrieves skill categories for a data entry."""
    active_components = {
        "ability",
        "combat_art",
        "build_charge",
        "Endstep_charge_increase",
        "upkeep_charge_increase",
    }
    active_desc_keywords = ["<red>CA:</>", "CD:"]

    support_components = {
        "canter",
        "canto_plus",
        "canto_sharp",
        "aura",
        "aura_range",
        "aura_target",
        "give_status_after_combat_on_hit",
        "negative",
    }
    support_desc_keywords = [
        "ally",
        "enemy within",
        "allies within",
        "enemies within",
        "can move after",
    ]

    if not is_skill_filtered(data_entry.get("nid")):
        return []

    components = data_entry.get("components", [])
    desc = data_entry.get("desc", "")
    categories = []
    if tier_category := session.get(SkillCategory, _get_tier_category(data_entry)):
        categories.append(tier_category)

    component_names = {
        comp[0] for comp in components if isinstance(comp, list) and len(comp) > 0
    }

    is_active_by_component = any(comp in component_names for comp in active_components)
    is_active_by_desc = any(keyword in desc for keyword in active_desc_keywords)
    if is_active_by_component or is_active_by_desc:
        categories.append(session.get(SkillCategory, "active"))

    is_support_by_component = any(
        comp in component_names for comp in support_components
    )
    is_support_by_desc = any(keyword in desc for keyword in support_desc_keywords)
    if is_support_by_component or is_support_by_desc:
        categories.append(session.get(SkillCategory, "support"))

    if not (is_active_by_component or is_active_by_desc):
        if "Passive" not in categories:
            categories.append(session.get(SkillCategory, "passive"))

    return categories


@log_execution_step
def _add_skill_categories(session: Session):
    """Adds initial skill categories to the session."""
    new_skill_categories = [
        ("feat_t1", "Tier 1", "Tier"),
        ("feat_t2", "Tier 2", "Tier"),
        ("feat_t3", "Tier 3", "Tier"),
        ("active", "Active", "Type"),
        ("passive", "Passive", "Type"),
        ("support", "Support", "Type"),
    ]

    session.add_all(
        [
            SkillCategory(nid=x[0], name=x[1], type=x[2], order_key=idx)
            for idx, x in enumerate(new_skill_categories)
        ]
    )


def remove_lt_tags(orig_str: str):
    """Removes HTML-like tags from a string."""
    new_str = re.sub(r"<\w+[^>]*>.*?((</\w+>)|/>)", "", orig_str, flags=re.DOTALL)
    new_str = re.sub(r"\([ \t\r\n]*\)|\s*\[[ \t\r\n]*\]|\s*\{[ \t\r\n]*\}", "", new_str)
    return new_str


@log_execution_step
def _add_skills(session: Session, json_dir: Path) -> None:
    """Parses skill JSON and adds Skill objects to the database."""
    for data_entry in load_json_data(json_dir / "skills.json"):
        icon_nid = data_entry.get("icon_nid")
        icon_class = (
            f"{make_valid_class_name(data_entry.get('nid'))}-skill-icon "
            f"{make_valid_class_name(icon_nid)}-icon"
            if icon_nid
            else ""
        )
        new_skill = Skill(
            nid=data_entry.get("nid"),
            name=remove_lt_tags(data_entry.get("name")),
            desc=process_styled_text(data_entry.get("desc")),
            icon_class=icon_class.strip(),
            is_hidden=get_comp(data_entry, "hidden", bool),
            categories=_set_skill_categories(session, data_entry),
        )

        session.add(new_skill)


def _process_item_target(components: list) -> str:
    """Extracts target information from item components."""
    for comp in components:
        if isinstance(comp, list) and comp and comp[0].startswith("target"):
            return comp[0].split("_")[1].title()
    return ""


@log_execution_step
def _add_item_categories(session: Session):
    """Adds standard item categories to the session."""
    new_cats = [
        ("wtype_Accessory", "Item Type", "Accessories"),
        ("wtype_HeldItem", "Item Type", "Held Items"),
        ("wtype_Consumable", "Item Type", "Consumables"),
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
    """Determines and retrieves item categories for a data entry."""
    categories = []
    wstypes = (
        "Dagger",
        "Blade",
        "Warhammer",
        "Greatlance",
    )
    arsenal_marks = {
        "_Arsenal",
        "bending",
        "_Studies",
        "_Stash",
        "Shiro_Grimoire",
        "Davius_Arsenal_Old",
    }

    if wtype_cat := session.get(
        ItemCategory, f"wtype_{get_comp(data_entry, 'weapon_type', str)}"
    ):
        categories.append(wtype_cat)
    elif get_comp(data_entry, "equippable_accessory", bool):
        categories.append(session.get(ItemCategory, "wtype_Accessory"))
    elif get_comp(data_entry, "status_on_hold", str) or get_comp(
        data_entry, "multi_status_on_hold", list
    ):
        categories.append(session.get(ItemCategory, "wtype_HeldItem"))
    elif (
        get_comp(data_entry, "uses", int)
        or get_comp(data_entry, "c_uses", int)
        or get_comp(data_entry, "usable", bool)
    ):
        categories.append(session.get(ItemCategory, "wtype_Consumable"))
    elif get_comp(data_entry, "multi_item", list) and not any(
        data_entry.get("nid", "").endswith(mark) for mark in arsenal_marks
    ):
        categories.append(session.get(ItemCategory, "wtype_Consumable"))

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
    """Extracts associated status NIDs from item data."""
    exclude: tuple[str, ...] = (
        "_hide",
        "_Penalty",
        "_Gain",
        "_Proc",
        "_Weapon",
        "_AOE_Splash",
        "_Boss",
        "Avo_Ddg_",
    )
    excluded_substrings: tuple[str, ...] = exclude
    wp_status: set[str] = set()

    single_status_comps: tuple[str, ...] = ("status_on_equip", "status_on_hit")
    multi_status_comps: tuple[str, ...] = ("multi_status_on_equip", "statuses_on_hit")

    for comp_name in single_status_comps:
        status: str = get_comp(data_entry, comp_name, str)
        if status and not any(sub in status for sub in excluded_substrings):
            wp_status.add(status)

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
    """Parses item JSON, creates Item objects, and links associated Skills."""
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
    arsenal_marks = {"_Arsenal", "bending", "_Studies", "_Stash", "Shiro_Grimoire"}

    for data_entry in load_json_data(json_dir / "items.json"):
        icon_nid = data_entry.get("icon_nid")
        icon_class = (
            f"{make_valid_class_name(data_entry.get('nid'))}-item-icon "
            f"{make_valid_class_name(icon_nid)}-icon"
            if icon_nid
            else ""
        )
        if not (weapon_type := get_comp(data_entry, "weapon_type", str)):
            if get_comp(data_entry, "equippable_accessory", bool):
                weapon_type = "Accessory"
            elif get_comp(data_entry, "status_on_hold", str) or get_comp(
                data_entry, "multi_status_on_hold", list
            ):
                weapon_type = "Held Item"
            elif (
                get_comp(data_entry, "uses", int)
                or get_comp(data_entry, "c_uses", int)
                or get_comp(data_entry, "usable", bool)
            ):
                weapon_type = "Consumable"
            elif get_comp(data_entry, "multi_item", list) and not any(
                data_entry.get("nid", "").endswith(mark) for mark in arsenal_marks
            ):
                weapon_type = "Consumable"
            else:
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
            nid=data_entry.get("nid"),
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
        exclude_skill_desc = (
            "give buff to",
            "gives buff to",
            "gives the proper change to",
            "give the proper change to",
            "for the",
        )
        or_conditions = []
        for prefix in exclude_skill_desc:
            or_conditions.append(func.lower(Skill.desc).startswith(prefix))
        prefix_exclusion_clause = or_(*or_conditions)

        if skill_nids := get_status(data_entry):
            session.flush()
            all_skills = session.scalars(
                select(Skill).where(
                    Skill.nid.in_(skill_nids),
                    not_(prefix_exclusion_clause),
                    Skill.desc != "",
                )
            ).all()

            unique_skills_by_name = {}
            for skill in all_skills:
                if skill.name not in unique_skills_by_name or len(skill.desc) > len(
                    unique_skills_by_name[skill.name].desc
                ):
                    unique_skills_by_name[skill.name] = skill

            skills_to_add = list(unique_skills_by_name.values())

            try:
                new_item.status_on_equip.extend(skills_to_add)
            except IntegrityError:
                pass

    session.flush()


@log_execution_step
def _add_sub_items(session: Session, json_dir: Path) -> None:
    """Links sub-items to their super-items based on JSON data."""
    item_data = load_json_data(json_dir / "items.json")

    for data_entry in item_data:
        if sub_items_nids := get_comp(data_entry, "multi_item", list):
            if super_item := session.get(Item, data_entry.get("nid")):
                sub_items = session.scalars(
                    select(Item).where(Item.nid.in_(sub_items_nids))
                ).all()
                super_item.sub_items.extend(sub_items)

    session.flush()


def _update_item_categories(session: Session) -> None:
    consumable_cat = session.get(ItemCategory, "wtype_Consumable")

    if not consumable_cat:
        print("Error: Consumable category not found.")
        return

    items_that_are_sub = session.scalars(
        select(Item).where(Item.super_items.any())
    ).all()

    for item in items_that_are_sub:
        if consumable_cat in item.categories:
            item.categories.remove(consumable_cat)

    session.flush()


def _process_shop_name(nids: list[str]) -> tuple[str, str]:
    """Generates a human-readable shop name and type from NIDs."""
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
    """Parses event JSON to create Shop objects and link items."""
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
    """Adds the unique Dragon's Gate shop and its items."""
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


@log_execution_step
def _add_arsenals(session: Session, json_dir: Path) -> None:
    """Creates Arsenal objects and links specific items to owners."""
    excluded_units = {"_Plushie", "Orson", "Orson_Evil", "Davius_Old", "MyUnit"}
    arsenal_marks = {"_Arsenal", "bending", "_Studies", "_Stash", "Shiro_Grimoire"}
    arsenal_exclude = {"Davius_Arsenal_Old"}

    items_list = load_json_data(json_dir / "items.json")
    items_cat = load_json_data(json_dir / "items.category.json")
    item_end_exclude = ("_Old", "_Multi", "_Warp_2", "_Warp")

    special_item_arsenal_map = {
        "Lunar_Brace": "Eirikas_Arsenal",
        "Solar_Brace": "Ephraims_Arsenal",
        "Dragonstone": "Myrrh_Arsenal",
    }

    for data_entry in items_list:
        nid = data_entry.get("nid")
        icon_nid = data_entry["icon_nid"]
        icon_class = (
            f"{make_valid_class_name(data_entry.get('nid'))}-item-icon "
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
                    nid=data_entry.get("nid"),
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

    current_arsenal = None
    current_item = None
    for item_nid, item_cat in items_cat.items():
        if not (current_item := session.get(Item, item_nid)):
            continue

        if item_nid in ("Dragonstone", "Solar_Brace", "Lunar_Brace"):
            if current_arsenal := session.get(
                Arsenal, special_item_arsenal_map[item_nid]
            ):
                current_arsenal.items.append(current_item)
                session.flush()
                continue

        if not item_cat.startswith("Personal Weapons"):
            continue

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

        if prf_unit == "L'arachel":
            prf_unit = "Larachel"
        elif prf_unit == "Pro":
            prf_unit = "ProTagonist"

        stmt = select(Arsenal).filter(Arsenal.arsenal_owner_nid == prf_unit)
        if len(possible_arsenals := session.scalars(stmt).all()) == 1:
            current_arsenal = possible_arsenals[0]
            if current_item.nid == current_arsenal.nid:
                continue
            if current_item.super_items and not any(
                current_item.super_items[0].nid.endswith(mark) for mark in arsenal_marks
            ):
                continue
            current_arsenal.items.append(current_item)
            session.flush()
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


@log_execution_step
def _add_unit_categories(session: Session):
    new_cats = [
        ("Vanilla", "Vanilla", "Category"),
        ("Dragon Gate", "Dragon's Gate", "Category"),
        ("Monsters", "Monsters", "Category"),
        # "NPCs",
        # "Enemies",
    ]

    session.add_all(
        [
            UnitCategory(nid=x[0], name=x[1], type=x[2], order_key=idx)
            for idx, x in enumerate(new_cats)
        ]
    )
    session.flush()


def _set_unit_categories(
    session: Session, data_entry: DataEntry, init_category_map: dict
) -> list:
    """Determines and retrieves item categories for a data entry."""
    categories = []

    if init_category := session.get(
        UnitCategory, init_category_map.get(data_entry.get("nid"), "")
    ):
        categories.append(init_category)

    return categories


@log_execution_step
def _add_class_categories(session: Session):
    """Adds standard item categories to the session."""
    new_cats = [
        ("class_tier_t0", "Trainee/Untiered", "Tier"),
        ("class_tier_t1", "Tier 1", "Tier"),
        ("class_tier_t2", "Tier 2", "Tier"),
        ("class_tier_t3", "Tier 3", "Tier"),
        ("class_cat_infantry", "Infantry", "Category"),
        # ("class_cat_autopromote", "AutoPromote", "Category"),
        # ("class_cat_convoy", "Convoy", "Category"),
        # ("class_cat_adjconvoy", "AdjConvoy", "Category"),
        ("class_cat_horse", "Horse", "Category"),
        ("class_cat_mounted", "Mounted", "Category"),
        ("class_cat_support", "Support", "Category"),
        ("class_cat_magic", "Magic", "Category"),
        # ("class_cat_sword", "Sword", "Category"),
        ("class_cat_armor", "Armor", "Category"),
        ("class_cat_monster", "Monster", "Category"),
        ("class_cat_flying", "Flying", "Category"),
        ("class_cat_dragon", "Dragon", "Category"),
        # ("class_cat_staff", "Staff", "Category"),
        ("prof_Sword", "Sword Users", "Weapon Prof."),
        ("prof_Axe", "Axe Users", "Weapon Prof."),
        ("prof_Lance", "Lance Users", "Weapon Prof."),
        ("prof_Bow", "Bow Users", "Weapon Prof."),
        ("prof_Staff", "Staff Users", "Weapon Prof."),
        ("prof_Anima", "Anima Tome Users", "Weapon Prof."),
        ("prof_Dark", "Dark Tome Users", "Weapon Prof."),
        ("prof_Light", "Light Tome Users", "Weapon Prof."),
        ("prof_Monster", "Monster Wpn Users", "Weapon Prof."),
    ]

    session.add_all(
        [
            ClassCategory(nid=x[0], name=x[1], type=x[2], order_key=idx)
            for idx, x in enumerate(new_cats)
        ]
    )


def _set_class_categories(session: Session, data_entry: DataEntry) -> list:
    """Determines and retrieves item categories for a data entry."""
    categories = []

    if class_tier := session.get(
        ClassCategory, f"class_tier_t{data_entry.get('tier', 0)}"
    ):
        categories.append(class_tier)
    if class_tags := data_entry.get("tags"):
        for class_tag in class_tags:
            if class_cat := session.get(
                ClassCategory, f"class_cat_{class_tag.lower()}"
            ):
                categories.append(class_cat)

    weapon_nids = [x for x, y in data_entry.get("wexp_gain", {}).items() if y[0]]
    for weapon_nid in weapon_nids:
        if weapon := session.get(ClassCategory, f"prof_{weapon_nid}"):
            categories.append(weapon)

    return categories


@log_execution_step
def _add_weapons(session: Session, json_dir: Path):
    weapons = []
    weapons_data = load_json_data(json_dir / "weapons.json")
    for data_entry in weapons_data:
        icon_nid = data_entry.get("icon_nid")
        new_weapon = Weapon(
            nid=data_entry.get("nid"),
            name=data_entry.get("name", "Unknown"),
            icon_class=(
                f"{make_valid_class_name(data_entry.get('nid'))}-weapon-icon "
                f"{make_valid_class_name(icon_nid)}-icon"
                if icon_nid
                else ""
            ),
        )
        weapons.append(new_weapon)
    session.add_all(weapons)


def _set_class_weapons(session: Session, data_entry: DataEntry):
    weapons = []

    weapon_nids = [x for x, y in data_entry.get("wexp_gain", {}).items() if y[0]]

    for weapon_nid in weapon_nids:
        if weapon := session.get(Weapon, weapon_nid):
            weapons.append(weapon)

    return weapons


@log_execution_step
def _add_classes(session: Session, json_dir: Path) -> None:
    """Parses class JSON to create Class objects and associations."""
    classes_data = load_json_data(json_dir / "classes.json")
    exclude_class = (
        "Test",
        "_Plushie",
        "Wall25",
        "Dummy_T1",
        "Snag20",
        "Dummy_T2",
        "Dummy_T3",
        "Boat",
        "Dead_Body",
    )
    for data_entry in classes_data:
        if any(substr in data_entry.get("nid") for substr in exclude_class):
            continue
        new_class = Class(
            nid=data_entry.get("nid"),
            name=data_entry.get("name", "Unknown"),
            desc=process_styled_text(data_entry.get("desc", "")),
            tier=data_entry.get("tier", 0),
            max_level=data_entry.get("max_level", 10),
            bases={
                stat_key: data_entry.get("bases", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            growths={
                stat_key: data_entry.get("growths", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            growth_bonus={
                stat_key: data_entry.get("growth_bonus", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            max_stats={
                stat_key: data_entry.get("max_stats", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            promotion={
                stat_key: data_entry.get("promotion", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            weapons=_set_class_weapons(session, data_entry),
            categories=_set_class_categories(session, data_entry),
            map_sprite_nid=data_entry.get("map_sprite_nid", ""),
            alt_name=get_alt_name(data_entry.get("name"), data_entry.get("nid")),
        )

        session.add(new_class)
    session.flush()

    for data_entry in classes_data:
        current_class = session.get(Class, data_entry.get("nid"))
        if not current_class:
            continue

        if learned := data_entry.get("learned_skills", []):
            for skill_level, skill_nid in learned:
                if not skill_nid.endswith("_hide") and (
                    skill := session.get(Skill, skill_nid)
                ):
                    current_class.learned_skills.append(
                        ClassSkillAssociation(skill=skill, level=skill_level)
                    )

        if turns_into_nids := data_entry.get("turns_into", []):
            if turns_into_nids:
                target_classes = session.scalars(
                    select(Class).where(Class.nid.in_(turns_into_nids))
                ).all()
                current_class.turns_into.extend(target_classes)

    session.flush()


def _add_affinities(session: Session, json_dir: Path):
    """Adds all affinities from affinities.json to the database."""
    log_execution_step("Adding Affinities")
    affinities_data = load_json_data(json_dir / "affinities.json")
    for data_entry in affinities_data:
        new_bonus = []
        val = data_entry.get("bonus", [])
        for bonus_data in val:
            new_bonus.append(
                {
                    "RANK": bonus_data["support_rank"],
                    "ATK": bonus_data["damage"],
                    "DEF": bonus_data["resist"],
                    "HIT": bonus_data["accuracy"],
                    "AVOID": bonus_data["avoid"],
                    "CRIT": bonus_data["crit"],
                    "DODGE": bonus_data["dodge"],
                    "ATK SPD": bonus_data["attack_speed"],
                    "DEF SPD": bonus_data["defense_speed"],
                }
            )
        affinity = Affinity(
            nid=data_entry.get("nid"),
            name=data_entry.get("name", ""),
            desc=data_entry.get("desc", ""),
            bonus=new_bonus,
            icon_class=f"Affinity-icon Pair-up-affinity-{data_entry.get('nid').lower()}-skill-icon",
        )
        session.add(affinity)
    session.flush()


@log_execution_step
def _add_unit_supports(session: Session, json_dir: Path):
    """Adds unit support pairs from support_pairs.json to the database."""
    support_pairs = load_json_data(json_dir / "support_pairs.json")

    for pair in support_pairs:
        unit1_nid = pair["unit1"]
        unit2_nid = pair["unit2"]
        one_way = pair.get("one_way", False)

        unit1 = session.get(Unit, unit1_nid)
        unit2 = session.get(Unit, unit2_nid)

        if unit1 and unit2:
            if unit2 not in unit1.supports:
                unit1.supports.append(unit2)

            # If not one-way, unit2 also supports unit1
            if not one_way and unit1 not in unit2.supports:
                unit2.supports.append(unit1)
        else:
            print(
                f"Warning: Could not find unit(s) for support pair: {unit1_nid} and {unit2_nid}"
            )

    session.flush()


def _add_units(session: Session, json_dir: Path) -> None:
    """Parses unit JSON to create Unit objects and associations."""
    units_data = load_json_data(json_dir / "units.json")
    init_category_map = load_json_data(json_dir / "units.category.json")
    exclude_unit = ("_Plushie", "Orson", "Orson_Evil", "Davius_Old", "MyUnit")

    for data_entry in units_data:
        new_unit_nid = data_entry.get("nid")
        if init_category_map.get(new_unit_nid, "") not in (
            "Vanilla",
            "Dragon Gate",
            "Monsters",
        ) or new_unit_nid.endswith(exclude_unit):
            continue
        new_unit = Unit(
            nid=data_entry.get("nid"),
            name=data_entry.get("name", "Unknown"),
            desc=process_styled_text(data_entry.get("desc", "")),
            level=data_entry.get("level", 1),
            base_class_nid=data_entry.get("klass"),
            portrait_nid=data_entry.get("portrait_nid"),
            affinity_nid=data_entry.get("affinity", ""),
            bases={
                stat_key: data_entry.get("bases", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            growths={
                stat_key: data_entry.get("growths", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            stat_cap_modifiers={
                stat_key: data_entry.get("stat_cap_modifiers", {}).get(stat_key, 0)
                for stat_key in STAT_KEYS
            },
            categories=_set_unit_categories(session, data_entry, init_category_map),
        )

        session.add(new_unit)
        session.flush()

        if current_unit := session.get(Unit, data_entry.get("nid")):
            if start_items := data_entry.get("starting_items"):
                item_nids = [i[0] for i in start_items]
                items = session.scalars(
                    select(Item).where(Item.nid.in_(item_nids))
                ).all()
                current_unit.starting_items.extend(items)

            if learned := data_entry.get("learned_skills", []):
                for skill_level, skill_nid in learned:
                    if not skill_nid.endswith(("_hide", "Feat_Enabler")) and (
                        skill := session.get(Skill, skill_nid)
                    ):
                        current_unit.learned_skills.append(
                            UnitSkillAssociation(skill=skill, level=skill_level)
                        )

    session.flush()


def add_to_db(json_dir: Path) -> None:
    """Orchestrates the database population process."""
    db_path = Path(__file__).resolve().parent / "app/fe8r-guide.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")

    print(f"\n--- Initializing Database at {db_path} ---")
    print(f"--- Loading JSON data from {json_dir} ---\n")

    with Session(engine) as session:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        _add_skill_categories(session)
        _add_skills(session, json_dir)
        session.flush()

        _add_item_categories(session)
        _add_main_items(session, json_dir)
        session.commit()

        _add_sub_items(session, json_dir)
        session.commit()

        _update_item_categories(session)
        session.commit()

        _add_shops(session, json_dir)
        session.commit()

        _add_dragons_gate_shop(session)
        session.commit()

        _add_weapons(session, json_dir)
        session.commit()

        _add_class_categories(session)
        _add_classes(session, json_dir)
        session.commit()

        _add_affinities(session, json_dir)
        session.commit()

        _add_unit_categories(session)
        _add_units(session, json_dir)
        session.commit()

        _add_unit_supports(session, json_dir)
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
