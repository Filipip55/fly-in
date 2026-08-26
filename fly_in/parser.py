"""Parser del file mappa per la simulazione fly-in.

Analizza i file di mappa .txt che definiscono zone, connessioni e
numero di droni.
"""

import re
from typing import Dict, List, Optional, Set, Tuple


class ParseError(Exception):
    """Eccezione sollevata quando il parsing della mappa fallisce."""

    pass


class Zone:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: str,
        color: Optional[str],
        max_drones: int,
        is_start: bool = False,
        is_end: bool = False
    ):
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.max_drones = max_drones
        self.is_start = is_start
        self.is_end = is_end


class Connection:
    def __init__(self, zone1: str, zone2: str, max_link_capacity: int):
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity


class Map:
    def __init__(self, nb_drones: int):
        self.nb_drones = nb_drones
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.start_zone: Optional[str] = None
        self.end_zone: Optional[str] = None


def parse_metadata(metadata_str: str, line_num: int) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    if not metadata_str:
        return metadata
    tokens = metadata_str.strip().split()
    for token in tokens:
        if "=" not in token:
            msg = f"Line {line_num}: Invalid metadata syntax '{token}'."
            raise ParseError(msg)
        parts = token.split("=", 1)
        if not parts[0] or not parts[1]:
            msg = f"Line {line_num}: Invalid metadata syntax '{token}'."
            raise ParseError(msg)
        metadata[parts[0]] = parts[1]
    return metadata


def _parse_zone(
    map_obj: Map,
    seen_coords: Set[Tuple[int, int]],
    line_idx: int,
    zone_prefix: str,
    name: str,
    x_str: str,
    y_str: str,
    metadata_str: Optional[str]
) -> None:
    x = int(x_str)
    y = int(y_str)

    if (x, y) in seen_coords:
        msg = (f"Line {line_idx+1}: Zone '{name}' has duplicate "
               f"coordinates ({x}, {y}). Another zone is already "
               "at this position.")
        raise ParseError(msg)
    seen_coords.add((x, y))

    zone_type = "normal"
    color = None
    max_drones = 1

    if metadata_str is not None:
        metadata = parse_metadata(metadata_str, line_idx + 1)

        valid_keys = {"zone", "color", "max_drones"}
        unknown = set(metadata.keys()) - valid_keys
        if unknown:
            keys = ", ".join(sorted(unknown))
            msg = (f"Line {line_idx+1}: Unknown zone metadata "
                   f"key(s): {keys}. Valid keys: "
                   f"{', '.join(sorted(valid_keys))}.")
            raise ParseError(msg)

        if "zone" in metadata:
            valid_types = ["normal", "blocked", "restricted", "priority"]
            if metadata["zone"] not in valid_types:
                t = metadata["zone"]
                msg = f"Line {line_idx+1}: Invalid zone type '{t}'."
                raise ParseError(msg)
            zone_type = metadata["zone"]

        if "color" in metadata:
            color_val = metadata["color"]
            if not color_val.isalpha():
                msg = (f"Line {line_idx+1}: Invalid color '{color_val}'. "
                       "Color must be a valid single-word alphabetic string.")
                raise ParseError(msg)
            color = color_val

        if "max_drones" in metadata:
            try:
                md = int(metadata["max_drones"])
                if md <= 0:
                    raise ValueError()
                max_drones = md
            except ValueError:
                msg = (f"Line {line_idx+1}: max_drones must be a "
                       "positive integer greater than 0.")
                raise ParseError(msg)

    if name in map_obj.zones:
        raise ParseError(f"Line {line_idx+1}: Duplicate zone name '{name}'.")

    is_start = (zone_prefix == "start_hub")
    is_end = (zone_prefix == "end_hub")

    if is_start:
        if zone_type == "blocked":
            msg = f"Line {line_idx+1}: start_hub cannot be blocked."
            raise ParseError(msg)
        if map_obj.start_zone:
            msg = f"Line {line_idx+1}: Only one start_hub can be defined."
            raise ParseError(msg)
        map_obj.start_zone = name
        max_drones = -1

    if is_end:
        if zone_type == "blocked":
            msg = f"Line {line_idx+1}: end_hub cannot be blocked."
            raise ParseError(msg)
        if map_obj.end_zone:
            msg = f"Line {line_idx+1}: Only one end_hub can be defined."
            raise ParseError(msg)
        map_obj.end_zone = name
        max_drones = -1

    map_obj.zones[name] = Zone(
        name, x, y, zone_type, color, max_drones, is_start, is_end
    )


