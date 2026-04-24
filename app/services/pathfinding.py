import heapq
from typing import List, Tuple


def astar(
    grid: List[List[int]],
    start: Tuple[int, int],
    end: Tuple[int, int],
    blocked: List[Tuple[int, int]] = None,
) -> List[Tuple[int, int]]:
    """
    A* pathfinding on the hotel floor's static_grid.

    grid:    2D matrix where 0 = walkable, 1 = wall
    start:   (x, y) guest's current grid position
    end:     (x, y) nearest safe exit grid position
    blocked: dynamic hazard nodes [[x,y],...] from EmergencyAlert
             these are treated as walls at runtime without modifying the DB grid

    Returns: list of (x, y) tuples representing the path, [] if no path found.
    """
    if not grid or not grid[0]:
        return []

    rows = len(grid)
    cols = len(grid[0])
    blocked_set = set(map(tuple, blocked or []))

    def in_bounds(x, y):
        return 0 <= x < cols and 0 <= y < rows

    def walkable(x, y):
        if not in_bounds(x, y):
            return False
        if grid[y][x] == 1:         # static wall
            return False
        if (x, y) in blocked_set:   # dynamic hazard
            return False
        return True

    def heuristic(a, b):
        # Manhattan distance — appropriate for grid movement
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # Priority queue: (f_score, (x, y))
    open_heap = []
    heapq.heappush(open_heap, (0, start))

    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, end)}

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current == end:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        cx, cy = current
        # 4-directional movement (no diagonals in corridor grid)
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)

            if not walkable(nx, ny):
                continue

            tentative_g = g_score[current] + 1

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                heapq.heappush(open_heap, (f_score[neighbor], neighbor))

    # No path found — return direct line as fallback
    return [start, end]


def reroute(
    grid: List[List[int]],
    guest_pos: Tuple[int, int],
    exit_pos: Tuple[int, int],
    blocked_nodes: List[List[int]],
) -> List[List[int]]:
    """
    Called when a new EmergencyAlert is created (fire spreads, new hazard).
    Re-runs A* with the updated blocked_nodes and returns
    the path as [[x,y],...] ready for the PATH_UPDATE WebSocket event.
    """
    blocked = [tuple(n) for n in blocked_nodes]
    path = astar(grid, guest_pos, exit_pos, blocked)
    return [[p[0], p[1]] for p in path]