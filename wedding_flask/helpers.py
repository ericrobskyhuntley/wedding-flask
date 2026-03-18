from datetime import datetime
from zoneinfo import ZoneInfo


def dt_parse(string):
    return datetime.fromisoformat(string.replace("Z", "+00:00")).astimezone(
        ZoneInfo("America/New_York")
    )


def unique(l):
    return list(set(l))

def address_if_blank(existing, new_col, new_dict, concat_string = ", "):
    """
    concatenates values of a dict based on whether value exists.
    """
    if new_col in new_dict:
        if len(existing) > 0:
            existing = existing + concat_string + new_dict[new_col]
        else:
            existing = new_dict[new_col]
    return existing