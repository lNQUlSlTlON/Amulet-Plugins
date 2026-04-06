# Spiral Path Placer
# Generate spiral wool paths that comply with rail placer path rules.
# Designed to feed into the Rail Placer plugin.
#
# Amulet Map Editor and API Code from the Amulet Team
# All other code (c) 2024 Black Forest Creations
# Blame:  @lNQUlSlTlON

"""
This plugin generates spiral-shaped wool paths for the Rail Placer plugin.

Place a single marker block (e.g., emerald block) to define the spiral start point,
then create a selection box around it and run this plugin.

It computes a helix path at the specified radius and pitch, rasterizes to
voxels, enforces rail placer path constraints, and fills with wool blocks.

Controls:
  - Radius: distance from center to spiral path
  - Y Offset: total vertical distance (negative = down, positive = up)
  - Number of Turns: how many revolutions (supports fractional)
  - Direction: clockwise or counter-clockwise
"""

import math
import numpy as np
import wx

from typing import TYPE_CHECKING, List, Tuple, Set
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI

if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas


# Marker block options: label -> universal blockstate
START_MARKER_MAP = {
    "Emerald Block": "universal_minecraft:emerald_block",
    "Diamond Block": "universal_minecraft:diamond_block",
    "Gold Block":    "universal_minecraft:gold_block",
    "Lapis Block":   "universal_minecraft:lapis_block",
}
START_MARKER_CHOICES = list(START_MARKER_MAP.keys())

# Wool color options: label -> (universal_color, platform_block_name)
WOOL_COLOR_MAP = {
    "Pink Wool":       ("pink",       "pink_wool"),
    "Orange Wool":     ("orange",     "orange_wool"),
}
WOOL_CHOICES = list(WOOL_COLOR_MAP.keys())

DIRECTION_CHOICES = ["Clockwise", "Counter-Clockwise"]

# Cardinal direction: which direction from start point to spiral center
CARDINAL_CHOICES = ["X+ (East)", "X- (West)", "Z+ (South)", "Z- (North)"]


