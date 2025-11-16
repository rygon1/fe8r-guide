#!/usr/bin/python3
import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

from PIL import Image
from sqlalchemy import Column, ForeignKey, String, Table, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app.blueprints.utils import (
    get_comp,
    make_valid_class_name,
    pad_digits_in_string,
    process_styled_text,
)

LTPROJ_DIR = Path("")
try:
    with Path("ltprojpath.txt").open("r", encoding="utf-8") as f:
        LTPROJ_DIR = Path(f.read())
except FileNotFoundError:
    print("Error: The file 'ltprojpath.txt' was not found.")


if not LTPROJ_DIR.exists():
    raise FileNotFoundError(f"The directory {LTPROJ_DIR} does not exist.")

JSON_DIR: Path = LTPROJ_DIR / "game_data"
ICONS_16_DIR = LTPROJ_DIR / "resources/icons16"
PORTRAITS_DIR: Path = LTPROJ_DIR / "resources/portraits"
MAP_SPRITES_DIR: Path = LTPROJ_DIR / "resources/map_sprites"
GUIDE_JSON_DIR: Path = Path.cwd() / "app/static/json"
GUIDE_IMG_DIR: Path = Path.cwd() / "app/static/images"
GUIDE_CSS_DIR: Path = Path.cwd() / "app/static/css"


def minify_json() -> None:
    """
    Removes JSON whitespace to save some bandwidth. Not necessary if running locally.
    """
    print("Minifying JSON files ...")
    for json_fpath in GUIDE_JSON_DIR.iterdir():
        if json_fpath.suffix == ".json":
            with json_fpath.open("r") as fp:
                x = json.load(fp)
            with json_fpath.open("w") as fp:
                json.dump(x, fp, separators=(",", ":"))
    print("Done.")


