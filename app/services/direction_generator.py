"""
direction_generator.py
──────────────────────
Converts a raw A* path (list of (x,y) grid coords) into
human-readable turn-by-turn evacuation directions.

Uses POI names to anchor references ("Pass Room 204, Room 202…")
and cardinal directions derived from coordinate deltas.
"""

from typing import List, Tuple, Dict


def _bearing(dx: int, dy: int) -> str:
    """Convert dx/dy delta into a cardinal direction label for the UI."""
    if abs(dx) >= abs(dy):
        return "RIGHT" if dx > 0 else "LEFT"
    return "DOWN corridor" if dy > 0 else "UP corridor"


def _compress(path: List[Tuple[int, int]]) -> List[Tuple[str, int, int, int, int]]:
    """
    Merge consecutive collinear steps into single segments.
    Returns list of (direction, start_x, start_y, end_x, end_y).
    """
    if len(path) < 2:
        return []
    segments = []
    sx, sy = path[0]
    dx = path[1][0] - path[0][0]
    dy = path[1][1] - path[0][1]
    bearing = _bearing(dx, dy)

    for i in range(2, len(path)):
        ndx = path[i][0] - path[i - 1][0]
        ndy = path[i][1] - path[i - 1][1]
        new_bearing = _bearing(ndx, ndy)
        if new_bearing != bearing:
            segments.append((bearing, sx, sy, path[i - 1][0], path[i - 1][1]))
            sx, sy = path[i - 1]
            bearing = new_bearing
        dx, dy = ndx, ndy

    segments.append((bearing, sx, sy, path[-1][0], path[-1][1]))
    return segments


def _rooms_along(
    start_x: int, start_y: int, end_x: int, end_y: int,
    pois: List[Dict], max_rooms: int = 3,
) -> List[str]:
    """
    Find room POI names whose coords lie along the segment's corridor.
    Sorted by proximity to the start of the segment.
    """
    rooms = []
    for p in pois:
        if p.get("type") != "room":
            continue
        px, py = p["coord_x"], p["coord_y"]

        # Must be roughly on the same row or column as the segment
        if start_x == end_x:  # vertical movement
            if px == start_x and min(start_y, end_y) < py < max(start_y, end_y):
                rooms.append((abs(py - start_y), p["name"]))
        else:  # horizontal movement
            if py == start_y and min(start_x, end_x) < px < max(start_x, end_x):
                rooms.append((abs(px - start_x), p["name"]))

    rooms.sort(key=lambda r: r[0])
    return [r[1] for r in rooms[:max_rooms]]


def generate_directions(
    path: List[Tuple[int, int]],
    pois: List[Dict],
    exit_name: str,
    origin_room: str,
) -> List[str]:
    """
    Public API — returns a list of step strings matching the image format:
      1. Leave room, turn LEFT down corridor
      2. Pass rooms 410, 408 — keep going west
      3. Enter stairwell door at end of hall
      4. Descend to ground floor, exit onto Main St
    """
    steps: List[str] = []

    if len(path) < 2:
        steps.append(f"Proceed directly to {exit_name}.")
        return steps

    segments = _compress(path)

    for i, (direction, sx, sy, ex, ey) in enumerate(segments):
        rooms_along = _rooms_along(sx, sy, ex, ey, pois)
        is_last = i == len(segments) - 1

        if i == 0:
            step = f"Leave {origin_room}, turn {direction} down corridor"
        elif is_last:
            step = f"Enter {exit_name} door at end of hall"
        else:
            if rooms_along:
                label = ", ".join(rooms_along)
                step = f"Continue {direction} — pass {label}"
            else:
                step = f"Continue {direction}"

        steps.append(step)

    steps.append("Descend stairwell to ground floor and exit the building")
    return steps


def format_distance(path: List[Tuple[int, int]], cell_meters: float = 2.5) -> str:
    """Estimate distance in metres (each grid cell ≈ 2.5 m by default)."""
    if len(path) < 2:
        return "0 m"
    dist = (len(path) - 1) * cell_meters
    return f"{int(dist)} m"
