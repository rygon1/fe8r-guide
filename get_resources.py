#!/usr/bin/python3
import json
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from PIL import Image

from add_to_db import add_to_db
from app.blueprints.utils import (
    load_json_data,
    log_execution_step,
    make_valid_class_name,
    save_json_data,
)

# --- Configuration & Constants ---
CONFIG_FILE = Path("config.json")


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()

# Load Paths
LTPROJ_DIR = Path(config.get("ltproj_path", ""))
if not LTPROJ_DIR.exists():
    raise FileNotFoundError(
        f"The directory {LTPROJ_DIR} does not exist. Check config.json."
    )

# Load Color (Convert list to tuple for PIL)
TARGET_COLOR = tuple(config.get("target_color", [128, 160, 128]))

# Define Resource Paths
JSON_DIR = LTPROJ_DIR / "game_data"
ICONS_16_DIR = LTPROJ_DIR / "resources/icons16"
PORTRAITS_DIR = LTPROJ_DIR / "resources/portraits"
MAP_SPRITES_DIR = LTPROJ_DIR / "resources/map_sprites"

# App Static Paths
APP_STATIC = Path.cwd() / "app/static"
GUIDE_JSON_DIR = APP_STATIC / "json"
GUIDE_IMG_DIR = APP_STATIC / "images"
GUIDE_CSS_DIR = APP_STATIC / "css"

