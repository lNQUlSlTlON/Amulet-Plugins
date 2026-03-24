# To Do List: Spline Rail Path Placer Plugin v1
## Project: Amulet-Plugins

---

### Completed (2026-03-16)

| Phase | Status | Notes |
|---|---|---|
| Phase 1: Scaffold & UI | Done | Full UI with dropdowns, slider, spinners, buttons |
| Phase 2: Marker Scanning | Done | `scan_markers()` with blockstate matching + validation |
| Phase 3: Control Point Ordering | Done | `order_control_points()` nearest-neighbor chain |
| Phase 4: Spline Math | Done | `catmull_rom_spline()` with tension, adaptive sampling, 2-point fallback |
| Phase 5: Voxel Rasterization | Done | `rasterize_to_voxels()` returns ordered list with Bresenham gap-filling |
| Phase 6: Clearance Computation | Done | `get_clearance_voxels()` above+sides, never below |
| Phase 7: Scan & Preview | Done | `_on_scan()` full pipeline with status updates |
| Phase 8: Fill Operation | Done | `_on_fill()` wrapped in `canvas.run_operation()` |
| Phase 9: Path Constraints | Done | `enforce_path_constraints()` — 7 sub-passes (9a-9g) |

---

### Phase 9: Rail Placer Path Constraints (Done - 2026-03-24)
Reference: `plans/Analysis_RailPlacer_PathRules_v1.md`
Implemented in `enforce_path_constraints()` static method, called from `_recompute_path()`.

#### 9a. Vertical Stacking Prevention
- [x] After rasterization, validate no two consecutive path voxels share the same X,Z with only a Y difference (dx=0, dz=0, dy!=0)
- [x] If detected, insert a horizontal offset block to create a legal ascending step (one cardinal + one vertical)

#### 9b. Elevation Step Normalization
- [x] Ensure every elevation change is exactly dy=±1 combined with exactly one cardinal axis dx=±1 or dz=±1
- [x] If the spline produces a step with both dx and dz non-zero during an elevation change, correct it to a single-axis step

#### 9c. Turn Flatness Enforcement
- [x] Detect turns in the rasterized path (three consecutive blocks forming a 90° direction change)
- [x] Validate that all blocks in a turn have dy=0 relative to each other
- [x] If a turn occurs on a slope, flatten it by adjusting Y values

#### 9d. Turn-to-Incline Buffer (Minimum 2 Flat Blocks)
- [x] After detecting turns and inclines, verify at least 2 flat cardinal blocks separate them
- [x] If buffer is insufficient, insert additional flat blocks between the turn and incline

#### 9e. Gap Prevention
- [x] Verify every consecutive pair of path voxels is within 1 block on all axes (3x3x3 neighborhood)
- [x] Bresenham gap-filling (Phase 5) should handle this, but add a post-rasterization validation pass

#### 9f. Branch/Ambiguity Prevention
- [x] Verify no path voxel has more than 2 neighbors in the path (would create a branch)
- [x] If detected, prune the extra neighbor(s) to maintain a single linear path

#### 9g. Diagonal Path Prevention
- [x] Detect pure diagonal steps (both dx!=0 and dz!=0 with dy=0) that don't form a valid turn pattern
- [x] Convert to a legal L-shaped step (one cardinal move then another) matching one of the 8 turn patterns

---

### Phase 10: Testing & Polish (Pending - User GUI Testing)
- [ ] Test with 2 points only (start + end, no controls)
- [ ] Test with 1 control point
- [ ] Test with many control points (5+)
- [ ] Test tension slider at extremes (0 and 100)
- [ ] Test with large clearance values
- [ ] Test error cases (missing start/end, duplicate colors)
- [ ] Verify generated wool path works with rail_placer plugin
- [ ] Test on both Bedrock and Java worlds if applicable