def make_arsenal_json() -> None:
    print("Creating arsenals.json ...")
    arsenals: dict = {}
    # Add units
    with (JSON_DIR / "units.category.json").open("r") as fp:
        for unit_nid, unit_cat in json.load(fp).items():
            if unit_cat in ("Vanilla", "Monsters", "Dragon Gate") and unit_nid not in (
                "_Plushie",
                "Orson",
                "Orson_Evil",
                "Davius_Old",
                "MyUnit",
            ):
                arsenals[unit_nid] = {}
    # Add arsenal details
    with (JSON_DIR / "items.json").open("r") as fp:
        arsenal_marks = ("_Arsenal", "bending", "_Studies", "_Stash", "_Grimoire")
        arsenal_exclude = ("Davius_Arsenal_Old",)
        for item_data in json.load(fp):
            if (
                any(item_data["nid"].endswith(x) for x in arsenal_marks)
                and item_data["nid"] not in arsenal_exclude
            ):
                if prf_list := get_comp(item_data, "prf_unit", list):
                    if prf_list[0] in arsenals:
                        arsenals[prf_list[0]][item_data["nid"]] = {
                            "name": item_data["name"],
                            "desc": process_styled_text(item_data["desc"]),
                            "items": {},
                        }
        # Add an arsenal for Myrrh
        arsenals["Myrrh"] = {
            "Myrrh_Arsenal": {
                "name": "Myrrh's Arsenal",
                "desc": process_styled_text(
                    "Arsenal of a Manakete.\n<red>Prof:</><icon>Monster</>"
                ),
                "items": {},
            }
        }
    # Make arsenal item list
    arsenal_nid_list = []
    for _, arsenal_unit_dict in arsenals.items():
        for arsenal_name in arsenal_unit_dict.keys():
            arsenal_nid_list.append(arsenal_name)
    # Get all item data
    with (JSON_DIR / "items.json").open("r") as fp:
        all_items: dict[Any, Any] = {x["nid"]: x for x in json.load(fp)}
    # Add items to arsenals
    item_end_exclude = ("_Old", "_Multi", "_Warp_2", "_Warp")
    with (JSON_DIR / "items.category.json").open("r") as fp:
        for item_nid, items_cat in json.load(fp).items():
            arsenal_data: dict[Any, Any] = {}
            if (
                items_cat.startswith("Personal Weapons")
                and item_nid not in arsenal_nid_list
                and not item_nid.endswith(item_end_exclude)
                and all_items[item_nid]["desc"]
                and (arsenal_unit := items_cat.split("/")[1]) not in ("Davius Old",)
            ):
                if arsenal_unit == "L'arachel":
                    arsenal_unit = "Larachel"
                elif arsenal_unit == "Pro":
                    arsenal_unit = "ProTagonist"
                match (arsenal_unit):
                    case "ProTagonist":
                        if item_nid not in arsenals[arsenal_unit]:
                            if item_nid.startswith("Air"):
                                arsenal_nid = "Airbending"
                            elif item_nid.startswith("Earth"):
                                arsenal_nid = "Earthbending"
                            elif item_nid.startswith("Fire"):
                                arsenal_nid = "Firebending"
                            else:
                                arsenal_nid = "Waterbending"
                            arsenal_data = arsenals[arsenal_unit][arsenal_nid]

                    case "Tana":
                        if item_nid not in arsenals[arsenal_unit]:
                            if "_Buff" in item_nid or "_Heal" in item_nid:
                                arsenal_nid = "Tanas_Stash"
                            else:
                                arsenal_nid = "Tanas_Arsenal"
                            arsenal_data = arsenals[arsenal_unit][arsenal_nid]
                    # Filter Summon Weapons
                    case "Lindsey":
                        if not item_nid.endswith("_D"):
                            arsenal_nid = list(arsenals[arsenal_unit].keys())[0]
                            arsenal_data = arsenals[arsenal_unit][arsenal_nid]
                    case "Azuth":
                        if not item_nid.endswith("_A"):
                            arsenal_nid = list(arsenals[arsenal_unit].keys())[0]
                            arsenal_data = arsenals[arsenal_unit][arsenal_nid]
                    case _:
                        if arsenal_unit in arsenals:
                            if item_nid not in arsenals[arsenal_unit]:
                                arsenal_nid = list(arsenals[arsenal_unit].keys())[0]
                                arsenal_data = arsenals[arsenal_unit][arsenal_nid]
                if arsenal_data and (item_data := all_items[item_nid]):
                    if not (weapon_type := get_comp(item_data, "weapon_type", str)):
                        weapon_type = "Misc"
                    if weapon_type not in arsenal_data["items"]:
                        arsenal_data["items"][weapon_type] = []
                    arsenal_data["items"][weapon_type].append(item_nid)
            elif item_nid in ("Dragonstone", "Solar_Brace", "Lunar_Brace"):
                if item_nid == "Lunar_Brace":
                    arsenal_data = arsenals["Eirika"]["Eirikas_Arsenal"]
                elif item_nid == "Solar_Brace":
                    arsenal_data = arsenals["Ephraim"]["Ephraims_Arsenal"]
                elif item_nid == "Dragonstone":
                    arsenal_data = arsenals["Myrrh"]["Myrrh_Arsenal"]
                if item_data := all_items[item_nid]:
                    weapon_type = get_comp(item_data, "weapon_type", str)
                    if weapon_type == "":
                        weapon_type = "Misc"
                    if weapon_type not in arsenal_data["items"]:
                        arsenal_data["items"][weapon_type] = []
                    arsenal_data["items"][weapon_type].append(item_nid)

    # Sort by ranks arsenals
    ranks: dict[str, int] = {
        "E": 0,
        "D": 1,
        "C": 2,
        "B": 3,
        "A": 4,
        "S": 5,
        "SS": 6,
        "SSS": 7,
        "X": 8,
        "": 9,
    }

    def w_rank(x) -> int:
        if weapon_rank := get_comp(all_items[x], "weapon_rank", str):
            return ranks[weapon_rank]
        return 10

    sorted_arsenal = {}
    for arsenal_unit_id, arsenal_unit_dict in arsenals.items():
        sorted_arsenal[arsenal_unit_id] = {}
        for arsenal_id, arsenal_dict in arsenal_unit_dict.items():
            sorted_arsenal[arsenal_unit_id][arsenal_id] = {
                "name": arsenal_dict["name"],
                "desc": arsenal_dict["desc"],
                "items": {},
            }
            for arsenal_dict_key, arsenal_dict_value in arsenal_dict.items():
                if arsenal_dict_key == "items":
                    for (
                        arsenal_weapon_type_id,
                        arsenal_items_list,
                    ) in arsenal_dict_value.items():
                        sorted_arsenal[arsenal_unit_id][arsenal_id]["items"][
                            arsenal_weapon_type_id
                        ] = sorted(arsenal_items_list, key=w_rank)
    with (GUIDE_JSON_DIR / "arsenals.json").open("w", encoding="utf-8") as fp:
        json.dump(sorted_arsenal, fp)
    print("Done.")


