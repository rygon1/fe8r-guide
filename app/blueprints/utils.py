import json
import re
import time
from functools import wraps
from pathlib import Path
from typing import Any, TypeAlias

SKILL_EXCLUDE = (
    "Absolute_Mastery_Anima",
    "Absolute_Mastery_Light",
    "Absolute_Mastery_Staff",
    "Absolute_Mastery_Dark",
    "_hide",
    "Feat_Enabler",
)

STATUS_EXCLUDE: tuple[str, ...] = (
    "_hide",
    "_Penalty",
    "_Gain",
    "_Proc",
    "_Weapon",
    "_AOE_Splash",
    "_Boss",
    "Avo_Ddg_",
)

DataEntry: TypeAlias = dict[str, Any]


def load_json_data(file_path: Path):
    """
    Loads and returns data from a specified JSON file.
    (Not decorated to avoid spamming logs for every single file load)
    """
    with file_path.open("r") as fp:
        return json.load(fp)


def save_json_data(
    file_path: Path,
    data: Any,
    indent: int | None = None,
    separators: tuple[str, str] | None = None,
) -> None:
    """Helper to save JSON data safely."""
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=indent, separators=separators)


def log_execution_step(func):
    """
    Decorator that prints a message before a function starts and
    after it completes successfully.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[*] Starting task: {func.__name__}...")
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(f"[✓] Successfully finished: {func.__name__} ({duration:.2f}s)\n")
            return result
        except Exception as e:
            print(f"[!] FAILED task: {func.__name__}")
            print(f"    Error: {e}")
            raise  # Re-raise the exception so the script stops and you see the traceback

    return wrapper


def make_valid_class_name(s) -> str:
    # Remove invalid characters and replace underscores with dashes and spaces with underscores
    cleaned_s = (
        "".join(c for c in s if c.isalnum() or c in (" ", "_", "-"))
        .replace("_", "-")
        .replace(" ", "_")
    )
    # Ensure it starts with a letter or underscore
    if cleaned_s and not cleaned_s[0].isalpha():
        cleaned_s = "xx" + cleaned_s
    # Convert to PascalCase (optional, but common for Python class names)
    parts = cleaned_s.split("_")
    pascal_case_name = "-".join(part.capitalize() for part in parts)
    return pascal_case_name


def convert_func(matchobj) -> str:
    if tag_name := matchobj.group(1):
        if tag_name == "icon":
            if m := matchobj.group(2):
                return f'<span class="{make_valid_class_name(m.lstrip().rstrip())}-subIcon"></span>'
        else:
            if m := matchobj.group(2):
                return f'<span class="lt-color-{tag_name}">{m}</span>'

    return ""


def process_styled_text(raw_text) -> str:
    """
    Converts in-game desc tags to html. Note that this uses pico.css, so remember to change the
    classes to get proper colors.
    """
    new_text = raw_text
    replacements: tuple[
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
        tuple[str, str],
    ] = (
        (
            r"\<(.*?)\>(.*?)(\</\>)",
            convert_func,  # pyright: ignore[reportAssignmentType]
        ),
        (r"{e:(.*?)}", r""),
        (r" \(<span class=\"lt-color-red\"></span>\)", r""),
        (r"\n", r"<br/>"),
        (r"\{br\}", r"<br/>"),
    )
    for pattern, replacement in replacements:
        new_text = re.sub(pattern, replacement, new_text)
    return new_text


def get_alt_name(orig_name: str, orig_nid: str) -> str:
    if orig_nid == orig_name:
        return ""
    alt_name = orig_nid
    replacements = (
        (r"_", r" "),
        (r"T\d", r""),
        (r"Leg ", r""),
    )
    for pattern, replacement in replacements:
        alt_name = re.sub(pattern, replacement, alt_name)
    alt_name = alt_name.replace(orig_name, "").lstrip().rstrip()
    return alt_name


def get_comp_old(entry, comp_name: str, comp_type: type) -> Any:
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
    return None


def get_status_equip(data_entry: DataEntry) -> list[str]:
    """
    Extracts unique, non-excluded status names from various component fields of an entry.

    :param data_entry: The item data entry to process.
    :type data_entry: DataEntry
    :returns: A list of unique status names associated with the item, excluding any in EXCLUDE.
    :rtype: list[str]
    """
    excluded_substrings: tuple[str, ...] = STATUS_EXCLUDE
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


def get_comp(entry: DataEntry, comp_name: str, comp_type: type) -> Any:
    """
    Retrieves the value of a component from an entry.
    Returns a default value based on comp_type if the component is not found.

    :param entry: The item data entry dictionary to search within.
    :type entry: DataEntry
    :param comp_name: The string name of the component to find (e.g., 'status_on_equip').
    :type comp_name: str
    :param comp_type: The expected type of the component's value (e.g., str, list, bool).
    :type comp_type: type
    :returns: The component's value, or a type-appropriate default.
    :rtype: Any
    """
    default_values: dict[type, Any] = {
        bool: False,
        int: 0,
        str: "",
        list: [],
    }

    comp_entry: list[Any] | None = next(
        (x for x in entry.get("components", []) if x[0] == comp_name), None
    )

    if comp_entry:
        value = comp_entry[1]
        if comp_type is bool and value is None:
            return True
        return value

    if comp_type is bool:
        return False
    return default_values.get(comp_type, None)


def pad_digits_in_string(text, width):
    """
    Finds all sequences of digits in a string and pads them with
    leading zeros to the specified width.
    """

    # Define a replacement function that takes the regex match object
    def replacer(match):
        # match.group(0) is the sequence of digits found (e.g., '1', '10', '007')
        digit_string = match.group(0)
        # Apply the padding using zfill()
        return digit_string.zfill(width)

    # re.sub() finds all matches of r'\d+' and replaces them using the replacer function
    return re.sub(r"\d+", replacer, text)
