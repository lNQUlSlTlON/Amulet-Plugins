# Session Logs

## Session: 2026-03-16

### Summary
Built the Spline Rail Path Placer plugin and set up reference data/source code for the project.

### Accomplished

1. **Ingested PyMCTranslate Block Information into Context-Mode**
   - Fetched 2,435 JSON files from `PyMCTranslate/json/versions/bedrock_1_21_90`
   - Indexed as 2,676 searchable sections across 14 markdown documents
   - Categories: specification (1,000 blocks), to_universal (1,000), from_universal (433), top-level (2)
   - Searchable via source filter "PyMCTranslate Block Information"

2. **Downloaded Amulet Source Code (no install)**
   - `amulet_source/amulet_map_editor/` — v0.10.52
   - `amulet_source/amulet_core/` — v1.9.37
   - `amulet_source/amulet_nbt/` — v2.0.6
   - `amulet_source/pymctranslate/` — v1.2.42
   - `amulet_source/minecraft_resource_pack/` — v1.3.6
   - `amulet_source/amulet_faulthandler/` — v1.0.3

3. **Planned and Built the Spline Rail Path Placer Plugin**
   - Created architectural analysis: `plans/Analysis_v1.md`
   - Created implementation plan: `plans/Plan_v1.md`
   - Created todo list: `docs/ToDoList_v1.md`
   - Implemented full plugin: `spline_rail_path_placer_v1.py`

### Files Created
| File | Purpose |
|---|---|
| `spline_rail_path_placer_v1.py` | Main plugin — spline-based wool path placer |
| `plans/Analysis_v1.md` | Architectural analysis (algorithms, risks, performance) |
| `plans/Plan_v1.md` | Implementation plan (class structure, workflow, verification) |
| `docs/ToDoList_v1.md` | Phased task checklist |
| `docs/session_logs.md` | This file |
| `amulet_source/` | Downloaded source for Amulet and all dependencies |

### Key Decisions
- **Catmull-Rom spline** (numpy-only, no scipy dependency) — passes through all control points
- **Nearest-neighbor ordering** for control points from start
- **Marker colors**: Lime=start, Red=end, Blue=control (distinct from rail placer's pink/orange/purple)
- **Clearance model**: Above + sides only, never below path
- **Single path per run** (no multi-segment/junction support in v1)
- **3D Bresenham** gap-filling to ensure connected voxel paths

### Pending / Next Steps
- [ ] User GUI testing of the plugin in Amulet
- [ ] Verify spline output works with rail_placer plugin end-to-end
- [ ] Test edge cases: 2 points only, many control points, extreme tension values
- [ ] Test error handling (missing markers, duplicate colors)
- [ ] Nothing has been committed to git yet — all files are untracked

---

## Session: 2026-03-24

### Summary
Thorough reverse-engineering analysis of the rail placer plugin's path-following logic to catalog all legal and illegal wool block configurations.

### Accomplished

1. **Rail Placer Path Rules Analysis**
   - Analyzed all 2,824 lines of `rail_placer_working_v1dot3_with_choices.py`
   - Documented the complete path-tracing algorithm (3x3x3 neighborhood search)
   - Mapped all 12 straight/ascending direction patterns (lines 531-544)
   - Mapped all 8 hardcoded turn patterns (lines 636-719)
   - Identified the `recursive` flag mechanism for ascending rail handling
   - Created comprehensive analysis: `plans/Analysis_RailPlacer_PathRules_v1.md`

2. **Illegal Configuration Catalog (6 crash/failure modes)**
   - Vertical stacking (dx=0, dy!=0, dz=0) — degenerate direction, no forward movement
   - Turn with elevation change — no matching pattern, unpack error at line 720
   - Turn within 1 block of incline — `recursive` flag corrupts direction metadata
   - Ambiguous neighborhood (3+ adjacent wool) — only last 2 processed
   - Gaps > 1 block — path tracing terminates
   - Pure diagonal paths — misidentified direction

3. **Bugs Found**
   - Powered rail frequency: `% 16 == 16` (line 844) is always false
   - Minimum 2 flat blocks required between turns and inclines (emergent, not validated)

### Files Created
| File | Purpose |
|---|---|
| `plans/Analysis_RailPlacer_PathRules_v1.md` | Complete legal/illegal path configuration catalog |

### Key Decisions
- **2-block minimum buffer** between turns and inclines is critical for spline plugin path generation
- All turns must be perfectly flat (dy=0 for both blocks in the turn pair)
- Path blocks must be within 1 block on all axes (3x3x3 neighborhood constraint)

### Pending / Next Steps
- [ ] Apply path rules as constraints in the spline plugin's voxel rasterization
- [ ] User GUI testing of the spline plugin in Amulet
- [ ] Verify spline output works with rail_placer plugin end-to-end
