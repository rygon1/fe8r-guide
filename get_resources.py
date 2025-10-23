#!/usr/bin/python3

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

try:
    with Path("ltprojpath.txt").open("r") as fp:
        LTPROJ_DIR = Path(fp.read())
except FileNotFoundError:
    print("Error: The file 'my_file.txt' was not found.")

if not LTPROJ_DIR.exists():
    raise FileNotFoundError(f"The directory {LTPROJ_DIR} does not exist.")

JSON_DIR: Path = LTPROJ_DIR / "game_data"
GUIDE_JSON_DIR: Path = Path.cwd() / "app/static/json"
GUIDE_IMG_DIR: Path = Path.cwd() / "app/static/images"
ICONS_16_DIR = LTPROJ_DIR / "resources/icons16"


def minify_json() -> None:
    """
    Removes JSON whitespace to save some bandwidth. Not necessary if running locally.
    """
    print(f"Creating minified JSON files in {GUIDE_JSON_DIR} ...")
    for json_fpath in GUIDE_JSON_DIR.iterdir():
        if json_fpath.suffix == ".json":
            with json_fpath.open("r") as fp:
                x = json.load(fp)
            with json_fpath.open("w") as fp:
                json.dump(x, fp, separators=(",", ":"))
    print("Done.")


def get_comp(entry, comp_name: str, comp_type: type) -> Any:
    """
    Returns component value
    """
    if comp_entry := [x for x in entry["components"] if x[0] == comp_name]:
        if comp_type == bool:
            if comp_entry[0][1] is None:
                return True
        else:
            return comp_entry[0][1]
    if comp_type == bool:
        return False
    elif comp_type == int:
        return 0
    elif comp_type == str:
        return ""
    elif comp_type == list:
        return []
    else:
        return None


def process_styled_text(raw_text) -> str:
    """
    Converts in-game desc tags to html. Note that this uses pico.css, so remember to change the
    classes to get proper colors.
    """
    new_text: Any = raw_text
    replacements: tuple[
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
    ] = (
        (
            r"\<icon\>(.*?)\</\>",
            r'<img class="skill-icon" src="/static/images/icons/\1.webp" title="\1" height="24" width="24" alt="\1"/>',
        ),
        (r"\<([^/]*?)\>(.*?)(\</\>)", r'<span class="pico-color-\1-500">\2</span>'),
        (r"{e:(.*?)}", r""),
        (r" \(<span class=\"pico-color-red-500\"></span>\)", r""),
        (r"\n", r"<br/>"),
    )
    for pattern, replacement in replacements:
        new_text = re.sub(pattern, replacement, new_text)
    return new_text


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
        for item_data in json.load(fp):
            if (
                get_comp(item_data, "multi_item_hides_unavailable", bool)
                or item_data["nid"]
                in (
                    "Vector_Arsenal",
                    "Andre_Arsenal",
                )  # Have no multi_item_hides_unavailable
            ) and item_data["nid"] not in ("Davius_Arsenal_Old",):
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
    arsenal_data: dict[Any, Any] = {}
    with (JSON_DIR / "items.category.json").open("r") as fp:
        for item_nid, items_cat in json.load(fp).items():
            if (
                items_cat.startswith("Personal Weapons")
                and item_nid not in arsenal_nid_list
                and not item_nid.endswith("_Old")
            ):
                arsenal_unit = items_cat.split("/")[1]
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

                    case _:
                        if arsenal_unit in arsenals:
                            if item_nid not in arsenals[arsenal_unit]:
                                arsenal_nid = list(arsenals[arsenal_unit].keys())[0]
                                arsenal_data = arsenals[arsenal_unit][arsenal_nid]
                if item_data := all_items[item_nid]:
                    weapon_type = get_comp(item_data, "weapon_type", str)
                    if weapon_type == "":
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
        return ranks[get_comp(all_items[x], "weapon_rank", str)]

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


def extract_icon_from_sheet(
    icon_sheet_path: Path | str,
    x: int,
    y: int,
    width: int,
    height: int,
    output_path: Path | str,
) -> None:
    """
    Extracts an icon from an icon sheet and saves it as a new image.
    Args:
        x, y (int): Coordinates of icon in icon sheet. Starts at top left.
        width, height (int): Icon size in pixels
    """
    try:
        icon_sheet = Image.open(icon_sheet_path)
        icon_bbox = (x * width, y * height, x * width + width, y * height + height)
        extracted_icon = icon_sheet.crop(icon_bbox)
        extracted_icon = extracted_icon.convert("RGBA")
        # Remove background
        datas = extracted_icon.getdata()
        new_img_data = []
        target_color = (128, 160, 128)
        for item in datas:
            if (
                item[0] == target_color[0]
                and item[1] == target_color[1]
                and item[2] == target_color[2]
            ):
                new_img_data.append((255, 255, 255, 0))
            else:
                new_img_data.append(item)
        extracted_icon.putdata(new_img_data)
        extracted_icon.save(output_path, "webp")
    except FileNotFoundError:
        print(f"Error: Icon sheet not found at {icon_sheet_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_skill_icons():
    print(f"Getting icons from icon sheets ...")
    icon_json = ICONS_16_DIR / "icons16.json"
    output_dir = GUIDE_IMG_DIR / "icons"
    with icon_json.open("r") as fp:
        for entry in json.load(fp):
            if entry["nid"] in (
                "skill_icons",
                "wexp_icons",
                "Affinity",
                "Monster WEP Icon",
            ):
                for fname, coords in entry["subicon_dict"].items():
                    extract_icon_from_sheet(
                        ICONS_16_DIR / f"{entry["nid"]}.png",
                        coords[0],
                        coords[1],
                        16,
                        16,
                        output_dir / f"{fname}.webp",
                    )
    print("Done.")


def main():
    make_arsenal_json()
    minify_json()
    get_skill_icons()


if __name__ == "__main__":
    main()