def make_item_cat_new_json():
    print("Creating items.category.new.json ...")
    item_cats = {"Dragon's Gate": {}, "Accessories": {}}
    with (JSON_DIR / "items.json").open("r") as fp:
        for data_entry in sorted(json.load(fp), key=lambda x: x["name"]):
            if data_entry["nid"].endswith("_DG"):
                item_cats["Dragon's Gate"][data_entry["nid"]] = data_entry["name"]
            if (
                get_comp(data_entry, "equippable_accessory", bool)
                and data_entry["name"] not in item_cats["Accessories"].values()
            ):
                item_cats["Accessories"][data_entry["nid"]] = data_entry["name"]
            if wtype := get_comp(data_entry, "weapon_type", str):
                if wtype not in item_cats:
                    item_cats[wtype] = {}
                if data_entry["name"] not in item_cats[wtype].values():
                    item_cats[wtype][data_entry["nid"]] = data_entry["name"]
    # TODO add Consumables category
    with (GUIDE_JSON_DIR / "items.category.new.json").open("w+") as fp:
        json.dump(item_cats, fp)
    print("Done.")


def get_icons():
    print("Copying icons ...")
    new_icons_path = GUIDE_IMG_DIR / "icons"
    for entry in ICONS_16_DIR.iterdir():
        if entry.suffix == ".png":
            img = Image.open(entry)
            img = img.convert("RGBA")
            datas = img.getdata()
            new_img_data = []
            target_color = (128, 160, 128)
            for item in datas:
                if (
                    item[0] == target_color[0]  # pyright: ignore[reportIndexIssue]
                    and item[1] == target_color[1]  # pyright: ignore[reportIndexIssue]
                    and item[2] == target_color[2]  # pyright: ignore[reportIndexIssue]
                ):
                    new_img_data.append(
                        (255, 255, 255, 0)
                    )  # Replace with transparent white
                else:
                    new_img_data.append(item)
            img.putdata(new_img_data)
            img.save(new_icons_path / entry.name)
    print("Done.")


def get_portraits():
    print("Copying portraits ...")
    new_portraits_path = GUIDE_IMG_DIR / "portraits"
    for entry in PORTRAITS_DIR.iterdir():
        if entry.suffix == ".png":
            base_img = Image.open(entry)
            img = base_img.crop((0, 0, 96, 80))
            img = img.convert("RGBA")
            datas = img.getdata()
            new_img_data = []
            target_color = (128, 160, 128)
            for item in datas:
                if (
                    item[0] == target_color[0]  # pyright: ignore[reportIndexIssue]
                    and item[1] == target_color[1]  # pyright: ignore[reportIndexIssue]
                    and item[2] == target_color[2]  # pyright: ignore[reportIndexIssue]
                ):
                    new_img_data.append(
                        (255, 255, 255, 0)
                    )  # Replace with transparent white
                else:
                    new_img_data.append(item)
            img.putdata(new_img_data)
            img.save(new_portraits_path / entry.name)
    print("Done.")


