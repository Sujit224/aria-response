import json, random, uuid
import os

random.seed(42)

# Grid is 24 wide x 12 tall per floor
# Layout: 10 rooms on front row, 10 on back row, corridor in middle (rows 4-7)
# Exits: 3 on front wall (row 0), 3 on back wall (row 11)

GRID_W = 24
GRID_H = 12
BLOCKS = [
    {"name": "North Wing",    "block_code": "A"},
    {"name": "Central Wing",  "block_code": "B"},
    {"name": "South Wing",    "block_code": "C"},
]
FLOORS = 4
ROOMS_PER_SIDE = 10  # 10 front + 10 back = 20 rooms per floor
CORR_START = 4
CORR_END   = 7

def make_grid(front_exit_cols, back_exit_cols):
    """Build 24x12 grid for one floor.
    Rooms in rows 1-3 (front) and 8-10 (back).
    Corridor in rows 4-7.
    Exits punched through row 0 (front) and row 11 (back).
    Room dividers every 2 cols.
    """
    g = [[1]*GRID_W for _ in range(GRID_H)]

    # Corridor (fully walkable)
    for r in range(CORR_START, CORR_END+1):
        for c in range(1, GRID_W-1):
            g[r][c] = 0

    # Front rooms (rows 1-3) and back rooms (rows 8-10)
    room_cols = [1+i*2 for i in range(ROOMS_PER_SIDE)]  # [1,3,5,...,19]
    for rc in room_cols:
        if rc < GRID_W-1:
            for r in range(1, 4):   # front
                for dc in range(2):
                    if rc+dc < GRID_W-1:
                        g[r][rc+dc] = 0
            for r in range(8, 11):  # back
                for dc in range(2):
                    if rc+dc < GRID_W-1:
                        g[r][rc+dc] = 0

    # Doorways connecting rooms to corridor (row 4 and row 7)
    for rc in room_cols:
        if rc < GRID_W-1:
            g[CORR_START][rc] = 0   # front doorway
            g[CORR_END][rc]   = 0   # back doorway

    # Punch exits through front wall (row 0) and back wall (row 11)
    for c in front_exit_cols:
        g[0][c]  = 0
        g[1][c]  = 0   # connect to room row
    for c in back_exit_cols:
        g[11][c] = 0
        g[10][c] = 0

    return g

def make_pois(block_code, floor_level, floor_id, front_exit_cols, back_exit_cols, aid_coords):
    pois = []
    room_cols = [1+i*2 for i in range(ROOMS_PER_SIDE)]

    # Front rooms (rows 1-3 → centre y=2)
    for i, rc in enumerate(room_cols):
        rnum = f"{block_code}{floor_level}{str(i+1).zfill(2)}"
        pois.append({
            "id":           str(uuid.uuid4()),
            "floor_id":     floor_id,
            "name":         f"Room {rnum}",
            "type":         "room",
            "coord_x":      rc,
            "coord_y":      2,
            "is_safe_exit": False,
        })

    # Back rooms (rows 8-10 → centre y=9)
    for i, rc in enumerate(room_cols):
        rnum = f"{block_code}{floor_level}{str(i+11).zfill(2)}"
        pois.append({
            "id":           str(uuid.uuid4()),
            "floor_id":     floor_id,
            "name":         f"Room {rnum}",
            "type":         "room",
            "coord_x":      rc,
            "coord_y":      9,
            "is_safe_exit": False,
        })

    # Front exits (row 0)
    exit_names_front = ["Stairwell NW", "Stairwell NC", "Stairwell NE"]
    for i, c in enumerate(front_exit_cols):
        pois.append({
            "id":           str(uuid.uuid4()),
            "floor_id":     floor_id,
            "name":         exit_names_front[i],
            "type":         "exit",
            "coord_x":      c,
            "coord_y":      0,
            "is_safe_exit": True,
        })

    # Back exits (row 11)
    exit_names_back = ["Stairwell SW", "Stairwell SC", "Stairwell SE"]
    for i, c in enumerate(back_exit_cols):
        pois.append({
            "id":           str(uuid.uuid4()),
            "floor_id":     floor_id,
            "name":         exit_names_back[i],
            "type":         "exit",
            "coord_x":      c,
            "coord_y":      11,
            "is_safe_exit": True,
        })

    # Aid kits
    for idx, (ax, ay) in enumerate(aid_coords):
        pois.append({
            "id":           str(uuid.uuid4()),
            "floor_id":     floor_id,
            "name":         f"Aid Kit {chr(65+idx)}",
            "type":         "medical",
            "coord_x":      ax,
            "coord_y":      ay,
            "is_safe_exit": False,
        })

    return pois