def _parse_conn(
    map_obj: Map,
    seen_conns: Set[Tuple[str, str]],
    line_idx: int,
    z1: str,
    z2: str,
    metadata_str: Optional[str]
) -> None:
    if z1 == z2:
        msg = f"Line {line_idx+1}: Self-connection on zone '{z1}'."
        raise ParseError(msg)

    if z1 not in map_obj.zones:
        msg = f"Line {line_idx+1}: Connection unknown zone '{z1}'."
        raise ParseError(msg)
    if z2 not in map_obj.zones:
        msg = f"Line {line_idx+1}: Connection unknown zone '{z2}'."
        raise ParseError(msg)

    pair = tuple(sorted([z1, z2]))
    if pair in seen_conns:
        msg = f"Line {line_idx+1}: Duplicate connection '{z1}' and '{z2}'."
        raise ParseError(msg)
    seen_conns.add((pair[0], pair[1]))

    max_link_cap = 1
    if metadata_str is not None:
        metadata = parse_metadata(metadata_str, line_idx + 1)

        valid_keys = {"max_link_capacity"}
        unknown = set(metadata.keys()) - valid_keys
        if unknown:
            keys = ", ".join(sorted(unknown))
            msg = (f"Line {line_idx+1}: Unknown connection metadata "
                   f"key(s): {keys}. Valid keys: "
                   f"{', '.join(sorted(valid_keys))}.")
            raise ParseError(msg)

        if "max_link_capacity" in metadata:
            try:
                mlc = int(metadata["max_link_capacity"])
                if mlc <= 0:
                    raise ValueError()
                max_link_cap = mlc
            except ValueError:
                msg = (f"Line {line_idx+1}: max_link_capacity must be a "
                       "positive integer greater than 0.")
                raise ParseError(msg)

    map_obj.connections.append(Connection(z1, z2, max_link_cap))


def parse_map(file_path: str) -> Map:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    map_obj: Optional[Map] = None
    nb_drones_found = False
    seen_connections: Set[Tuple[str, str]] = set()
    seen_coords: Set[Tuple[int, int]] = set()

    zone_regex = re.compile(
        r'^(start_hub|end_hub|hub):\s+([^\s\-]+)\s+(-?\d+)\s+(-?\d+)'
        r'(?:\s*\[([^\[\]]*)\])?\s*$'
    )
    conn_regex = re.compile(
        r'^connection:\s+([^\s\-]+)-([^\s\-]+)(?:\s*\[([^\[\]]*)\])?\s*$'
    )

    for line_idx, line in enumerate(lines):
        comment_pos = line.find('#')
        if comment_pos != -1:
            line = line[:comment_pos]
        line = line.strip()

        if not line:
            continue

        if not nb_drones_found:
            m = re.match(r'^nb_drones:\s*([1-9]\d*)\s*$', line)
            if m:
                nb_drones = int(m.group(1))
                map_obj = Map(nb_drones)
                nb_drones_found = True
                continue
            else:
                if line.startswith("nb_drones:"):
                    msg = (
                        f"Line {line_idx+1}: nb_drones must be a "
                        "positive integer and greater than 0."
                    )
                else:
                    msg = (
                        f"Line {line_idx+1}: First line must be nb_drones. "
                        "It must be a positive integer and greater than 0."
                    )
                raise ParseError(msg)

        assert map_obj is not None

        zone_match = zone_regex.match(line)
        conn_match = conn_regex.match(line)

        if zone_match:
            _parse_zone(
                map_obj,
                seen_coords,
                line_idx,
                zone_match.group(1),
                zone_match.group(2),
                zone_match.group(3),
                zone_match.group(4),
                zone_match.group(5)
            )
        elif conn_match:
            _parse_conn(
                map_obj,
                seen_connections,
                line_idx,
                conn_match.group(1),
                conn_match.group(2),
                conn_match.group(3)
            )
        else:
            raise ParseError(f"Line {line_idx+1}: Invalid syntax.")

    if not map_obj:
        raise ParseError("File is empty or missing nb_drones.")

    if not map_obj.start_zone or not map_obj.end_zone:
        raise ParseError("Map must contain exactly one start_hub and end_hub.")

    return map_obj
