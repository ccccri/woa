"""Validation of user input coming from the configuration page."""

import re

MAX_NAME_LENGTH = 64
_HEX12 = re.compile(r"^[0-9A-F]{12}$")
_SEPARATORS = re.compile(r"[\s:\-.]")


def normalize_mac(raw):
    """Return the MAC as 'AA-BB-CC-DD-EE-FF' (the format Alexa expects).

    Accepts colons, dashes, dots, spaces or no separator at all.
    Raises ValueError for anything that cannot be a unicast device MAC.
    """
    if not isinstance(raw, str):
        raise ValueError("MAC address is required")
    digits = _SEPARATORS.sub("", raw).upper()
    if not _HEX12.match(digits):
        raise ValueError("MAC address must have 12 hexadecimal digits")
    if digits in ("000000000000", "FFFFFFFFFFFF"):
        raise ValueError("MAC address is not a device address")
    if int(digits[:2], 16) & 1:
        raise ValueError("MAC address is a multicast address")
    return "-".join(digits[i:i + 2] for i in range(0, 12, 2))


def normalize_name(raw):
    """Return a friendly name Alexa accepts: letters, digits and spaces only."""
    if not isinstance(raw, str):
        raise ValueError("Name is required")
    name = " ".join(raw.split())
    if not name:
        raise ValueError("Name is required")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be at most {MAX_NAME_LENGTH} characters")
    if not all(ch.isalnum() or ch == " " for ch in name):
        raise ValueError("Name can contain only letters, digits and spaces")
    return name