def make_icon_css():
    print("Creating iconsheet.css ...")
    css_path = GUIDE_CSS_DIR / "iconsheet.css"
    icons_json = ICONS_16_DIR / "icons16.json"
    items_json = JSON_DIR / "items.json"
    skills_json = JSON_DIR / "skills.json"
    css_str = ""
    icon_height, icon_width = 16, 16
    added_icon_sheet = []
    with items_json.open("r") as fp:
        for entry in json.load(fp):
            if entry["icon_nid"]:
                if entry["icon_nid"] not in added_icon_sheet:
                    new_sheet_css = f"""
                    .{make_valid_class_name(entry["icon_nid"])}-icon {{
                        background-image: url(\'/static/images/icons/{quote(entry["icon_nid"]+".png")}\');
                        background-repeat: no-repeat;
                        width: 16px;
                        height: 16px;
                        display: inline-block;
                    }}\n
                    """
                    css_str += new_sheet_css
                    added_icon_sheet.append(entry["icon_nid"])
                css_str += f"""
                .{make_valid_class_name(entry["nid"])}-item-icon {{
                    background-position: -{entry["icon_index"][0]*icon_width}px -{entry["icon_index"][1]*icon_height}px;
                    margin: 0px 4px;
                    transform: scale(1.5);
                }}\n
                """
    with skills_json.open("r") as fp:
        for entry in json.load(fp):
            if entry["icon_nid"]:
                if entry["icon_nid"] not in added_icon_sheet:
                    new_sheet_css = f"""
                    .{make_valid_class_name(entry["icon_nid"])}-icon {{
                        background-image: url(\'/static/images/icons/{quote(entry["icon_nid"]+".png")}\');
                        background-repeat: no-repeat;
                        width: 16px;
                        height: 16px;
                        display: inline-block;
                    }}\n
                    """
                    css_str += new_sheet_css
                    added_icon_sheet.append(entry["icon_nid"])
                css_str += f"""
                .{make_valid_class_name(entry["nid"])}-skill-icon {{
                    background-position: -{entry["icon_index"][0]*icon_width}px -{entry["icon_index"][1]*icon_height}px;
                    margin: 0px 4px;
                    transform: scale(1.5);
                }}\n
                """
    with icons_json.open("r") as fp:
        for entry in json.load(fp):
            if entry["subicon_dict"]:
                subicon_classes = ",".join(
                    f".{make_valid_class_name(x)}-subIcon"
                    for x in entry["subicon_dict"]
                )

                new_sheet_css = f"""
                    {subicon_classes} {{
                        background-image: url(\'/static/images/icons/{quote(entry["nid"]+".png")}\');
                        background-repeat: no-repeat;
                        width: 16px;
                        height: 16px;
                        display: inline-block;
                    }}\n
                    """
                css_str += new_sheet_css
                for subicon_nid, subicon_index in entry["subicon_dict"].items():
                    css_str += f"""
                        .{make_valid_class_name(subicon_nid)}-subIcon {{
                            background-position: -{subicon_index[0]*icon_width}px -{subicon_index[1]*icon_height}px;
                            margin: 0px 4px;
                            transform: scale(1.5);
                        }}\n
                        """
    # Special case for monster wep missing in wexp_icons.png
    css_str += f"""
    .Wexpicons-icon.Monster-subIcon{{
    background-image: url(\'/static/images/icons/{quote("Monster WEP Icon.png")}\');
    background-repeat: no-repeat;
    background-position: -0px -0px;
    width: 16px;
    height: 16px;
    display: inline-block;
    margin: 0px 4px;
    transform: scale(1.5);
    }}\n
    """
    with css_path.open("w") as fp:
        fp.write(css_str)
    print("Done.")


def make_class_promo_json() -> None:
    print("Creating classes.promos.json ...")
    unit_promos = {}
    with (JSON_DIR / "classes.json").open("r") as fp:
        for data_entry in sorted(json.load(fp), key=lambda x: x["tier"], reverse=True):
            if data_entry["nid"] not in unit_promos:
                unit_promos[data_entry["nid"]] = {
                    "turns_into": data_entry["turns_into"],
                    "turns_from": [],
                }
            for class_nid in data_entry["turns_into"]:
                unit_promos[class_nid]["turns_from"].append(data_entry["nid"])
    with (GUIDE_JSON_DIR / "classes.promos.json").open("w+") as fp:
        json.dump(unit_promos, fp, indent=2)
    print("Done.")


def make_skill_hide_json() -> None:
    print("Creating skills.hidden.json ...")
    skills = {}
    with (JSON_DIR / "skills.json").open("r") as fp:
        for data_entry in json.load(fp):
            skills[data_entry["nid"]] = get_comp(data_entry, "hidden", bool)
    with (GUIDE_JSON_DIR / "skills.hidden.json").open("w+") as fp:
        json.dump(skills, fp)
    print("Done.")


def remove_bg(entry: Path):
    img = Image.open(entry)
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    target_color = (128, 160, 128)  # Example: black color
    for item in datas:
        if (
            item[0] == target_color[0]  # pyright: ignore[reportIndexIssue]
            and item[1] == target_color[1]  # pyright: ignore[reportIndexIssue]
            and item[2] == target_color[2]  # pyright: ignore[reportIndexIssue]
        ):
            new_data.append((255, 255, 255, 0))  # Replace with transparent white
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img


