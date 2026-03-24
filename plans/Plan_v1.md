# Implementation Plan: Spline Rail Path Placer Plugin
## Version 1.0

---

### Context

Placing hundreds of pink wool blocks manually to define rail paths in Amulet is tedious. This plugin lets the user place just a few colored wool markers (start=lime, end=red, control=blue), then computes a smooth 3D Catmull-Rom spline through them and fills the path with pink wool automatically. It also clears air above and beside the path for minecart clearance. The output feeds directly into the existing `rail_placer_working_v1dot3_with_choices.py` plugin.

---

### File to Create

**`/data/ClaudeCodeProjects/Amulet-Plugins/spline_rail_path_placer_v1.py`** — single file, matching project convention.

---

### Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Spline algorithm | Catmull-Rom (numpy only) | Passes through points, tension control, no scipy needed |
| Control point ordering | Nearest-neighbor from start | Simple, works for path-like layouts |
| Marker colors | Lime=start, Red=end, Blue=control | Distinct from rail placer's pink/orange/purple |
| Clearance model | Above + sides, never below | Preserves terrain floor |
| Path topology | Single path (1 start, 1 end) | User runs plugin multiple times for branches |
| Gap filling | 3D Bresenham between samples | Ensures connected voxel path |

---

### Class Structure

```python
class SplineRailPathPlacer(wx.Panel, DefaultOperationUI):

    # --- Constants ---
    WOOL_COLOR_MAP = {
        "lime_wool": ("lime", "lime_wool"),     # (universal_color, platform_block_name)
        "red_wool": ("red", "red_wool"),
        "blue_wool": ("blue", "blue_wool"),
        "pink_wool": ("pink", "pink_wool"),
        "cyan_wool": ("cyan", "cyan_wool"),
        "orange_wool": ("orange", "orange_wool"),
        "yellow_wool": ("yellow", "yellow_wool"),
        "light_blue_wool": ("light_blue", "light_blue_wool"),
        "magenta_wool": ("magenta", "magenta_wool"),
        "green_wool": ("green", "green_wool"),
        "white_wool": ("white", "white_wool"),
        "black_wool": ("black", "black_wool"),
    }

    # --- UI & Init ---
    __init__(parent, canvas, world, options_path)

    # --- Button Handlers ---
    _on_scan(event)              # Phase 1: scan + compute + preview
    _on_fill(event)              # Phase 2: place blocks
    _on_tension_change(event)    # Recompute spline when slider moves

    # --- Core Logic (static methods) ---
    scan_markers(world, dimension, selection, start_color, end_color, control_color)
        -> (start_coord, end_coord, control_coords_list)

    order_control_points(start, end, control_points)
        -> ordered list of (x, y, z) tuples

    catmull_rom_spline(points, tension, samples_per_unit=2)
        -> np.ndarray of shape (N, 3)

    rasterize_to_voxels(spline_coords)
        -> set of (int, int, int)

    bresenham_3d(p1, p2)
        -> list of (int, int, int) between two points

    get_clearance_voxels(path_voxels, width, height)
        -> set of (int, int, int)

    place_blocks(world, dimension, path_voxels, clearance_voxels, path_block_name, remove_markers, marker_coords)
        -> None (modifies world)
```

---

### UI Layout (top to bottom)

```
+--------------------------------------+
| Start Marker Color:    [lime_wool v] |
| End Marker Color:      [red_wool  v] |
| Control Point Color:   [blue_wool v] |
| Path Block:            [pink_wool v] |
|--------------------------------------|
| Spline Tension:  [====O==========]  |
|                  loose    tight      |
|--------------------------------------|
| Clearance Width:       [1  ^v]       |
| Clearance Height:      [3  ^v]       |
|--------------------------------------|
| [x] Remove markers after fill       |
|--------------------------------------|
| Status: Ready                        |
|--------------------------------------|
| [ Scan & Preview ]  [ Fill Path ]    |
+--------------------------------------+
```

- Dropdowns: `wx.Choice`
- Tension: `wx.Slider` (min=0, max=100, default=50) maps to 0.0-1.0
- Width/Height: `wx.SpinCtrl` (min=0, max=10)
- Checkbox: `wx.CheckBox`
- Status: `wx.StaticText` (updated with scan results, errors, block counts)
- Fill button: starts disabled, enabled after successful scan

---

### Workflow