RANK_VALUES = {
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

# --- Helper Functions ---


def process_image_transparency(
    img: Image.Image, target_rgb: tuple[int, int, int] = TARGET_COLOR
) -> Image.Image:
    """
    Converts a specific RGB color to transparent.
    """
    img = img.convert("RGBA")
    datas = img.getdata()

    # Replace target color with transparent pixel
    new_data = [
        (255, 255, 255, 0) if item[:3] == target_rgb else item for item in datas
    ]

    img.putdata(new_data)
    return img


# --- Core Logic Functions ---


@log_execution_step
def minify_json() -> None:
    """Removes JSON whitespace to save bandwidth."""
    for json_fpath in GUIDE_JSON_DIR.glob("*.json"):
        data = load_json_data(json_fpath)
        save_json_data(json_fpath, data, separators=(",", ":"))


@log_execution_step
def get_icons():
    dest_dir = GUIDE_IMG_DIR / "icons"
    dest_dir.mkdir(parents=True, exist_ok=True)

    for entry in ICONS_16_DIR.glob("*.png"):
        with Image.open(entry) as img:
            processed_img = process_image_transparency(img)
            processed_img.save(dest_dir / entry.name)


@log_execution_step
def get_portraits():
    dest_dir = GUIDE_IMG_DIR / "portraits"
    dest_dir.mkdir(parents=True, exist_ok=True)

    for entry in PORTRAITS_DIR.glob("*.png"):
        with Image.open(entry) as base_img:
            # Crop first, then process transparency
            img = base_img.crop((0, 0, 96, 80))
            processed_img = process_image_transparency(img)
            processed_img.save(dest_dir / entry.name)


@log_execution_step
def make_icon_css():
    items = load_json_data(JSON_DIR / "items.json")
    skills = load_json_data(JSON_DIR / "skills.json")
    weapons = load_json_data(JSON_DIR / "weapons.json")
    icons = load_json_data(ICONS_16_DIR / "icons16.json")

    css_lines = []
    added_sheets = set()
    icon_w, icon_h = 16, 16

    def add_sheet_entry(icon_nid_val):
        if icon_nid_val and icon_nid_val not in added_sheets:
            safe_cls = make_valid_class_name(icon_nid_val)
            url_str = quote(icon_nid_val + ".png")
            css_lines.append(
                f".{safe_cls}-icon {{ background-image: url('/static/images/icons/{url_str}'); "
                f"background-repeat: no-repeat; width: 16px; height: 16px; display: inline-block; }}"
            )
            added_sheets.add(icon_nid_val)

    def add_position_entry(nid, icon_idx, suffix):
        safe_nid = make_valid_class_name(nid)
        pos_x = -(icon_idx[0] * icon_w)
        pos_y = -(icon_idx[1] * icon_h)
        css_lines.append(
            f".{safe_nid}-{suffix} {{ background-position: {pos_x}px {pos_y}px; "
            f"margin: 0px 4px; transform: scale(1.5); }}"
        )

    # Process Items
    for entry in items:
        if entry["icon_nid"]:
            add_sheet_entry(entry["icon_nid"])
            add_position_entry(entry["nid"], entry["icon_index"], "item-icon")

    # Process Skills
    for entry in skills:
        if entry["icon_nid"]:
            add_sheet_entry(entry["icon_nid"])
            add_position_entry(entry["nid"], entry["icon_index"], "skill-icon")

    # Process Weapons
    for entry in weapons:
        if entry["icon_nid"]:
            add_sheet_entry(entry["icon_nid"])
            add_position_entry(entry["nid"], entry["icon_index"], "weapon-icon")

    # Process SubIcons
    for entry in icons:
        if entry["subicon_dict"]:
            sub_classes = ",".join(
                f".{make_valid_class_name(x)}-subIcon" for x in entry["subicon_dict"]
            )
            url_str = quote(entry["nid"] + ".png")

            css_lines.append(
                f"{sub_classes} {{ background-image: url('/static/images/icons/{url_str}'); "
                f"background-repeat: no-repeat; width: 16px; height: 16px; display: inline-block; }}"
            )

            for sub_nid, sub_idx in entry["subicon_dict"].items():
                add_position_entry(sub_nid, sub_idx, "subIcon")

    # Special case
    monster_icon_url = quote("Monster WEP Icon.png")
    css_lines.append(
        f".Wexpicons-icon.Monster-subIcon {{ background-image: url('/static/images/icons/{monster_icon_url}'); "
        "background-repeat: no-repeat; background-position: 0px 0px; width: 16px; height: 16px; "
        "display: inline-block; margin: 0px 4px; transform: scale(1.5); }"
    )

    with (GUIDE_CSS_DIR / "iconsheet.css").open("w", encoding="utf-8") as fp:
        fp.write("\n".join(css_lines))


@log_execution_step
def make_class_promo_json() -> None:
    classes = sorted(
        load_json_data(JSON_DIR / "classes.json"), key=lambda x: x["tier"], reverse=True
    )
    promos = {}

    for entry in classes:
        nid = entry["nid"]
        if nid not in promos:
            promos[nid] = {"turns_into": entry["turns_into"], "turns_from": []}

        for target_cls in entry["turns_into"]:
            # Ensure target exists in dict
            if target_cls not in promos:
                promos[target_cls] = {"turns_into": [], "turns_from": []}
            promos[target_cls]["turns_from"].append(nid)

    save_json_data(GUIDE_JSON_DIR / "classes.promos.json", promos, indent=2)


@log_execution_step
def get_map_sprites():
    fe_classes = load_json_data(JSON_DIR / "classes.json")
    dest_dir = GUIDE_IMG_DIR / "map_sprites"
    dest_dir.mkdir(parents=True, exist_ok=True)

    frame_width = 192 // 3
    frame_height = 144 // 3
    row_to_capture = 2

    for entry in fe_classes:
        if not entry["map_sprite_nid"]:
            continue

        sprite_path = MAP_SPRITES_DIR / f"{entry['map_sprite_nid']}-stand.png"
        if not sprite_path.exists():
            continue

        with Image.open(sprite_path) as raw_img:
            sprite_sheet = process_image_transparency(raw_img)
            num_columns = int(sprite_sheet.width // frame_width)

            frames = []
            for col in range(num_columns):
                left = col * frame_width
                upper = row_to_capture * frame_height
                right = left + frame_width
                lower = upper + frame_height

                sprite = sprite_sheet.crop((left, upper, right, lower))
                frame = sprite.crop((8, 0, 56, 48))
                frames.append(frame)

            if frames:
                out_path = dest_dir / f"{entry['map_sprite_nid']}-stand.webp"
                frames[0].save(
                    out_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=200,
                    loop=0,
                )


@log_execution_step
def copy_json():
    files_to_copy = [
        "affinities.json",
        "classes.json",
        "lore.json",
        "stats.json",
        "support_pairs.json",
        "units.category.json",
        "units.json",
        "weapon_ranks.json",
        "weapons.json",
    ]

    for fname in files_to_copy:
        src = JSON_DIR / fname
        dst = GUIDE_JSON_DIR / fname

        if src.exists():
            print(f"Copying {fname}...")
            try:
                shutil.copy(src, dst)
            except OSError as e:
                print(f"Failed to copy {src}: {e}")
        else:
            print(f"Warning: {src} does not exist!")


def main():
    GUIDE_JSON_DIR.mkdir(parents=True, exist_ok=True)
    GUIDE_IMG_DIR.mkdir(parents=True, exist_ok=True)
    GUIDE_CSS_DIR.mkdir(parents=True, exist_ok=True)

    copy_json()
    make_class_promo_json()
    minify_json()
    get_icons()
    get_portraits()
    get_map_sprites()
    make_icon_css()

    add_to_db(JSON_DIR)


if __name__ == "__main__":
    main()