class SpiralPathPlacerV1(wx.Panel, DefaultOperationUI):
    def __init__(
        self,
        parent: wx.Window,
        canvas: "EditCanvas",
        world: "BaseLevel",
        options_path: str,
    ):
        wx.Panel.__init__(self, parent)
        DefaultOperationUI.__init__(self, parent, canvas, world, options_path)
        self.Freeze()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        # --- Start Marker Block ---
        self._sizer.Add(
            wx.StaticText(self, label="Start Marker Block:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._marker_dropdown = wx.Choice(self, choices=START_MARKER_CHOICES)
        self._marker_dropdown.SetSelection(0)
        self._sizer.Add(self._marker_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Cardinal Direction (start to center) ---
        self._sizer.Add(
            wx.StaticText(self, label="Spiral Extends Toward:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._cardinal_dropdown = wx.Choice(self, choices=CARDINAL_CHOICES)
        self._cardinal_dropdown.SetSelection(0)
        self._sizer.Add(self._cardinal_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Radius ---
        self._sizer.Add(
            wx.StaticText(self, label="Radius (blocks):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._radius_spin = wx.SpinCtrl(self, min=4, max=50, initial=8)
        self._sizer.Add(self._radius_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Y Offset ---
        self._sizer.Add(
            wx.StaticText(self, label="Y Offset (+ up, - down):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._y_offset_spin = wx.SpinCtrl(self, min=-256, max=256, initial=-20)
        self._sizer.Add(self._y_offset_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Number of Turns ---
        self._sizer.Add(
            wx.StaticText(self, label="Number of Turns:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._turns_spin = wx.SpinCtrlDouble(
            self, min=0.25, max=20.0, initial=1.0, inc=0.25
        )
        self._turns_spin.SetDigits(2)
        self._sizer.Add(self._turns_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Direction ---
        self._sizer.Add(
            wx.StaticText(self, label="Direction:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._direction_dropdown = wx.Choice(self, choices=DIRECTION_CHOICES)
        self._direction_dropdown.SetSelection(0)
        self._sizer.Add(self._direction_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Clearance Controls ---
        self._sizer.Add(
            wx.StaticText(self, label="Clearance Width (blocks each side):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._width_spin = wx.SpinCtrl(self, min=0, max=5, initial=1)
        self._sizer.Add(self._width_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._sizer.Add(
            wx.StaticText(self, label="Clearance Height (blocks above):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._height_spin = wx.SpinCtrl(self, min=2, max=8, initial=4)
        self._sizer.Add(self._height_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Wool Color ---
        self._sizer.Add(
            wx.StaticText(self, label="Path Block:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._wool_dropdown = wx.Choice(self, choices=WOOL_CHOICES)
        self._wool_dropdown.SetSelection(0)  # Pink Wool
        self._sizer.Add(self._wool_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Buttons ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._scan_button = wx.Button(self, label="Scan")
        self._scan_button.Bind(wx.EVT_BUTTON, self._on_scan)
        btn_sizer.Add(self._scan_button, 0, wx.ALL, 5)

        self._preview_button = wx.Button(self, label="Preview")
        self._preview_button.Bind(wx.EVT_BUTTON, self._on_preview)
        self._preview_button.Disable()
        btn_sizer.Add(self._preview_button, 0, wx.ALL, 5)

        self._fill_button = wx.Button(self, label="Fill")
        self._fill_button.Bind(wx.EVT_BUTTON, self._on_fill)
        self._fill_button.Disable()
        btn_sizer.Add(self._fill_button, 0, wx.ALL, 5)

        self._sizer.Add(btn_sizer, 0, wx.ALIGN_CENTRE_HORIZONTAL)

        # --- Status Label ---
        self._status = wx.StaticText(self, label="Status: Ready. Create a selection and click Scan.")
        self._status.Wrap(250)
        self._sizer.Add(self._status, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

        # --- State ---
        self._start: Tuple[int, int, int] = (0, 0, 0)
        self._path_voxels: Set[Tuple[int, int, int]] = set()
        self._clearance_voxels: Set[Tuple[int, int, int]] = set()
        self._ordered_path: List[Tuple[int, int, int]] = []
        self._constraint_stats: dict = {}
        self._scan_complete = False

    # -------------------------------------------------------------------------
    # Button Handlers
    # -------------------------------------------------------------------------

    def _on_scan(self, _):
        """Phase 1: Scan selection for the start marker block."""
        marker_label = self._marker_dropdown.GetStringSelection()
        marker_blockstate = START_MARKER_MAP[marker_label]

        selection_group = self.canvas.selection.selection_group
        if selection_group is None or len(selection_group) == 0:
            self._set_status("Error: Create a selection box first.")
            return

        world = self.canvas.world
        dimension = self.canvas.dimension

        centers = []
        for box in selection_group.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        block = world.get_block(x, y, z, dimension)
                        bs = block.blockstate
                        if bs == marker_blockstate:
                            centers.append((x, y, z))

        if len(centers) == 0:
            self._set_status(f"Error: No {marker_label} found in selection.")
            return
        if len(centers) > 1:
            self._set_status(
                f"Error: Found {len(centers)} {marker_label}s. Place exactly 1."
            )
            return

        self._start = centers[0]
        self._scan_complete = True
        self._preview_button.Enable()
        self._fill_button.Disable()

        self._set_status(
            f"Scan complete! Start at ({self._start[0]}, {self._start[1]}, {self._start[2]}). "
            f"Click Preview to compute spiral path."
        )

    def _on_preview(self, _):
        """Phase 2: Compute spiral path and show as selection preview."""
        if not self._scan_complete:
            return

        self._recompute_path()
        self._show_path_preview()
        self._fill_button.Enable()

        fixes = self._constraint_stats.get("total_fixes", 0)
        fix_msg = f" Constraints: {fixes} fix(es)." if fixes > 0 else ""
        self._set_status(
            f"Preview: {len(self._path_voxels)} path blocks, "
            f"{len(self._clearance_voxels)} air clearance.{fix_msg} "
            f"Adjust settings and re-Preview, or click Fill."
        )

    def _on_fill(self, _):
        """Phase 3: Place path blocks and clear air."""
        if not self._scan_complete:
            return

        world = self.canvas.world
        dimension = self.canvas.dimension
        wool_label = self._wool_dropdown.GetStringSelection()
        wool_block_name = WOOL_COLOR_MAP[wool_label][1]

        # Capture state for the closure
        path_voxels = set(self._path_voxels)
        clearance_voxels = set(self._clearance_voxels)

        def operation():
            platform = world.level_wrapper.platform
            version_number = world.level_wrapper.version

            path_block = Block("minecraft", wool_block_name)
            air_block = Block("minecraft", "air")

            # Place path blocks
            for x, y, z in path_voxels:
                world.set_version_block(
                    x, y, z, dimension,
                    (platform, version_number),
                    path_block, None
                )

            # Place air blocks for clearance
            for x, y, z in clearance_voxels:
                world.set_version_block(
                    x, y, z, dimension,
                    (platform, version_number),
                    air_block, None
                )

        self.canvas.run_operation(operation)

        self._set_status(
            f"Done! Placed {len(path_voxels)} path blocks, "
            f"cleared {len(clearance_voxels)} air blocks."
        )
        print("Spiral Path Placer operation completed successfully.")

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _recompute_path(self):
        """Recompute spiral, rasterize, enforce constraints, and calculate clearance."""
        radius = self._radius_spin.GetValue()
        y_offset = self._y_offset_spin.GetValue()
        num_turns = self._turns_spin.GetValue()
        clockwise = self._direction_dropdown.GetStringSelection() == "Clockwise"
        cardinal = self._cardinal_dropdown.GetStringSelection()
        width = self._width_spin.GetValue()
        height = self._height_spin.GetValue()

        # Compute spiral center from start point + cardinal direction + radius
        sx, sy, sz = self._start
        if cardinal.startswith("X+"):
            center = (sx + radius, sy, sz)
        elif cardinal.startswith("X-"):
            center = (sx - radius, sy, sz)
        elif cardinal.startswith("Z+"):
            center = (sx, sy, sz + radius)
        else:  # Z-
            center = (sx, sy, sz - radius)

        # Generate raw spiral coordinates
        raw_coords = self.generate_spiral(
            self._start, center, radius, y_offset, num_turns, clockwise
        )

        # Rasterize to voxels with Bresenham gap filling
        ordered_voxels = self.rasterize_to_voxels(raw_coords)

        # Enforce rail placer path constraints
        self._ordered_path, self._constraint_stats = self.enforce_path_constraints(
            ordered_voxels
        )
        self._path_voxels = set(self._ordered_path)
        self._clearance_voxels = self.get_clearance_voxels(
            self._path_voxels, width, height
        )

    def _show_path_preview(self):
        """Set the canvas selection to show path blocks as highlighted boxes."""
        boxes = [
            SelectionBox((x, y, z), (x + 1, y + 1, z + 1))
            for x, y, z in self._ordered_path
        ]
        if boxes:
            self.canvas.selection.set_selection_group(SelectionGroup(boxes))

    def _set_status(self, text: str):
        """Update the status label text."""
        self._status.SetLabel(f"Status: {text}")
        self._status.Wrap(250)
        self.Layout()

    # -------------------------------------------------------------------------
    # Spiral Generation
    # -------------------------------------------------------------------------

    @staticmethod
    def generate_spiral(
        start: Tuple[int, int, int],
        center: Tuple[int, int, int],
        radius: int,
        y_offset: int,
        num_turns: float,
        clockwise: bool,
    ) -> List[Tuple[float, float, float]]:
        """
        Generate dense float coordinates along a helix (spiral).

        The path starts at the start marker position and spirals around the
        computed center, going up or down based on y_offset.

        Args:
            start: (x, y, z) of the start marker block (where spiral begins).
            center: (x, y, z) of the computed spiral center.
            radius: Horizontal distance from center to path.
            y_offset: Total vertical displacement (negative = down, positive = up).
            num_turns: Number of full revolutions (supports fractional).
            clockwise: True for clockwise when viewed from above.

        Returns:
            List of (x, y, z) float coordinates.
        """
        cx, cy, cz = center
        sx, sy, sz = start

        # Compute starting angle from the start position relative to center
        start_angle = math.atan2(sz - cz, sx - cx)
        total_angle = num_turns * 2.0 * math.pi

        # Sample densely: approximately 1 degree per step
        num_samples = max(int(math.degrees(total_angle)), 2)
        coords = []

        for i in range(num_samples + 1):
            t = i / num_samples  # 0.0 to 1.0

            # CW = increasing angle, CCW = decreasing angle (Minecraft Y-down view)
            if clockwise:
                theta = start_angle + t * total_angle
            else:
                theta = start_angle - t * total_angle

            x = cx + radius * math.cos(theta)
            z = cz + radius * math.sin(theta)
            y = sy + t * y_offset

            coords.append((x, y, z))

        return coords

    # -------------------------------------------------------------------------
    # Rasterization (from spline v3)
    # -------------------------------------------------------------------------

    @staticmethod
    def bresenham_3d(
        p1: Tuple[int, int, int],
        p2: Tuple[int, int, int],
    ) -> List[Tuple[int, int, int]]:
        """
        3D Bresenham line algorithm to fill gaps between two voxel positions.
        Returns list of (x, y, z) positions along the line, excluding p1.
        """
        x1, y1, z1 = p1
        x2, y2, z2 = p2

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dz = abs(z2 - z1)

        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        sz = 1 if z2 > z1 else -1

        if dx >= dy and dx >= dz:
            err_y = 2 * dy - dx
            err_z = 2 * dz - dx
            result = []
            x, y, z = x1, y1, z1
            for _ in range(dx):
                if err_y > 0:
                    y += sy
                    err_y -= 2 * dx
                if err_z > 0:
                    z += sz
                    err_z -= 2 * dx
                x += sx
                err_y += 2 * dy
                err_z += 2 * dz
                result.append((x, y, z))
            return result
        elif dy >= dx and dy >= dz:
            err_x = 2 * dx - dy
            err_z = 2 * dz - dy
            result = []
            x, y, z = x1, y1, z1
            for _ in range(dy):
                if err_x > 0:
                    x += sx
                    err_x -= 2 * dy
                if err_z > 0:
                    z += sz
                    err_z -= 2 * dy
                y += sy
                err_x += 2 * dx
                err_z += 2 * dz
                result.append((x, y, z))
            return result
        else:
            err_x = 2 * dx - dz
            err_y = 2 * dy - dz
            result = []
            x, y, z = x1, y1, z1
            for _ in range(dz):
                if err_x > 0:
                    x += sx
                    err_x -= 2 * dz
                if err_y > 0:
                    y += sy
                    err_y -= 2 * dz
                z += sz
                err_x += 2 * dx
                err_y += 2 * dy
                result.append((x, y, z))
            return result

    @staticmethod
    def rasterize_to_voxels(
        float_coords: List[Tuple[float, float, float]],
    ) -> List[Tuple[int, int, int]]:
        """
        Convert continuous float coordinates to discrete block positions.
        Uses rounding + Bresenham gap-filling to ensure a connected path.

        Returns an ordered list (deduplicated, preserving traversal order).
        """
        if len(float_coords) == 0:
            return []

        ordered = []
        seen = set()
        prev = None

        for coord in float_coords:
            current = (int(round(coord[0])), int(round(coord[1])), int(round(coord[2])))

            if prev is not None and prev != current:
                dx = abs(current[0] - prev[0])
                dy = abs(current[1] - prev[1])
                dz = abs(current[2] - prev[2])
                if dx > 1 or dy > 1 or dz > 1:
                    gap_voxels = SpiralPathPlacerV1.bresenham_3d(prev, current)
                    for gv in gap_voxels:
                        if gv not in seen:
                            ordered.append(gv)
                            seen.add(gv)

            if current not in seen:
                ordered.append(current)
                seen.add(current)

            prev = current

        return ordered

    # -------------------------------------------------------------------------
    # Path Constraint Enforcement (from spline v3)
    # -------------------------------------------------------------------------

    @staticmethod
    def enforce_path_constraints(
        path: List[Tuple[int, int, int]],
    ) -> Tuple[List[Tuple[int, int, int]], dict]:
        """
        Validate and fix the rasterized path to comply with rail placer rules.

        Runs constraint fixes in order:
          9e. Gap prevention
          9b. Elevation step normalization
          9g. Diagonal path prevention
          9d. Turn-to-incline buffer insertion
          9c. Turn flatness enforcement
          10.  Post-filter: vertical stack cleanup
          10b. Post-filter: knot detection
          10c. Post-filter: gap detection
          10d. Post-filter: turn before elevation detection
          9f.  Branch/ambiguity prevention

        Returns (fixed_path, stats_dict) where stats_dict counts fixes applied.
        """
        if len(path) < 2:
            return list(path), {"total_fixes": 0}

        stats = {
            "gaps_filled": 0,
            "vertical_stacks_fixed": 0,
            "elevation_steps_fixed": 0,
            "diagonals_fixed": 0,
            "turns_flattened": 0,
            "buffers_inserted": 0,
            "branches_pruned": 0,
        }

        fixed = list(path)

        def _is_single_cardinal(dx, dz):
            """True if the step is exactly one cardinal direction (not diagonal, not zero)."""
            return (dx != 0) != (dz != 0)

        def _log_path(label):
            """Print the full ordered path with step deltas for debugging."""
            print(f"\n=== {label} ({len(fixed)} blocks) ===")
            for idx, v in enumerate(fixed):
                if idx == 0:
                    print(f"  [{idx:3d}] ({v[0]:5d}, {v[1]:3d}, {v[2]:5d})")
                else:
                    p = fixed[idx - 1]
                    d = (v[0]-p[0], v[1]-p[1], v[2]-p[2])
                    print(f"  [{idx:3d}] ({v[0]:5d}, {v[1]:3d}, {v[2]:5d})  delta=({d[0]:+d},{d[1]:+d},{d[2]:+d})")

        _log_path("INPUT (after rasterization)")

        # --- 9e. Gap Prevention ---
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = abs(nxt[0] - curr[0])
            dy = abs(nxt[1] - curr[1])
            dz = abs(nxt[2] - curr[2])
            if dx > 1 or dy > 1 or dz > 1:
                gap = SpiralPathPlacerV1.bresenham_3d(curr, nxt)
                for j, gv in enumerate(gap[:-1]):
                    fixed.insert(i + 1 + j, gv)
                stats["gaps_filled"] += len(gap) - 1
                i += len(gap)
            else:
                i += 1

        if stats["gaps_filled"]:
            _log_path("AFTER 9e (gap prevention)")

        # --- 9b. Elevation Step Normalization ---
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dy != 0:
                if dx != 0 and dz != 0:
                    if abs(dx) >= abs(dz):
                        step_dx = 1 if dx > 0 else -1
                        step_dy = 1 if dy > 0 else -1
                        mid = (curr[0] + step_dx, curr[1] + step_dy, curr[2])
                    else:
                        step_dz = 1 if dz > 0 else -1
                        step_dy = 1 if dy > 0 else -1
                        mid = (curr[0], curr[1] + step_dy, curr[2] + step_dz)
                    fixed.insert(i + 1, mid)
                    stats["elevation_steps_fixed"] += 1
                    i += 1
                elif abs(dy) > 1:
                    step_dy = 1 if dy > 0 else -1
                    step_dx = 1 if dx > 0 else (-1 if dx < 0 else 0)
                    step_dz = 1 if dz > 0 else (-1 if dz < 0 else 0)
                    if step_dx == 0 and step_dz == 0:
                        if i > 0:
                            prev = fixed[i - 1]
                            pdx = curr[0] - prev[0]
                            pdz = curr[2] - prev[2]
                            step_dx = 1 if pdx > 0 else (-1 if pdx < 0 else 1)
                            if pdx == 0:
                                step_dz = 1 if pdz > 0 else (-1 if pdz < 0 else 0)
                                step_dx = 0
                        else:
                            step_dx = 1
                    mid = (curr[0] + step_dx, curr[1] + step_dy, curr[2] + step_dz)
                    fixed.insert(i + 1, mid)
                    stats["elevation_steps_fixed"] += 1
                    i += 1
                else:
                    i += 1
            else:
                i += 1

        if stats["elevation_steps_fixed"]:
            _log_path("AFTER 9b (elevation normalization)")

        # --- 9g. Diagonal Path Prevention ---
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dx != 0 and dz != 0 and dy == 0:
                is_turn = False
                if i > 0 and i + 2 < len(fixed):
                    prev = fixed[i - 1]
                    after = fixed[i + 2]
                    d_prev_x = curr[0] - prev[0]
                    d_prev_y = curr[1] - prev[1]
                    d_prev_z = curr[2] - prev[2]
                    d_after_x = after[0] - nxt[0]
                    d_after_y = after[1] - nxt[1]
                    d_after_z = after[2] - nxt[2]
                    if (_is_single_cardinal(d_prev_x, d_prev_z) and
                            _is_single_cardinal(d_after_x, d_after_z) and
                            d_prev_y == 0 and d_after_y == 0 and
                            prev[1] == curr[1] == nxt[1] == after[1]):
                        prev_axis = 'x' if d_prev_x != 0 else 'z'
                        after_axis = 'x' if d_after_x != 0 else 'z'
                        if prev_axis != after_axis:
                            is_turn = True
                if not is_turn:
                    mid = (nxt[0], curr[1], curr[2])
                    fixed.insert(i + 1, mid)
                    stats["diagonals_fixed"] += 1
                    i += 2
                else:
                    i += 1
            else:
                i += 1

        if stats["diagonals_fixed"]:
            _log_path("AFTER 9g (diagonal prevention)")

        # --- 9d. Turn-to-Incline Buffer ---
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dy = nxt[1] - curr[1]
            if dy != 0 and _is_single_cardinal(nxt[0] - curr[0], nxt[2] - curr[2]):
                adx = nxt[0] - curr[0]
                adz = nxt[2] - curr[2]
                elev_y = curr[1]

                major_is_x = (adx != 0)

                reshape_start = i
                for j in range(i - 1, max(i - 8, -1), -1):
                    if j < 0:
                        break
                    if fixed[j][1] != elev_y:
                        break
                    reshape_start = j

                start_pt = fixed[reshape_start]
                end_pt = fixed[i]
                total_dx = end_pt[0] - start_pt[0]
                total_dz = end_pt[2] - start_pt[2]

                if major_is_x:
                    major_disp = abs(total_dx)
                    minor_disp = abs(total_dz)
                else:
                    major_disp = abs(total_dz)
                    minor_disp = abs(total_dx)

                while major_disp < 3 and reshape_start > 0:
                    reshape_start -= 1
                    if fixed[reshape_start][1] != elev_y:
                        reshape_start += 1
                        break
                    start_pt = fixed[reshape_start]
                    total_dx = end_pt[0] - start_pt[0]
                    total_dz = end_pt[2] - start_pt[2]
                    major_disp = abs(total_dx) if major_is_x else abs(total_dz)
                    minor_disp = abs(total_dz) if major_is_x else abs(total_dx)

                if major_disp >= 3 and minor_disp >= 1:
                    y = elev_y
                    x, z = start_pt[0], start_pt[2]
                    replacement = [start_pt]

                    if major_is_x:
                        sz = 1 if total_dz > 0 else -1
                        for _ in range(abs(total_dz)):
                            z += sz
                            replacement.append((x, y, z))
                        sx = 1 if total_dx > 0 else -1
                        for _ in range(abs(total_dx)):
                            x += sx
                            replacement.append((x, y, z))
                    else:
                        sx = 1 if total_dx > 0 else -1
                        for _ in range(abs(total_dx)):
                            x += sx
                            replacement.append((x, y, z))
                        sz = 1 if total_dz > 0 else -1
                        for _ in range(abs(total_dz)):
                            z += sz
                            replacement.append((x, y, z))

                    if replacement[-1] == end_pt:
                        old_len = i - reshape_start + 1
                        fixed[reshape_start:i + 1] = replacement
                        new_i = reshape_start + len(replacement) - 1
                        stats["buffers_inserted"] += 1
                        print(
                            f"  9d: reshaped [{reshape_start}..{i}] ({old_len} blocks) "
                            f"-> L-shape ({len(replacement)} blocks) "
                            f"major={'X' if major_is_x else 'Z'}={major_disp}, "
                            f"minor={'Z' if major_is_x else 'X'}={minor_disp}, "
                            f"buffer before ascending at Y={elev_y}->{elev_y + dy}"
                        )
                        i = new_i + 1
                        continue
            i += 1

        if stats["buffers_inserted"]:
            _log_path("AFTER 9d (turn-to-incline buffer)")

        # --- 9c. Turn Flatness Enforcement ---
        i = 1
        while i < len(fixed) - 1:
            prev = fixed[i - 1]
            curr = fixed[i]
            nxt = fixed[i + 1]
            d1x = curr[0] - prev[0]
            d1y = curr[1] - prev[1]
            d1z = curr[2] - prev[2]
            d2x = nxt[0] - curr[0]
            d2y = nxt[1] - curr[1]
            d2z = nxt[2] - curr[2]
            is_turn = False
            if (d1y == 0 and d2y == 0 and
                    _is_single_cardinal(d1x, d1z) and _is_single_cardinal(d2x, d2z)):
                prev_axis = 'x' if d1x != 0 else 'z'
                next_axis = 'x' if d2x != 0 else 'z'
                if prev_axis != next_axis:
                    is_turn = True
            if is_turn:
                target_y = prev[1]
                if curr[1] != target_y or nxt[1] != target_y:
                    fixed[i] = (curr[0], target_y, curr[2])
                    fixed[i + 1] = (nxt[0], target_y, nxt[2])
                    stats["turns_flattened"] += 1
                i += 2
            else:
                i += 1

        if stats["turns_flattened"]:
            _log_path("AFTER 9c (turn flatness)")

        # --- 10. Post-Filter: Vertical Stack Cleanup ---
        path_positions = set(fixed)
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dx == 0 and dz == 0 and dy != 0:
                candidates = []
                if i + 2 < len(fixed):
                    after = fixed[i + 2]
                    ddx, ddz = after[0] - nxt[0], after[2] - nxt[2]
                    if ddx != 0:
                        candidates.append((1 if ddx > 0 else -1, 0))
                    if ddz != 0:
                        candidates.append((0, 1 if ddz > 0 else -1))
                if i > 0:
                    prev = fixed[i - 1]
                    pdx, pdz = curr[0] - prev[0], curr[2] - prev[2]
                    if pdx != 0:
                        candidates.append((1 if pdx > 0 else -1, 0))
                    if pdz != 0:
                        candidates.append((0, 1 if pdz > 0 else -1))
                for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    if d not in candidates:
                        candidates.append(d)

                for ox, oz in candidates:
                    shifted = (nxt[0] + ox, nxt[1], nxt[2] + oz)
                    if shifted == curr:
                        continue
                    if shifted in path_positions and shifted != nxt:
                        if i + 2 < len(fixed) and shifted == fixed[i + 2]:
                            pass
                        else:
                            continue
                    path_positions.discard(nxt)
                    path_positions.add(shifted)
                    fixed[i + 1] = shifted
                    stats["vertical_stacks_fixed"] += 1
                    print(f"  10: vstack fix [{i}]->[{i+1}] shifted {nxt} -> {shifted}")
                    if i + 2 < len(fixed) and fixed[i + 1] == fixed[i + 2]:
                        path_positions.discard(fixed[i + 2])
                        fixed.pop(i + 2)
                        print(f"  10: merged duplicate at [{i+2}]")
                    break
            i += 1

        # --- 10b. Post-Filter: Knot Detection ---
        for i in range(len(fixed)):
            for j in range(i + 3, len(fixed)):
                bx = abs(fixed[j][0] - fixed[i][0])
                by = abs(fixed[j][1] - fixed[i][1])
                bz = abs(fixed[j][2] - fixed[i][2])
                if bx <= 1 and by <= 1 and bz <= 1:
                    print(f"  10b: KNOT at [{i}] {fixed[i]} <-> [{j}] {fixed[j]} (dist {j-i} apart in path)")

        # --- 10c. Post-Filter: Gap Detection ---
        for i in range(len(fixed) - 1):
            curr = fixed[i]
            nxt = fixed[i + 1]
            adx = abs(nxt[0] - curr[0])
            ady = abs(nxt[1] - curr[1])
            adz = abs(nxt[2] - curr[2])
            if max(adx, ady, adz) > 1 or adx + ady + adz > 2:
                print(f"  10c: GAP at [{i}]->[{i+1}] {curr} -> {nxt} (d={adx},{ady},{adz})")

        # --- 10d. Post-Filter: Turn Before Elevation ---
        for i in range(2, len(fixed)):
            curr = fixed[i - 1]
            nxt = fixed[i]
            dy = nxt[1] - curr[1]
            if dy == 0:
                continue
            prev = fixed[i - 2]
            d1x = curr[0] - prev[0]
            d1z = curr[2] - prev[2]
            d2x = nxt[0] - curr[0]
            d2z = nxt[2] - curr[2]
            if d1x != 0 and d2z != 0 and d1z == 0 and d2x == 0:
                print(f"  10d: TURN BEFORE ELEV at [{i-2}]->[{i}] {prev}->{curr}->{nxt}")
            elif d1z != 0 and d2x != 0 and d1x == 0 and d2z == 0:
                print(f"  10d: TURN BEFORE ELEV at [{i-2}]->[{i}] {prev}->{curr}->{nxt}")

        if stats["vertical_stacks_fixed"]:
            _log_path("AFTER 10 (post-filter cleanup)")

        # --- 9f. Branch/Ambiguity Prevention ---
        path_set = set(fixed)
        for i, v in enumerate(fixed):
            neighbors_in_path = 0
            for dx, dy, dz in [
                (1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),
                (1,1,0),(-1,1,0),(1,-1,0),(-1,-1,0),
                (0,1,1),(0,-1,1),(0,1,-1),(0,-1,-1),
                (1,0,1),(-1,0,1),(1,0,-1),(-1,0,-1),
                (1,1,1),(-1,1,1),(1,-1,1),(1,1,-1),
                (-1,-1,1),(-1,1,-1),(1,-1,-1),(-1,-1,-1),
            ]:
                neighbor = (v[0]+dx, v[1]+dy, v[2]+dz)
                if neighbor in path_set and neighbor != v:
                    neighbors_in_path += 1
            if neighbors_in_path > 2:
                stats["branches_pruned"] += 1

        # Remove duplicate consecutive entries
        deduped = [fixed[0]]
        for v in fixed[1:]:
            if v != deduped[-1]:
                deduped.append(v)
        fixed = deduped

        stats["total_fixes"] = sum(v for v in stats.values())
        return fixed, stats

    # -------------------------------------------------------------------------
    # Clearance (from spline v3)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_clearance_voxels(
        path_voxels: Set[Tuple[int, int, int]],
        width: int,
        height: int,
    ) -> Set[Tuple[int, int, int]]:
        """
        Compute air clearance voxels: above and to the sides of the path.
        Never clears below the path level. Excludes path voxels themselves.
        """
        if width == 0 and height == 0:
            return set()

        clearance = set()
        for x, y, z in path_voxels:
            for dx in range(-width, width + 1):
                for dz in range(-width, width + 1):
                    if dx == 0 and dz == 0:
                        continue
                    clearance.add((x + dx, y, z + dz))

            for dy in range(1, height + 1):
                for dx in range(-width, width + 1):
                    for dz in range(-width, width + 1):
                        clearance.add((x + dx, y + dy, z + dz))

        clearance -= path_voxels
        return clearance


export = {
    "name": "Spiral Path Placer v1",
    "operation": SpiralPathPlacerV1,
}