**Phase 1 — Scan & Preview** (`_on_scan`):
1. Validate color selections (all different)
2. Get `selection = self.canvas.selection.selection_group`
3. `scan_markers()` — iterate all blocks in selection, match blockstates
4. Validate: exactly 1 start, exactly 1 end
5. `order_control_points()` — nearest-neighbor chain
6. `catmull_rom_spline()` — compute 3D curve with current tension
7. `rasterize_to_voxels()` — discretize to block positions with gap filling
8. Update status: "Found N control points. Path: M blocks. Clearance: K blocks."
9. Store results on `self`, enable Fill button

**Phase 2 — Fill** (`_on_fill`):
1. `self.canvas.run_operation(operation)` wraps the work
2. Get `platform, version = world.level_wrapper.platform, world.level_wrapper.version`
3. For each path voxel: `world.set_version_block(x, y, z, dim, (plat, ver), Block("minecraft", path_block), None)`
4. For each clearance voxel: `world.set_version_block(..., Block("minecraft", "air"), None)`
5. If remove markers checked: set marker positions to air
6. Update status: "Done! Placed M path blocks, cleared K air blocks."

**Tension slider change**: If scan data exists, recompute spline + rasterize, update status with new block count. Does not place blocks.

---

### Spline Math: Catmull-Rom

```
Given ordered points P0..Pn:
1. Pad: P = [P0, P0, P1, ..., Pn, Pn]  (duplicate endpoints)
2. For each segment i (from 1 to len(P)-2):
   p0, p1, p2, p3 = P[i-1], P[i], P[i+1], P[i+2]
   segment_length = distance(p1, p2)
   num_samples = max(int(segment_length * samples_per_unit), 2)
   For t in linspace(0, 1, num_samples):
     q(t) = tension-parameterized Catmull-Rom interpolation
3. Concatenate all segment samples
```

Tension matrix (tau = tension, 0.0=loose, 1.0=tight):
```
M = [[ 0,      1,      0,       0     ],
     [-tau,    0,      tau,     0     ],
     [ 2*tau,  tau-3,  3-2*tau, -tau  ],
     [-tau,    2-tau,  tau-2,   tau   ]]

q(t) = [1, t, t^2, t^3] * M * [p0, p1, p2, p3]^T
```

---

### Clearance Model

For each path voxel at (x, y, z):
- Side clearance: dx in [-width, +width], dz in [-width, +width] at same y
- Height clearance: dy in [1, height] with same side expansion
- Exclude path voxels from air set
- Never touch y-1 or below (preserve floor)

---

### Error Handling

All errors shown in the status label, never exceptions to user:

| Condition | Status Message |
|---|---|
| No selection | "Error: Create a selection box first." |
| No start found | "Error: No lime wool (start) found in selection." |
| Multiple starts | "Error: Found N start markers. Place exactly 1." |
| No end found | "Error: No red wool (end) found in selection." |
| Multiple ends | "Error: Found N end markers. Place exactly 1." |
| Duplicate color selections | "Error: Marker colors must all be different." |
| Fill before scan | Button disabled (prevented by UI) |

---

### Reference Files

| File | Use |
|---|---|
| `rail_placer_working_v1dot3_with_choices.py` | Primary pattern: class structure, block iteration, blockstate matching, set_version_block |
| `torch_and_lanter_placer_multilayered_v1.py` | UI patterns: SpinCtrl, Slider, Freeze/Thaw |
| `blue_ice_tunnel_east-west_v1.py` | Multi-block-type placement (path + air), canvas.run_operation wrapping |
| `amulet_source/amulet_core/amulet/api/block.py` | Block class constructor and properties |
| `amulet_source/amulet_core/amulet/api/selection/box.py` | SelectionBox min/max iteration |

---

### Verification

1. **Load plugin**: Copy to Amulet plugins folder, verify it appears in Operations list
2. **UI test**: Confirm all dropdowns, slider, spinners, buttons render correctly
3. **Scan test**: Place lime (start), red (end), 2-3 blue (control) wool blocks, create selection, click Scan. Verify status shows correct counts.
4. **Tension test**: Move slider, verify block count changes in status
5. **Fill test**: Click Fill, verify pink wool path appears along expected spline
6. **Clearance test**: Verify air blocks above/beside path, floor preserved
7. **Error tests**: Try without start, without end, with duplicate colors
8. **Rail placer integration**: Run rail_placer on the generated pink wool path, verify it works end-to-end