def get_map_sprites():
    with (JSON_DIR / "classes.json").open("r") as fp:
        fe_classes = json.load(fp)
    des_dir = GUIDE_IMG_DIR / "map_sprites"
    for data_entry in fe_classes:
        if data_entry["map_sprite_nid"]:
            sprite_path = MAP_SPRITES_DIR / f"{data_entry['map_sprite_nid']}-stand.png"
            sprite_sheet = remove_bg(sprite_path)
            frame_width = 192 / 3
            frame_height = 144 / 3
            num_columns = int(sprite_sheet.width // frame_width)
            # num_rows = int(sprite_sheet.height // frame_height)
            frames = []
            # for row in range(num_rows):
            row = 2
            for col in range(num_columns):
                left = col * frame_width
                upper = row * frame_height
                right = left + frame_width
                lower = upper + frame_height
                sprite = sprite_sheet.crop((left, upper, right, lower))
                frame = sprite.crop((8, 0, 64 - 8, 48))
                frames.append(frame)
            frames[0].save(
                des_dir / f"{data_entry['map_sprite_nid']}-stand.webp",
                save_all=True,
                append_images=frames[1:],
                duration=200,
                loop=0,
            )


def copy_json():
    game_data_jsons = (
        "affinities.json",
        "classes.json",
        "items.category.json",
        "items.json",
        "lore.json",
        "skills.category.json",
        "skills.json",
        "stats.json",
        "support_pairs.json",
        "units.category.json",
        "units.json",
        "weapon_ranks.json",
        "weapons.json",
    )
    for fname in game_data_jsons:
        if (JSON_DIR / fname).exists():
            print(f"Copying {fname} from ltproj directory ...")
            try:
                shutil.copy((JSON_DIR / fname), (GUIDE_JSON_DIR / fname))
            except Exception as e:
                print(f"Failed to copy {(JSON_DIR/fname)}! {e}")
        else:
            print(f"{(JSON_DIR/fname)} does not exist!")


def _get_status_equip(data_entry) -> list:
    exclude: tuple = (
        "_hide",
        "_Penalty",
        "_Buff",
        "_Effect",
        "_Gain",
        "_Proc",
        "_Weapon",
        "_AOE_Splash",
        "Drench",
        "Avo_Ddg_",
        "Luckblade",  # TODO
    )
    wp_status = []
    if s1 := get_comp(data_entry, "status_on_equip", str):
        if not any(sub in s1 for sub in exclude):
            wp_status.append(s1)
    if s2 := get_comp(data_entry, "multi_status_on_equip", list):
        for entry in s2:
            if not any(sub in entry for sub in exclude):
                wp_status.append(entry)
    return list(set(wp_status))


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


def add_to_db() -> None:
    db_path = Path(__file__).resolve().parent / "app/fe8r-guide.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    skill_cats = {}
    new_skill_cats = []
    with (JSON_DIR / "skills.category.json").open("r") as fp:
        for key, value in json.load(fp).items():
            skill_cats[key] = value
            if value not in (x.nid for x in new_skill_cats if new_skill_cats):
                if value.startswith("MyUnit/T"):
                    new_skill_cats.append(
                        SkillCategory(
                            nid=value, name=f"Feats (Tier {value.split('/T')[1]})"
                        )
                    )
                else:
                    new_skill_cats.append(SkillCategory(nid=value, name=value))
    with Session(engine) as session:
        # Add skills
        with (JSON_DIR / "skills.json").open("r") as fp:
            new_skills = [
                Skill(
                    nid=data_entry["nid"],
                    name=data_entry["name"],
                    desc=process_styled_text(data_entry["desc"]),
                    icon_class=(
                        f"{make_valid_class_name(data_entry["nid"])}-skill-icon "
                        + f"{make_valid_class_name(data_entry["icon_nid"])}-icon"
                        if data_entry["icon_nid"]
                        else ""
                    ),
                    is_hidden=get_comp(data_entry, "hidden", bool),
                    category_nid=skill_cats[data_entry["nid"]],
                )
                for data_entry in json.load(fp)
            ]
            session.add_all(new_skills)
            session.add_all(new_skill_cats)
        # Add items
        with (JSON_DIR / "items.json").open("r") as fp:
            for data_entry in json.load(fp):
                if target := [
                    x for x in data_entry["components"] if x[0].startswith("target")
                ]:
                    target = target[0][0].split("_")[1].title()
                else:
                    target = ""
                new_item = Item(
                    nid=data_entry["nid"],
                    name=data_entry["name"],
                    desc=process_styled_text(data_entry["desc"]),
                    value=get_comp(data_entry, "value", int),
                    weapon_rank=get_comp(data_entry, "weapon_rank", str),
                    weapon_type=get_comp(data_entry, "weapon_type", str),
                    damage=get_comp(data_entry, "damage", int),
                    weight=get_comp(data_entry, "weight", int),
                    crit=get_comp(data_entry, "crit", int),
                    hit=get_comp(data_entry, "hit", int),
                    min_range=get_comp(data_entry, "min_range", int),
                    max_range=get_comp(data_entry, "max_range", int),
                    target=target,
                    icon_class=(
                        f"{make_valid_class_name(data_entry['nid'])}-item-icon {make_valid_class_name(data_entry['icon_nid'])}-icon"
                        if data_entry["icon_nid"]
                        else ""
                    ),
                )
                session.add(new_item)
                # Add item skills
                if status_on_equip := _get_status_equip(data_entry):
                    if item_with_skill := session.get(Item, data_entry["nid"]):
                        for skill_nid in status_on_equip:
                            try:
                                item_with_skill.status_on_equip.append(
                                    session.get(Skill, skill_nid)
                                )
                            except IntegrityError:
                                print("Skipping existing entry.")

        session.commit()
        # Add sub_items
        with (JSON_DIR / "items.json").open("r") as fp:
            for data_entry in json.load(fp):
                if sub_items := get_comp(data_entry, "multi_item", list):
                    if super_item := session.get(Item, data_entry["nid"]):
                        for sub_item_nid in sub_items:
                            super_item.sub_items.append(session.get(Item, sub_item_nid))
        session.commit()
        # Add shops
        alt_shops = {}
        with (JSON_DIR / "events.json").open("r") as fp:
            for data_entry in sorted(json.load(fp), key=lambda x: x["nid"]):
                if (
                    data_entry["nid"].endswith(("Vendor", "SecretShop", "Armory"))
                    and data_entry["name"] not in ("Armory", "Vendor", "SecretShop")
                    and "Dragons_Gate" not in data_entry["nid"]
                ):
                    shop_name = ""
                    shop_items = next(
                        x.split(";")[2].split(",")
                        for x in data_entry["_source"]
                        if x.startswith("shop;")
                    )
                    for key, val in alt_shops.items():
                        if sorted(shop_items) == sorted(val):
                            shop_name += f"{" ".join(key.split()[:-1])} / "
                    shop_name += " ".join(re.split(r"(?=[A-Z])", data_entry["name"]))
                    shop_name = " ".join(shop_name.split()).rstrip().lstrip()
                    if "SecretShop" in data_entry["nid"]:
                        shop_type = "Secret Shop"
                    elif "Armory" in data_entry["nid"]:
                        shop_type = "Armory"
                    else:
                        shop_type = "Vendor"
                    new_shop = Shop(
                        nid=data_entry["nid"],
                        name=shop_name,
                        type=shop_type,
                        order_name=pad_digits_in_string(shop_name, 2),
                    )
                    session.add(new_shop)
                    for item_nid in shop_items:
                        if curr_shop := session.get(Shop, data_entry["nid"]):
                            curr_shop.items.append(session.get(Item, item_nid))
                elif data_entry["name"] in ("Armory", "Vendor", "SecretShop"):
                    shop_items = next(
                        x.split(";")[2].split(",")
                        for x in data_entry["_source"]
                        if x.startswith("shop;")
                    )
                    alt_shops["Chapter " + data_entry["nid"]] = shop_items
        # Add Dragon's Gate to shops
        new_shop = Shop(
            nid="Dragon_Gate",
            name="Dragon's Gate (Anna)",
            type="Vendor",
            order_name="Z_Dragon_Gate",
        )
        session.add(new_shop)
        with (JSON_DIR / "items.json").open("r") as fp:
            for data_entry in json.load(fp):
                if data_entry["nid"].endswith("_DG"):
                    if curr_shop := session.get(Shop, "Dragon_Gate"):
                        curr_shop.items.append(session.get(Item, data_entry["nid"]))
        session.commit()


def main():
    copy_json()
    make_arsenal_json()
    make_class_promo_json()
    make_item_cat_new_json()
    minify_json()
    get_icons()
    get_portraits()
    get_map_sprites()
    make_icon_css()
    add_to_db()


if __name__ == "__main__":
    main()