# Fixed exit columns: evenly distributed (3 front, 3 back)
FRONT_EXITS = [3, 11, 19]
BACK_EXITS  = [3, 11, 19]

# Aid kit positions per floor (randomised corridor positions)
AID_KIT_POSITIONS_PER_FLOOR = [
    [(5, 5), (13, 5), (19, 4)],  # floor 1
    [(7, 6), (15, 5), (21, 6)],  # floor 2
    [(4, 4), (12, 6), (20, 5)],  # floor 3
    [(6, 5), (14, 4), (18, 6)],  # floor 4
]

# ── Build full hotel data ─────────────────────────────────────────
hotel_id = str(uuid.uuid4())

hotel = {
    "collection": "hotels",
    "doc_id": hotel_id,
    "data": {
        "id":         hotel_id,
        "name":       "Grand ARIA Hotel",
        "address":    "12 Convention Road, Mumbai 400001",
        "created_at": "2025-04-28T00:00:00Z",
    }
}

blocks_out = []
floors_out = []
pois_out   = []

for b in BLOCKS:
    block_id = str(uuid.uuid4())
    blocks_out.append({
        "collection": "blocks",
        "doc_id": block_id,
        "data": {
            "id":         block_id,
            "hotel_id":   hotel_id,
            "name":       b["name"],
            "block_code": b["block_code"],
        }
    })

    for fl in range(1, FLOORS+1):
        floor_id  = str(uuid.uuid4())
        aid_pos   = AID_KIT_POSITIONS_PER_FLOOR[fl-1]
        grid      = make_grid(FRONT_EXITS, BACK_EXITS)

        floors_out.append({
            "collection": "floors",
            "doc_id": floor_id,
            "data": {
                "id":          floor_id,
                "block_id":    block_id,
                "level":       fl,
                "grid_width":  GRID_W,
                "grid_height": GRID_H,
                "static_grid": grid,
            }
        })

        pois = make_pois(b["block_code"], fl, floor_id, FRONT_EXITS, BACK_EXITS, aid_pos)
        for p in pois:
            pois_out.append({
                "collection": "pois",
                "doc_id": p["id"],
                "data": p
            })

seed_data = {
    "hotel":  hotel,
    "blocks": blocks_out,
    "floors": floors_out,
    "pois":   pois_out,
    "summary": {
        "total_blocks": len(blocks_out),
        "total_floors": len(floors_out),
        "total_pois":   len(pois_out),
        "rooms_per_floor": 20,
        "exits_per_floor": 6,
        "aid_kits_per_floor": 3,
    }
}

out_path = os.path.join("scripts", "hotel_seed_firebase.json")
with open(out_path, "w") as f:
    json.dump(seed_data, f, indent=2)

print(f"Hotel ID:      {hotel_id}")
print(f"Blocks:        {len(blocks_out)}")
print(f"Floors:        {len(floors_out)}")
print(f"Total POIs:    {len(pois_out)}")
room_count = len([p for p in pois_out if p['data']['type']=='room'])
exit_count = len([p for p in pois_out if p['data']['is_safe_exit']])
aid_count  = len([p for p in pois_out if p['data']['type']=='medical'])
print(f"  Rooms:       {room_count}")
print(f"  Exits:       {exit_count}")
print(f"  Aid kits:    {aid_count}")
