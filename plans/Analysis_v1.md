# Architectural Analysis: Spline Rail Path Placer Plugin
## Version 1.0

### 1. System Context

The Spline Rail Path Placer is an Amulet Map Editor plugin that automates wool block placement for the existing Rail Placer plugin. It replaces tedious manual placement of hundreds of pink wool blocks with a spline-based workflow: place a few colored markers, compute a smooth 3D path, and fill it automatically.

**Upstream dependency**: Amulet Map Editor v0.10.52 + amulet-core v1.9.37
**Downstream consumer**: `rail_placer_working_v1dot3_with_choices.py` (reads pink wool paths)

---

### 2. Plugin Architecture Pattern

All Amulet plugins in this project follow the same pattern:

```
Class(wx.Panel, DefaultOperationUI)
  __init__(parent, canvas, world, options_path)
    -> builds wxPython UI
  _operation / button handlers
    -> reads selection via canvas.selection.selection_group
    -> reads blocks via world.get_block(x, y, z, dimension)
    -> writes blocks via world.set_version_block(x, y, z, dimension, (platform, version), Block(...), None)

export = {"name": "...", "operation": Class}
```

Key imports:
- `amulet.api.block.Block`
- `amulet.api.selection.SelectionBox, SelectionGroup`
- `amulet.api.data_types.Dimension`
- `amulet_map_editor.programs.edit.api.operations.DefaultOperationUI`
- `amulet_nbt.StringTag, IntTag, ByteTag`
- `wx`, `numpy`

---

### 3. Block Identification

Blocks are read in **universal format**: `'universal_minecraft:wool[color=pink]'`
Blocks are written in **platform format**: `Block("minecraft", "pink_wool")`

The `set_version_block` method handles translation between universal and platform-specific formats using the platform/version tuple from `world.level_wrapper`.

---

### 4. Spline Algorithm Selection

**Chosen: Catmull-Rom spline (manual implementation with numpy)**

| Algorithm | Passes Through Points | Tension Control | External Deps | Complexity |
|---|---|---|---|---|
| Catmull-Rom | Yes | Yes | None (numpy only) | Medium |
| Cubic B-spline | No (approximates) | Yes | None | Medium |
| scipy CubicSpline | Yes | Limited | scipy | Low |
| Bezier curves | Control points != path | N/A | None | Low |

**Rationale**: Catmull-Rom is ideal because:
1. The path passes **through** all control points (user expectation)
2. Built-in tension parameter (0.0=loose, 1.0=tight/linear)
3. No scipy dependency (may not be in Amulet's environment)
4. Well-understood, deterministic behavior

**Edge cases**:
- 2 points (start+end only): Degenerates to linear interpolation
- 3 points (start+1 control+end): Single curve segment
- Endpoint padding: Duplicate first/last points for boundary segments

---

### 5. Control Point Ordering

**Chosen: Nearest-neighbor chain from start point**

The user places control points in 3D space with no inherent ordering. The algorithm:
1. Begin at the start point
2. Find the nearest unvisited control point
3. Move to it, repeat until all visited
4. Append the end point

This is a greedy heuristic (O(n^2) but n is small). It works well for path-like arrangements where control points are roughly sequential. For ambiguous layouts (e.g., U-shaped paths), the user can adjust by adding intermediate control points.

---

### 6. Voxel Rasterization Strategy

Converting continuous spline coordinates to discrete block positions:

1. **Sample the spline** at sub-block resolution (samples proportional to segment length)
2. **Round to integers** to get block coordinates
3. **Fill gaps** using 3D Bresenham line algorithm between consecutive samples
4. **Deduplicate** into a set of unique (x, y, z) positions

This ensures a connected path with no gaps, even on diagonal/steep sections.

---

### 7. Clearance Model

"Above + sides" clearance (user-selected):

```
         AIR  AIR  AIR          <- y + height
         AIR  AIR  AIR
         AIR  AIR  AIR          <- y + 1
    [ground] WOOL [ground]      <- y (path level)
    [ground] [ground] [ground]  <- y - 1 (untouched)
         ^         ^
    x - width   x + width
```

- Width: configurable (0-10 blocks on each side)
- Height: configurable (0-10 blocks above path)
- Below path: never cleared (preserves terrain floor)
- Path voxels themselves: excluded from air clearing

---

### 8. Two-Phase Operation Model

**Phase 1 - Scan & Preview** (no world modifications):
- Iterate selection, find marker blocks by blockstate
- Validate (exactly 1 start, 1 end, colors don't conflict)
- Order control points
- Compute spline with current tension
- Rasterize to voxels
- Display block count and path info in status label
- Enable the Fill button

**Phase 2 - Fill** (modifies world):
- Wrapped in `canvas.run_operation()` for undo support
- Place path blocks (pink wool by default) along spline voxels
- Set clearance voxels to air
- Optionally remove original markers

This separation lets the user preview and adjust tension before committing.

---

### 9. Performance Considerations

| Operation | Scaling Factor | Mitigation |
|---|---|---|
| Selection scan | O(volume of selection box) | User keeps selection tight; status shows progress |
| Spline computation | O(num_segments * samples_per_segment) | Fast with numpy; typically <1000 points |
| Voxel rasterization | O(spline_samples) | Set deduplication; typically <5000 voxels |
| Block placement | O(path_voxels + clearance_voxels) | Individual set_version_block calls; bottleneck for large paths |
| Clearance computation | O(path_voxels * width * height) | Could be large; precompute as set for O(1) lookup |

For a typical rail path of ~200 blocks with width=1, height=3 clearance: ~200 wool placements + ~1400 air placements. This is well within interactive performance.

---

### 10. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| scipy not available | Build fails | Low | Using numpy-only Catmull-Rom implementation |
| Nearest-neighbor misordering | Wrong path shape | Medium | User can add more control points to disambiguate |
| Gaps in rasterized path | Rail placer fails | High if unhandled | Bresenham gap-filling between samples |
| Large selection scan is slow | Poor UX | Medium | Status feedback during scan |
| Block name differences Java vs Bedrock | Wrong blocks placed | Low | set_version_block handles translation |
