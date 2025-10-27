"""
Contains the colors palettes uses to colors the boxes.
"""

import numpy as np
from beartype.typing import Union


# Find color by name or hex code: https://www.color-name.com

# primary_colors
# Color name (in order):
# Alphabet Red, Nokia Blue, Discord Green,
# Cashmere Purple, Supreme Orange, Middle Yellow,
# Oak Brown, deep Pink, Simple Gray

primary_colors = {
    "hex": (
        "#ED1C24",
        "#005AFF",
        "#57F287",
        "#664E88",
        "#EA871E",
        "#FFEB00",
        "#87633A",
        "#FF1493",
        "#676765",
    ),
    "rgb": (
        (237, 28, 36),
        (0, 90, 255),
        (87, 242, 135),
        (102, 78, 136),
        (234, 135, 30),
        (255, 235, 0),
        (135, 99, 58),
        (255, 20, 147),
        (103, 103, 101),
    ),
}

# light_colors
# Color name (in order):
# Light Baby Blue, Light Red, Whole Foods Green,
# Light Purple Blue, Clear Orange, Mid Yellow,
# Bakery Brown, Lotus Pink, Neutral Light Gray

light_colors = {
    "hex": (
        "#A6DAF4",
        "#FF7F7F",
        "#006F46",
        "#BD86D2",
        "#FCBF8D",
        "#DDD59D",
        "#BF8654",
        "#EAD0D6",
        "#CACACA",
    ),
    "rgb": (
        (166, 218, 244),
        (255, 127, 127),
        (0, 111, 70),
        (189, 134, 210),
        (252, 191, 141),
        (221, 213, 157),
        (191, 134, 84),
        (234, 208, 214),
        (202, 202, 202),
    ),
}


def mixing_palettes(dict1: dict, dict2: dict) -> dict:
    """
    Mixes two color palettes together.
    """
    if dict1.keys() != dict2.keys():
        raise ValueError("The keys of the two dictionaries must be the same.")

    return {key: dict1[key] + dict2[key] for key in dict1.keys()}


def shades_colors(
    base_color: Union[str, tuple], num_shades=5, lighten_factor=0.15, darken_factor=0.1
) -> Union[tuple[int, int, int], str]:
    """
    Generate shades of a color based on the base color.

    Args:
        base_color (str | tuple): Hex color value (e.g., "#B4FBB8") or RGB tuple.
        num_shades (int): Number of shades to generate (default is 5).
        lighten_factor (float): Factor to lighten the base color (0 to 1, default is 0.15).
        darken_factor (float): Factor to darken the base color (0 to 1, default is 0.1).

    Returns:
        tuple[int, int, int] | str: RGB tuple representing the shade color, or hex string if input was hex.
    """

    def hex_to_rgb(hex_value: str) -> tuple[int, int, int]:
        hex_value = hex_value.lstrip("#")
        return tuple(
            int(hex_value[i : i + len(hex_value) // 3], 16)
            for i in range(0, len(hex_value), len(hex_value) // 3)
        )  # type: ignore

    # Check if base_color is a hex string
    is_hex = isinstance(base_color, str) and base_color.startswith("#")

    if is_hex and isinstance(base_color, str):
        base_color = hex_to_rgb(base_color)

    base_rgb = np.array(base_color)
    shades = [
        base_rgb * (1 - lighten_factor * i) * (1 - darken_factor * (num_shades - i))
        for i in range(num_shades)
    ]
    color_tuple = tuple(int(x) for x in (base_rgb - shades[-1].astype(int)))

    # Return hex string if input was hex, otherwise return RGB tuple
    if is_hex:
        return f"#{color_tuple[0]:02x}{color_tuple[1]:02x}{color_tuple[2]:02x}"
    else:
        return color_tuple  # type: ignore
