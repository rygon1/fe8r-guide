import re
from typing import Any

SKILL_EXCLUDE = (
    "Absolute_Mastery_Anima",
    "Absolute_Mastery_Light",
    "Absolute_Mastery_Staff",
    "Absolute_Mastery_Dark",
    "_hide",
    "Feat_Enabler",
)


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
    return None


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
