# Rail Placer Path Rules Analysis
## File: `rail_placer_working_v1dot3_with_choices.py` (2824 lines)
## Date: 2026-03-24

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Path-Tracing Algorithm](#2-path-tracing-algorithm)
3. [Direction Detection Logic](#3-direction-detection-logic)
4. [Rail Type Selection](#4-rail-type-selection)
5. [Legal Path Configurations](#5-legal-path-configurations)
6. [Illegal Path Configurations](#6-illegal-path-configurations)
7. [Turn (Diagonal) Handling](#7-turn-diagonal-handling)
8. [Elevation Change Handling](#8-elevation-change-handling)
9. [Turn-to-Incline Proximity](#9-turn-to-incline-proximity)
10. [Wool Block Types](#10-wool-block-types)
11. [Block Metadata Dictionary](#11-block-metadata-dictionary)
12. [Failure Modes and Crash Scenarios](#12-failure-modes-and-crash-scenarios)

---

## 1. Architecture Overview

The plugin operates in a **sequential pipeline**:

```
read_selection() -> start_direction() -> loop_operation() -> set_rails() -> set_ballast() -> find_solid_ground() -> place_supports()
```

**Key Functions (with line numbers):**
| Function | Lines | Purpose |
|---|---|---|
| `_run_operation` | 258-291 | Entry point; initializes state, calls pipeline |
| `read_selection` / `get_coordinates` | 301-338 | Scans selection box for wool blocks |
| `start_direction` | 348-394 | Finds next wool block in 3x3x3 neighborhood |
| `rail_direction` | 467-490 | Computes dx/dy/dz differential between current and next block |
| `set_roadbase` | 499-757 | Core path-following: determines direction, places cobblestone roadbed, records metadata |
| `b2b_test` | 396-465 | Detects back-to-back diagonal (turn) blocks |
| `loop_operation` | 129-198 | Main loop that iterates through the entire path |
| `set_rails` | 760-866 | Places rail blocks based on direction metadata |
| `set_ballast` | 880-1721 | Places stair/air blocks on sides of roadbed |
| `find_solid_ground` | 1728-2062 | Tests for air/water beneath all placed blocks |
| `place_supports` | 2075-2669 | Places cribbing, underpinning, and support pillars |

---

## 2. Path-Tracing Algorithm

### How the code follows the wool path:

**Step 1: Initial Selection (lines 310-338)**
- User selects a single block (the starting wool block) in Amulet's selection box.
- `get_coordinates()` iterates every block in the selection, checks if it is pink/orange/purple wool.
- The starting block is **replaced with cobblestone** immediately (line 337).

**Step 2: Find Next Block - `start_direction()` (lines 348-394)**
- From the current block at `(x, y, z)`, the code searches a **3x3x3 cube** (x-1 to x+1, y-1 to y+1, z-1 to z+1).
- It skips any block already in the `placed_blocks` list (line 370-371).
- It checks each block's `blockstate` for pink wool, orange wool, or purple wool.
- All found wool blocks are appended to `second_block_coordinates` with `value=1`.
- **CRITICAL**: This 3x3x3 search means the algorithm can find blocks that are:
  - Adjacent on a cardinal axis (N/S/E/W) -- distance 1
  - Diagonally adjacent on the same Y level -- distance sqrt(2)
  - One block up or down AND one block in a cardinal direction -- distance sqrt(2)
  - One block up or down AND diagonal -- distance sqrt(3) (corner of the cube)

**Step 3: Compute Direction - `rail_direction()` (lines 467-490)**
- Calculates `diff_x`, `diff_y`, `diff_z` between current block and found next block(s).
- The `value` field records how many next-blocks were found (1 = straight, 2 = turn).
- Returns `block_differential` list.

**Step 4: Main Loop - `loop_operation()` (lines 129-177)**
- Calls `rail_direction()` to get the differential.
- Calls `set_roadbase()` to place the roadbed and determine direction metadata.
- If a diagonal (turn) was detected, calls `b2b_test()` to check for consecutive diagonals.
- Gets `continue_coordinates` from `set_roadbase()` -- this is where to resume searching.
- Calls `start_direction()` again from the continue point.
- Loop continues until no more wool blocks are found.

**Step 5: Termination (lines 170-177)**
- If `start_direction()` returns no blocks with `value == 1`, the loop ends.
- After the loop, `set_rails()`, `set_ballast()`, etc. are called to finish.

---

## 3. Direction Detection Logic

### Straight Paths (`len(block_differential) == 1`) -- Lines 516-606

The `determine_direction()` inner function at line 517 maps dx/dy/dz differentials to named directions:

| dx | dy | dz | Direction | Facing | Rail Type |
|---|---|---|---|---|---|
| +1 | 0 | 0 | `east_west` | `east` | Straight E-W |
| -1 | 0 | 0 | `east_west` | `west` | Straight E-W |
| 0 | 0 | +1 | `north_south` | `south` | Straight N-S |
| 0 | 0 | -1 | `north_south` | `north` | Straight N-S |
| +1 | +1 | 0 | `east_ascending` | `east` | Ascending E |
| -1 | +1 | 0 | `east_descending` | `west` | Descending E (ascending W) |
| 0 | +1 | -1 | `north_ascending` | `north` | Ascending N |
| 0 | +1 | +1 | `north_descending` | `south` | Descending N (ascending S) |
| +1 | -1 | 0 | `east_descending` | `east` | Descending E |
| -1 | -1 | 0 | `east_ascending` | `west` | Ascending E (descending W) |
| 0 | -1 | -1 | `north_descending` | `north` | Descending N |
| 0 | -1 | +1 | `north_ascending` | `south` | Ascending N (descending S) |

**Key observation**: Elevation changes (`dy != 0`) are ONLY valid combined with a SINGLE cardinal axis change (`dx` or `dz`, never both). This is enforced by the if/elif chain structure at lines 531-544.

### Diagonal/Turn Paths (`len(block_differential) == 2`) -- Lines 608-757

When TWO next-blocks are found, the code enters the turn-handling logic. The `determine_direction()` at line 623 matches **exact dx/dy/dz pairs** for the two found blocks against 8 hardcoded patterns:

| Pattern (block1 dx,dy,dz + block2 dx,dy,dz) | Direction Name | d1 | d2 (corner) | d3 |
|---|---|---|---|---|
| (-1,0,1) + (0,0,1) | `west-southwest` | north_south | north_west | east_west |
| (-1,0,0) + (-1,0,1) | `south-southwest` | east_west | south_east | north_south |
| (0,0,1) + (1,0,1) | `east-southeast` | north_south | north_east | east_west |
| (1,0,0) + (1,0,1) | `south-southeast` | east_west | south_west | north_south |
| (0,0,-1) + (1,0,-1) | `east-northeast` | north_south | south_east | east_west |
| (1,0,-1) + (1,0,0) | `north-northeast` | east_west | north_west | north_south |
| (-1,0,-1) + (-1,0,0) | `north-northwest` | east_west | north_east | north_south |
| (-1,0,-1) + (0,0,-1) | `west-northwest` | north_south | south_west | east_west |

**CRITICAL**: Every turn pattern has `dy == 0` for BOTH blocks. There is NO pattern that combines a turn with an elevation change. This is the root cause of the turn-near-incline restriction.

Each turn produces THREE blocks in `placed_blocks`:
1. **d1** = the cardinal direction entering the turn (e.g., `north_south`)
2. **d2** = the diagonal corner rail (e.g., `north_west`, `south_east`, etc.)
3. **d3** = the cardinal direction exiting the turn (e.g., `east_west`)

---

## 4. Rail Type Selection

### `set_rails()` (Lines 760-866)

Rail blocks are placed at `y+1` above each roadbed block. The direction stored in `placed_blocks[i]['direction']` is used as the key to select the rail type.

**Available rail directions (lines 795-806):**
```python
rail_directions = {
    'north_south': rail_north_south,           # IntTag(0)
    'north_ascending': rail_north_ascending,   # IntTag(4)
    'north_descending': rail_north_descending, # IntTag(5)
    'east_west': rail_east_west,               # IntTag(1)
    'east_ascending': rail_east_ascending,     # IntTag(2)
    'east_descending': rail_east_descending,   # IntTag(3)
    'north_west': rail_north_west,             # IntTag(8)
    'north_east': rail_north_east,             # IntTag(9)
    'south_west': rail_south_west,             # IntTag(7)
    'south_east': rail_south_east              # IntTag(6)
}
```

**Powered rail restriction (lines 828-833):**
```python
invalid_powered_rail_direction = {
    'north_west', 'north_east', 'south_west', 'south_east'
}
```
Curved rails CANNOT be powered rails. Only straight and ascending rails can be powered. This matches Minecraft's game mechanics -- golden rails (powered rails) only come in straight variants.

**Air clearance (lines 852-862):**
- Every rail gets `air` placed at `y+2` (one block above the rail).
- Ascending/descending rails get ADDITIONAL `air` at `y+3` (lines 853-854, 861-862).

**Powered rail frequency (line 844):**
```python
if placed_rails_iter % 16 == 16:  # BUG: This condition is NEVER true (x % 16 is 0-15)
```
This is a **bug** -- the modulo check `% 16 == 16` can never be true, so powered rails are never automatically placed by the frequency logic. The `power_choice` dropdown controls whether ascending rails use powered rails instead.

---

## 5. Legal Path Configurations

### LEGAL: Straight Cardinal Paths
- **North-South**: Wool blocks in a line along the Z axis (same X, same Y, Z changes by +/-1 each step)
- **East-West**: Wool blocks in a line along the X axis (same Z, same Y, X changes by +/-1 each step)
- Minimum: 2 wool blocks needed (start + at least one more)

### LEGAL: Ascending/Descending Paths
- **North Ascending**: Each block is at (same X, Y+1, Z-1) relative to previous
- **North Descending**: Each block is at (same X, Y-1, Z-1) relative to previous
- **East Ascending**: Each block is at (X+1, Y+1, same Z) relative to previous
- **East Descending**: Each block is at (X+1, Y-1, same Z) relative to previous
- And their reverses (south/west variants)
- **Rule**: Only ONE block of elevation change per step (dy = +/-1), combined with exactly ONE cardinal direction (dx or dz = +/-1, not both)

### LEGAL: 90-Degree Turns (on flat ground)
- A turn is a 2-block diagonal step where the path changes from one cardinal direction to a perpendicular one.
- The 8 legal turn patterns are enumerated in Section 3 above.
- **All turns must be on flat ground (dy == 0 for both blocks in the turn)**
- Turns consume 3 blocks in the placed_blocks list (entering cardinal, corner, exiting cardinal)

### LEGAL: Back-to-Back Turns
- Two consecutive turns (e.g., S-shaped path) are handled by `b2b_test()` (lines 396-465).
- When detected, the middle block's direction is updated to reflect the connecting direction.
- The `b2b` flag is set to `True` on the connecting block.

### LEGAL: Wool Block Types
- **Pink Wool** (`use_case: 'standard_path'`): Normal rail path
- **Orange Wool** (`use_case: 'overpass'`): Rail path that skips cribbing (for overpasses)
- **Purple Wool** (`use_case: 'drop_pillar'`): Marks locations for support pillar placement

---

## 6. Illegal Path Configurations

### ILLEGAL #1: Vertically Stacked Wool Blocks (Two blocks directly above/below each other)

**Why it crashes**: When the `start_direction()` 3x3x3 search finds a block directly above or below (dx=0, dy=+/-1, dz=0), the `determine_direction()` function at lines 531-544 has no matching case.

Looking at the logic:
```python
if dy > 0:
    if dx > 0: return 'east_ascending', ...
    elif dx < 0: return 'east_descending', ...
    elif dz < 0: return 'north_ascending', ...
    else: return 'north_descending', ...  # dz >= 0 case
```

When dx=0, dy=1, dz=0: the code falls through to `else: return 'north_descending', 'south', 0, 1, 0`. This returns `dz=0` which means the next block placement at `base_x + dx, base_y + dy, base_z + dz` = `base_x + 0, base_y + 1, base_z + 0` -- placing the roadbed block ON TOP of the current block. This creates an infinite loop or corrupted path because:
1. The "continue" coordinates point to the same XZ location at Y+1
2. The `start_direction()` search from Y+1 may find the original block at Y (already in placed_blocks, so skipped) and no new blocks
3. OR it may find a block at Y+2 and repeat the problem

**The actual crash**: The direction `north_descending` with `dz=0` means the rail type mapping works, but the roadbed placement overwrites the current block, and path-following breaks because the "next" block is directly above with no forward movement. The loop at line 170 checks `if any(d['value'] == 1 for d in second_block_coordinates)` -- if no new wool is found, it terminates, but if there ARE more wool blocks nearby, it can get confused.

**Lines involved**: 531-544 (determine_direction), 579 (block placement), 605 (continue coordinates)

### ILLEGAL #2: True Diagonal Path (X and Z both change, no turn pattern)

If wool blocks are placed in a pure diagonal line (e.g., each block at X+1, Z+1 from previous), the `start_direction()` search would find this block. However, `len(block_differential)` would be 1, and the `determine_direction()` function only handles cases where EITHER dx or dz is non-zero (not both simultaneously when dy=0). This would cause an error because none of the conditions at lines 541-544 would match (they check `dx > 0`, `dx < 0`, `dz > 0`, `dz < 0` sequentially, so dx=1,dz=1 would return `east_west` with facing `east` -- which is technically wrong but wouldn't crash). The resulting rail would be incorrectly oriented.

### ILLEGAL #3: Turn Combined with Elevation Change

**Why it's illegal**: The 8 turn patterns at lines 636-719 ALL have `y1 == 0` and `y2 == 0`. There are NO patterns that include a dy component. If the two found blocks in a turn have any dy != 0, NONE of the `elif` conditions will match, and `determine_direction()` will either:
- Return `None` (causing an unpack error at line 720)
- Fall through without returning (same crash)

**Lines involved**: 636-719 (all 8 turn pattern matches require y1==0, y2==0)

### ILLEGAL #4: Turn Within One Block of an Incline

**Why it's illegal**: This is a GEOMETRIC constraint, not explicitly validated in code. Here's what happens:

When an ascending block is placed (e.g., at iteration N), the block at iteration N has `direction = 'north_ascending'`. The `set_roadbase()` function sets `recursive = True` (line 585) when `dy > 0`.

On the NEXT iteration (N+1), if that next block starts a turn (two blocks found), the code enters the `len(block_differential) == 2` branch. But the problem is more fundamental:

The `start_direction()` search at the top of the ascending block is at coordinates `(x, y+1, z-1)` (for north ascending). The 3x3x3 search cube from here will search Y, Y+1, Y+2 and the surrounding XZ area. If a turn's wool blocks are placed at this level, they would need to be at the SAME Y as the top of the incline. But the turn patterns (section 3) all require `dy == 0` for both blocks.

The issue is that the block JUST BEFORE the turn still has an ascending direction, and the code at lines 731-736 tries to handle the `recursive` flag by updating the last placed block's direction. But this creates an inconsistency: the placed_blocks entry gets its direction overwritten to the turn's `d1`, losing the ascending information. The rail placement later (set_rails) would then place a flat rail where an ascending rail was needed, or vice versa.

Additionally, the `set_ballast()` function (line 966 onwards) tests `origin_direction == direction` to determine "happy path" vs "complex path". An ascending block followed immediately by a turn creates a mismatch that the ballast logic doesn't handle, potentially causing index-out-of-bounds errors when accessing `placed_blocks[placed_ballast_iter + 1]` at turn corners.

**Minimum safe distance**: At least 2 blocks of flat (cardinal) path between an incline and a turn. This gives the recursive flag time to reset (line 595: `recursive = False` when `dy <= 0` and previous was not recursive) and ensures the direction metadata is consistent.

### ILLEGAL #5: Path Branching (More than 2 next-blocks found)

The code at line 477 handles `len(second_block_coordinates) >= 1` and at line 479 takes `last_two_blocks = second_block_coordinates[-2:]`. If 3+ wool blocks are in the 3x3x3 search area, only the last 2 are used. This means:
- The third (or more) blocks are silently ignored
- The two blocks selected may not be the correct turn pair
- This can cause incorrect direction detection or crashes

### ILLEGAL #6: Gap of More Than 1 Block

The 3x3x3 search cube only reaches 1 block in each direction. If two wool blocks are more than 1 block apart on any axis, the path-tracing will terminate (no next block found). This is not a "crash" but the path will be incomplete.

---

## 7. Turn (Diagonal) Handling -- Detailed

### The Turn Geometry

A 90-degree turn in Minecraft rail terms requires THREE consecutive blocks:
1. **Approach block**: straight rail in the incoming direction
2. **Corner block**: curved rail connecting the two directions
3. **Exit block**: straight rail in the outgoing direction

In the wool path, this manifests as the current block having TWO adjacent wool blocks in its 3x3x3 neighborhood (after excluding already-placed blocks). These two blocks define:
- **Block 1** (closer to the approach): offset from current block
- **Block 2** (the exit point): offset from current block

### The 8 Turn Patterns (Lines 636-719)

Each pattern is a specific pair of (dx1,dy1,dz1) + (dx2,dy2,dz2):

**Pattern: west-southwest** (line 636-649)
```
Current -> Block1 at (-1,0,+1) then -> Block2 at (0,0,+1)  [REVERSED to (0,0,+1) then (-1,0,+1)]
Path: going south (Z+), turning to go west (X-)
Rails: N-S straight -> NW curve -> E-W straight
```

**Pattern: south-southwest** (line 650-656)
```
Current -> Block1 at (-1,0,0) then -> Block2 at (-1,0,+1)
Path: going west (X-), turning to go south (Z+)
Rails: E-W straight -> SE curve -> N-S straight
```

**Pattern: east-southeast** (line 657-663)
```
Current -> Block1 at (0,0,+1) then -> Block2 at (+1,0,+1)
Path: going south (Z+), turning to go east (X+)
Rails: N-S straight -> NE curve -> E-W straight
```

**Pattern: south-southeast** (line 664-670)
```
Current -> Block1 at (+1,0,0) then -> Block2 at (+1,0,+1)
Path: going east (X+), turning to go south (Z+)
Rails: E-W straight -> SW curve -> N-S straight
```

**Pattern: east-northeast** (line 671-677)
```
Current -> Block1 at (0,0,-1) then -> Block2 at (+1,0,-1)
Path: going north (Z-), turning to go east (X+)
Rails: N-S straight -> SE curve -> E-W straight
```

**Pattern: north-northeast** (line 678-691)
```
Current -> Block1 at (+1,0,-1) then -> Block2 at (+1,0,0)  [REVERSED to (+1,0,0) then (+1,0,-1)]
Path: going east (X+), turning to go north (Z-)
Rails: E-W straight -> NW curve -> N-S straight
```

**Pattern: north-northwest** (line 692-705)
```
Current -> Block1 at (-1,0,-1) then -> Block2 at (-1,0,0)  [REVERSED to (-1,0,0) then (-1,0,-1)]
Path: going west (X-), turning to go north (Z-)
Rails: E-W straight -> NE curve -> N-S straight
```

**Pattern: west-northwest** (line 706-719)
```
Current -> Block1 at (-1,0,-1) then -> Block2 at (0,0,-1)  [REVERSED to (0,0,-1) then (-1,0,-1)]
Path: going north (Z-), turning to go west (X-)
Rails: N-S straight -> SW curve -> E-W straight
```

### Note on Block Order Reversal
Some patterns (lines 637, 679, 693, 707) reverse the order of the two blocks before processing. This ensures the "approach" block is always processed first and the "exit" block second, regardless of the order `start_direction()` found them.

### Back-to-Back Turn Detection -- `b2b_test()` (Lines 396-465)

After each turn is processed, `b2b_test()` checks the MIDDLE block of the turn (the corner block) for additional adjacent wool/cobblestone blocks. If found, it means another turn follows immediately.

When a b2b is detected, the last block in `placed_blocks` has its direction UPDATED (not appended) to the **reverse** of the previous block's direction:
- `north_west` -> updates to `south_east` (line 450)
- `north_east` -> updates to `south_west` (line 454)
- `south_west` -> updates to `north_east` (line 459)
- `south_east` -> updates to `north_west` (line 464)

The `b2b` flag is set to `True` and `state` is set to `'diagonal'`.

---

## 8. Elevation Change Handling -- Detailed

### Ascending Path Mechanics (Lines 581-598)

When `dy > 0` (going up):
1. The PREVIOUS block's direction is retroactively updated to the ascending variant (line 583):
   ```python
   placed_blocks[-1] = {..., 'direction': direction, ...}  # e.g., 'north_ascending'
   ```
2. The current block is appended with the same ascending direction (line 584).
3. `recursive = True` is set (line 585) -- this is a flag that tells the NEXT iteration that an elevation change just happened.

When `dy <= 0` on the NEXT iteration and `recursive == True` (lines 588-595):
1. The last placed block is overwritten with the current flat direction (line 591).
2. `recursive = False` is reset (line 595).
3. This effectively creates the transition: ascending -> flat.

### The "Recursive" Flag Purpose
The `recursive` flag handles the fact that Minecraft ascending rails need TWO blocks:
- The LOWER block gets the ascending rail
- The UPPER block is where the cart arrives at the new elevation

When entering an ascending section, the code needs to retroactively mark the previous block as ascending. The `recursive` flag prevents double-processing on the next iteration.

### Descending Path Mechanics
Descending (`dy < 0`) is handled symmetrically. The direction names like `east_descending` or `north_descending` map to the appropriate rail_direction IntTag values.

### Air Clearance for Ascending Rails (Lines 853-854, 861-862)
Ascending/descending rails get an EXTRA air block above them (`y+3` in addition to the standard `y+2`). This accommodates the visual height of the ascending rail plus minecart/rider.

---

## 9. Turn-to-Incline Proximity -- Detailed Analysis

### Why It Fails

There is **no explicit validation** in the code that checks for turns near inclines. The failure is emergent from how the code processes blocks:

**Scenario: Ascending immediately followed by a turn**

1. Block N: ascending block. `recursive = True`. Direction = `north_ascending`.
2. Block N+1: at the top of the incline. The `start_direction()` 3x3x3 search finds TWO wool blocks (the turn pattern).
3. Code enters `len(block_differential) == 2` branch (line 608).
4. At line 731, `recursive == True`, so placed_blocks[-1] gets its direction overwritten to `d1` of the turn.
5. But placed_blocks[-1] is the TOP of the incline -- it was supposed to keep its ascending direction!
6. Now the rail placement (set_rails) will place a flat rail where an ascending rail was needed.

**Even worse**: The turn pattern matching (lines 636-719) requires `y1 == 0` and `y2 == 0`. If the turn blocks are at the same Y as the top of the incline (which they would be if placed right after ascending), the dy values in block_differential WILL be 0. But the issue is that the PREVIOUS block's metadata gets corrupted.

**Scenario: Turn immediately followed by ascending**

1. Turn processes 3 blocks (approach, corner, exit).
2. The exit block is the new "current" for the next iteration.
3. `start_direction()` finds the next wool block, which is one block UP.
4. `rail_direction()` returns `len(block_differential) == 1` with `dy == 1`.
5. Code enters `len(block_differential) == 1` branch.
6. The ascending logic updates placed_blocks[-1] (the turn exit block) to an ascending direction.
7. But the turn exit block was supposed to be a straight cardinal rail!
8. The `set_ballast()` function later sees inconsistent direction/origin_direction and may crash.

### Minimum Buffer Required

Based on the code structure, you need at least **2 flat cardinal blocks** between any turn and any incline:
1. One block to "absorb" the turn's exit direction (d3)
2. One block that can safely be retroactively changed to ascending

This ensures:
- The `recursive` flag is properly reset before a turn
- The turn's d1/d2/d3 sequence is not corrupted by ascending rewrites
- The `set_ballast()` function's `origin_direction == direction` test works correctly

---

## 10. Wool Block Types

### Three Types (Lines 324-333)

| Block | Blockstate | use_case | Purpose |
|---|---|---|---|
| Pink Wool | `universal_minecraft:wool[color=pink]` | `standard_path` | Normal rail path |
| Orange Wool | `universal_minecraft:wool[color=orange]` | `overpass` | Path over existing structures; skips cribbing |
| Purple Wool | `universal_minecraft:wool[color=purple]` | `drop_pillar` | Marks support pillar placement locations |

### Behavior Differences

- **Pink**: Full treatment -- roadbed, rails, ballast, cribbing, underpinning
- **Orange**: Roadbed and rails placed, but support detection treats it as "always floating" (line 2221: `any(use_case == 'overpass' ...)` triggers Air_Bridge span type regardless of actual ground contact)
- **Purple**: Roadbed and rails placed, AND coordinates are added to `support_locations` list (line 2218) for pillar placement

---

## 11. Block Metadata Dictionary

Each entry in `placed_blocks` contains these fields:

| Field | Type | Purpose |
|---|---|---|
| `x`, `y`, `z` | int | World coordinates of the roadbed block |
| `count` | int | Sequential iteration number |
| `direction` | string | Rail direction to place (e.g., `north_south`, `east_ascending`, `north_west`) |
| `origin_direction` | string | The composite direction name (e.g., `north-northeast` for turns) |
| `facing` | string | Cardinal facing for ballast inner/outer determination |
| `state` | string | `'cardinal'` for straight, `'corner'` for turn midpoint, `'diagonal'` for b2b |
| `b2b` | bool | Whether this block is part of a back-to-back turn sequence |
| `use_case` | string | `'standard_path'`, `'overpass'`, or `'drop_pillar'` |

### Direction vs Origin_Direction

- **`direction`**: The specific rail type to place (maps directly to `rail_directions` dict). For turns, this cycles through d1/d2/d3.
- **`origin_direction`**: The turn's composite name (e.g., `'north-northeast'`). For straight paths, same as `direction`. Used by ballast logic to determine which of the 8 turn patterns to apply.

### State Values

- `'cardinal'`: Block on a straight section or the first/last block of a turn
- `'corner'`: The middle block of a turn (gets a curved rail)
- `'diagonal'`: Block in a back-to-back turn sequence (modified by b2b_test)

---

## 12. Failure Modes and Crash Scenarios

### Crash #1: Vertical Stack (dx=0, dy!=0, dz=0)
- **Trigger**: Two wool blocks directly above/below each other with no horizontal offset
- **Mechanism**: `determine_direction()` returns a direction with dz=0 and dy=1, causing the "next" block to be placed at the same XZ as current. Path-following loops or terminates unexpectedly.
- **Lines**: 531-544

### Crash #2: Turn with Elevation
- **Trigger**: Turn pattern blocks at different Y levels
- **Mechanism**: None of the 8 turn patterns (lines 636-719) match because they all require y1==0 and y2==0
- **Result**: `determine_direction()` returns `None` or doesn't return, causing unpack error at line 720
- **Lines**: 636-719, 720

### Crash #3: Turn Adjacent to Incline
- **Trigger**: Turn within 1 block of an ascending/descending section
- **Mechanism**: `recursive` flag corruption or direction metadata overwrite (see Section 9)
- **Result**: Incorrect rails placed, possible index errors in ballast function
- **Lines**: 583-595, 731-736

### Crash #4: Ambiguous Neighborhood
- **Trigger**: Multiple wool blocks in the 3x3x3 search area that don't form a recognized pattern
- **Mechanism**: More than 2 blocks found, only last 2 used; or 2 blocks found that don't match any of the 8 turn patterns
- **Result**: `determine_direction()` doesn't match any case, returns None
- **Lines**: 479, 636-719

### Crash #5: Single Block Path
- **Trigger**: Only one wool block selected with no adjacent wool blocks
- **Mechanism**: `start_direction()` returns empty list, `loop_operation()` tries to proceed
- **Lines**: 166-177

### Non-Crash Issues

- **Powered rail bug**: `% 16 == 16` is never true (line 844). Automatic powered rail placement doesn't work.
- **Bedrock stair limitation**: Corner stairs are replaced with air blocks (lines 924-931) because Bedrock can't handle programmatic diagonal stair placement.

---

## Summary: Complete Rule Catalog

### MUST DO (Legal Configurations)
1. Path blocks must be within 1 block of each other on ALL axes (3x3x3 neighborhood)
2. Straight paths: dx OR dz changes by exactly 1, dy=0
3. Ascending/descending: exactly ONE of dx/dz changes by 1, AND dy changes by exactly 1
4. Turns: exactly TWO next-blocks found, both at dy=0, matching one of 8 hardcoded patterns
5. At least 2 flat blocks between any turn and any incline
6. Start block must be user-selected in the Amulet selection box
7. Path must use pink, orange, or purple wool blocks

### MUST NOT DO (Illegal Configurations)
1. **No vertical stacking**: Never place wool blocks directly above/below with no horizontal offset
2. **No diagonal-only paths**: Never place wool in a pure diagonal line (both dx and dz non-zero without forming a turn pattern)
3. **No turns with elevation**: Never place turn-pattern blocks at different Y levels
4. **No incline adjacent to turn**: Never start ascending/descending within 1 block of a turn
5. **No gaps**: Never leave more than 1 block between consecutive path blocks
6. **No branches**: Never place 3+ wool blocks adjacent to a single path block (only the last 2 are processed)
7. **No powered curved rails**: Curved rail positions will never get powered rails (Minecraft limitation, enforced at line 828-833)
