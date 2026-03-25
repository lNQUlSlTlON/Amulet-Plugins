# Spline Rail Path Placer
# Place colored wool markers, compute a 3D spline, and fill with pink wool.
# Designed to feed into the Rail Placer plugin.
#
# Amulet Map Editor and API Code from the Amulet Team
# All other code (c) 2024 Black Forest Creations
# Blame:  @lNQUlSlTlON

"""
This plugin automates the placement of wool blocks for the Rail Placer plugin.

Instead of manually placing hundreds of pink wool blocks, place a few colored
wool markers:
  - Lime Wool   = Start point (exactly 1)
  - Red Wool    = End point (exactly 1)
  - Blue Wool   = Control points (0 or more)

Then create a selection box around all markers and run this plugin.
It computes a 3D Catmull-Rom spline through the points and fills the path
with pink wool, while clearing air above and beside the path.

The tension slider controls how tightly the spline follows the control points:
  - Low tension (left) = loose, sweeping curves
  - High tension (right) = tight, nearly straight lines between points
"""

import math
import numpy as np
import wx

from typing import TYPE_CHECKING, List, Tuple, Set, Optional
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI

if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas


# Mapping from dropdown label to (universal_color_name, platform_block_name)
WOOL_COLOR_MAP = {
    "Lime Wool":       ("lime",       "lime_wool"),
    "Red Wool":        ("red",        "red_wool"),
    "Blue Wool":       ("blue",       "blue_wool"),
    "Pink Wool":       ("pink",       "pink_wool"),
    "Cyan Wool":       ("cyan",       "cyan_wool"),
    "Orange Wool":     ("orange",     "orange_wool"),
    "Yellow Wool":     ("yellow",     "yellow_wool"),
    "Light Blue Wool": ("light_blue", "light_blue_wool"),
    "Magenta Wool":    ("magenta",    "magenta_wool"),
    "Green Wool":      ("green",      "green_wool"),
    "White Wool":      ("white",      "white_wool"),
    "Black Wool":      ("black",      "black_wool"),
    "Purple Wool":     ("purple",     "purple_wool"),
}

# Dropdown label lists for each role
START_CHOICES = ["Lime Wool", "Yellow Wool", "Light Blue Wool", "Green Wool"]
END_CHOICES = ["Red Wool", "Magenta Wool", "Black Wool", "Orange Wool"]
CONTROL_CHOICES = ["Blue Wool", "Cyan Wool", "Purple Wool", "White Wool"]
PATH_CHOICES = ["Pink Wool", "Orange Wool", "White Wool", "Magenta Wool"]


class SplineRailPathPlacerV2(wx.Panel, DefaultOperationUI):
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

        # --- Marker Color Dropdowns ---
        self._sizer.Add(
            wx.StaticText(self, label="Start Marker Color:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._start_dropdown = wx.Choice(self, choices=START_CHOICES)
        self._start_dropdown.SetSelection(0)
        self._sizer.Add(self._start_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._sizer.Add(
            wx.StaticText(self, label="End Marker Color:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._end_dropdown = wx.Choice(self, choices=END_CHOICES)
        self._end_dropdown.SetSelection(0)
        self._sizer.Add(self._end_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._sizer.Add(
            wx.StaticText(self, label="Control Point Color:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._control_dropdown = wx.Choice(self, choices=CONTROL_CHOICES)
        self._control_dropdown.SetSelection(0)
        self._sizer.Add(self._control_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._sizer.Add(
            wx.StaticText(self, label="Path Block:"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._path_dropdown = wx.Choice(self, choices=PATH_CHOICES)
        self._path_dropdown.SetSelection(0)
        self._sizer.Add(self._path_dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Spline Tension Slider ---
        self._sizer.Add(
            wx.StaticText(self, label="Spline Tension (loose <-> tight):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._tension_slider = wx.Slider(
            self, value=50, minValue=0, maxValue=100,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS
        )
        self._tension_slider.Bind(wx.EVT_SLIDER, self._on_tension_change)
        self._sizer.Add(self._tension_slider, 0, wx.ALL | wx.EXPAND, 5)

        # --- Clearance Controls ---
        self._sizer.Add(
            wx.StaticText(self, label="Clearance Width (blocks each side):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._width_spin = wx.SpinCtrl(self, min=0, max=10, initial=1)
        self._sizer.Add(self._width_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._sizer.Add(
            wx.StaticText(self, label="Clearance Height (blocks above):"),
            0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5
        )
        self._height_spin = wx.SpinCtrl(self, min=0, max=10, initial=3)
        self._sizer.Add(self._height_spin, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Options ---
        self._remove_markers_cb = wx.CheckBox(self, label="Remove markers after fill")
        self._remove_markers_cb.SetValue(True)
        self._sizer.Add(self._remove_markers_cb, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # --- Buttons (above status so they stay visible) ---
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._scan_button = wx.Button(self, label="Scan && Preview")
        self._scan_button.Bind(wx.EVT_BUTTON, self._on_scan)
        btn_sizer.Add(self._scan_button, 0, wx.ALL, 5)

        self._fill_button = wx.Button(self, label="Fill Path")
        self._fill_button.Bind(wx.EVT_BUTTON, self._on_fill)
        self._fill_button.Disable()
        btn_sizer.Add(self._fill_button, 0, wx.ALL, 5)

        self._sizer.Add(btn_sizer, 0, wx.ALIGN_CENTRE_HORIZONTAL)

        # --- Status Label (at bottom, can expand freely) ---
        self._status = wx.StaticText(self, label="Status: Ready. Create a selection and click Scan.")
        self._status.Wrap(250)
        self._sizer.Add(self._status, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

        # --- State ---
        self._path_voxels: Set[Tuple[int, int, int]] = set()
        self._clearance_voxels: Set[Tuple[int, int, int]] = set()
        self._ordered_path: List[Tuple[int, int, int]] = []
        self._constraint_stats: dict = {}
        self._marker_coords: List[Tuple[int, int, int]] = []
        self._ordered_points: List[Tuple[int, int, int]] = []
        self._scan_complete = False

    # -------------------------------------------------------------------------
    # Button Handlers
    # -------------------------------------------------------------------------

    def _on_scan(self, _):
        """Phase 1: Scan selection for markers, compute spline, show preview."""
        # Validate color selections are all different
        start_label = self._start_dropdown.GetStringSelection()
        end_label = self._end_dropdown.GetStringSelection()
        control_label = self._control_dropdown.GetStringSelection()

        start_color = WOOL_COLOR_MAP[start_label][0]
        end_color = WOOL_COLOR_MAP[end_label][0]
        control_color = WOOL_COLOR_MAP[control_label][0]

        if len({start_color, end_color, control_color}) < 3:
            self._set_status("Error: Start, end, and control colors must all be different.")
            return

        selection_group = self.canvas.selection.selection_group
        if selection_group is None or len(selection_group) == 0:
            self._set_status("Error: Create a selection box first.")
            return

        world = self.canvas.world
        dimension = self.canvas.dimension

        # Scan for markers
        start_pts, end_pts, control_pts = self.scan_markers(
            world, dimension, selection_group,
            start_color, end_color, control_color
        )

        # Validate results
        if len(start_pts) == 0:
            self._set_status(f"Error: No {start_label} (start) found in selection.")
            return
        if len(start_pts) > 1:
            self._set_status(f"Error: Found {len(start_pts)} start markers. Place exactly 1.")
            return
        if len(end_pts) == 0:
            self._set_status(f"Error: No {end_label} (end) found in selection.")
            return
        if len(end_pts) > 1:
            self._set_status(f"Error: Found {len(end_pts)} end markers. Place exactly 1.")
            return

        start = start_pts[0]
        end = end_pts[0]

        # Store all marker coordinates for optional removal
        self._marker_coords = [start] + control_pts + [end]

        # Order control points
        ordered_controls = self.order_control_points(start, end, control_pts)
        self._ordered_points = [start] + ordered_controls + [end]

        # Compute spline and rasterize
        self._recompute_path()

        self._scan_complete = True
        self._fill_button.Enable()

        num_controls = len(control_pts)
        fixes = self._constraint_stats.get("total_fixes", 0)
        fix_msg = f" Constraints applied {fixes} fix(es)." if fixes > 0 else ""
        self._set_status(
            f"Scan complete! Found {num_controls} control point(s). "
            f"Path: {len(self._path_voxels)} blocks. "
            f"Air clearance: {len(self._clearance_voxels)} blocks.{fix_msg} "
            f"Ready to fill."
        )

    def _on_fill(self, _):
        """Phase 2: Place path blocks and clear air."""
        if not self._scan_complete:
            return

        world = self.canvas.world
        dimension = self.canvas.dimension
        path_label = self._path_dropdown.GetStringSelection()
        path_block_name = WOOL_COLOR_MAP[path_label][1]
        remove_markers = self._remove_markers_cb.GetValue()

        # Capture state for the closure
        path_voxels = set(self._path_voxels)
        clearance_voxels = set(self._clearance_voxels)
        marker_coords = list(self._marker_coords)

        def operation():
            platform = world.level_wrapper.platform
            version_number = world.level_wrapper.version

            path_block = Block("minecraft", path_block_name)
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

            # Remove original markers if requested
            if remove_markers:
                for x, y, z in marker_coords:
                    # Only remove if not part of the path (don't undo our own work)
                    if (x, y, z) not in path_voxels:
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
        # if self._constraint_stats.get("total_fixes", 0) > 0:
        #     print(f"Constraint fixes applied: {self._constraint_stats}")
        print("Spline Rail Path Placer operation completed successfully.")

    def _on_tension_change(self, _):
        """Recompute spline when tension slider changes (if scan data exists)."""
        if not self._scan_complete or len(self._ordered_points) < 2:
            return

        self._recompute_path()
        fixes = self._constraint_stats.get("total_fixes", 0)
        fix_msg = f" Constraints: {fixes} fix(es)." if fixes > 0 else ""
        self._set_status(
            f"Tension updated. Path: {len(self._path_voxels)} blocks. "
            f"Air clearance: {len(self._clearance_voxels)} blocks.{fix_msg}"
        )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _recompute_path(self):
        """Recompute spline, rasterize, enforce constraints, and calculate clearance."""
        tension = self._tension_slider.GetValue() / 100.0
        width = self._width_spin.GetValue()
        height = self._height_spin.GetValue()

        spline_coords = self.catmull_rom_spline(self._ordered_points, tension)
        ordered_voxels = self.rasterize_to_voxels(spline_coords)
        self._ordered_path, self._constraint_stats = self.enforce_path_constraints(
            ordered_voxels
        )
        self._path_voxels = set(self._ordered_path)
        self._clearance_voxels = self.get_clearance_voxels(
            self._path_voxels, width, height
        )

    def _set_status(self, text: str):
        """Update the status label text."""
        self._status.SetLabel(f"Status: {text}")
        self._status.Wrap(250)
        self.Layout()

    # -------------------------------------------------------------------------
    # Core Logic (Static Methods)
    # -------------------------------------------------------------------------

    @staticmethod
    def scan_markers(
        world: "BaseLevel",
        dimension: Dimension,
        selection: SelectionGroup,
        start_color: str,
        end_color: str,
        control_color: str,
    ) -> Tuple[List[Tuple[int, int, int]], List[Tuple[int, int, int]], List[Tuple[int, int, int]]]:
        """
        Scan all blocks in the selection for wool markers.

        Returns (start_points, end_points, control_points) as lists of (x, y, z).
        """
        start_blockstate = f"universal_minecraft:wool[color={start_color}]"
        end_blockstate = f"universal_minecraft:wool[color={end_color}]"
        control_blockstate = f"universal_minecraft:wool[color={control_color}]"

        start_pts = []
        end_pts = []
        control_pts = []

        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        block = world.get_block(x, y, z, dimension)
                        bs = block.blockstate
                        if bs == start_blockstate:
                            start_pts.append((x, y, z))
                        elif bs == end_blockstate:
                            end_pts.append((x, y, z))
                        elif bs == control_blockstate:
                            control_pts.append((x, y, z))

        return start_pts, end_pts, control_pts

    @staticmethod
    def order_control_points(
        start: Tuple[int, int, int],
        end: Tuple[int, int, int],
        control_points: List[Tuple[int, int, int]],
    ) -> List[Tuple[int, int, int]]:
        """
        Order control points using nearest-neighbor chain starting from start.
        """
        if len(control_points) <= 1:
            return list(control_points)

        remaining = list(control_points)
        ordered = []
        current = start

        while remaining:
            distances = [
                math.sqrt(
                    (p[0] - current[0]) ** 2 +
                    (p[1] - current[1]) ** 2 +
                    (p[2] - current[2]) ** 2
                )
                for p in remaining
            ]
            nearest_idx = distances.index(min(distances))
            nearest = remaining.pop(nearest_idx)
            ordered.append(nearest)
            current = nearest

        return ordered

    @staticmethod
    def catmull_rom_spline(
        points: List[Tuple[int, int, int]],
        tension: float = 0.5,
        samples_per_unit: float = 2.0,
    ) -> np.ndarray:
        """
        Compute a 3D Catmull-Rom spline through the given points.

        Args:
            points: Ordered list of (x, y, z) coordinates to pass through.
            tension: 0.0 = loose curves, 1.0 = tight/linear.
            samples_per_unit: Number of samples per block of distance.

        Returns:
            np.ndarray of shape (N, 3) with float coordinates along the spline.
        """
        if len(points) < 2:
            return np.array(points, dtype=float)

        # For exactly 2 points, linear interpolation
        if len(points) == 2:
            p0 = np.array(points[0], dtype=float)
            p1 = np.array(points[1], dtype=float)
            dist = np.linalg.norm(p1 - p0)
            num_samples = max(int(dist * samples_per_unit), 2)
            t_vals = np.linspace(0.0, 1.0, num_samples)
            return np.outer(1.0 - t_vals, p0) + np.outer(t_vals, p1)

        pts = np.array(points, dtype=float)

        # Pad endpoints by duplicating first and last
        padded = np.vstack([pts[0:1], pts, pts[-1:]])

        all_samples = []
        num_segments = len(padded) - 3

        for i in range(1, len(padded) - 2):
            p0 = padded[i - 1]
            p1 = padded[i]
            p2 = padded[i + 1]
            p3 = padded[i + 2]

            segment_dist = np.linalg.norm(p2 - p1)
            num_samples = max(int(segment_dist * samples_per_unit), 2)

            # Don't include the last point of each segment except the final one
            include_end = (i == len(padded) - 3)
            t_vals = np.linspace(0.0, 1.0, num_samples, endpoint=include_end)

            tau = tension
            for t in t_vals:
                t2 = t * t
                t3 = t2 * t

                # Catmull-Rom basis functions with tension parameter
                q = (
                    p1
                    + (-tau * p0 + tau * p2) * t
                    + (2.0 * tau * p0 + (tau - 3.0) * p1 + (3.0 - 2.0 * tau) * p2 - tau * p3) * t2
                    + (-tau * p0 + (2.0 - tau) * p1 + (tau - 2.0) * p2 + tau * p3) * t3
                )
                all_samples.append(q)

        return np.array(all_samples)

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

        # Determine the driving axis
        if dx >= dy and dx >= dz:
            # X-dominant
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
            # Y-dominant
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
            # Z-dominant
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
    def rasterize_to_voxels(spline_coords: np.ndarray) -> List[Tuple[int, int, int]]:
        """
        Convert continuous spline coordinates to discrete block positions.
        Uses rounding + Bresenham gap-filling to ensure a connected path.

        Returns an ordered list (deduplicated, preserving spline traversal order).
        """
        if len(spline_coords) == 0:
            return []

        ordered = []
        seen = set()
        prev = None

        for coord in spline_coords:
            current = (int(round(coord[0])), int(round(coord[1])), int(round(coord[2])))

            # Fill gaps between consecutive samples using Bresenham
            if prev is not None and prev != current:
                dx = abs(current[0] - prev[0])
                dy = abs(current[1] - prev[1])
                dz = abs(current[2] - prev[2])
                if dx > 1 or dy > 1 or dz > 1:
                    gap_voxels = SplineRailPathPlacer.bresenham_3d(prev, current)
                    for gv in gap_voxels:
                        if gv not in seen:
                            ordered.append(gv)
                            seen.add(gv)

            # Add current after any gap fills
            if current not in seen:
                ordered.append(current)
                seen.add(current)

            prev = current

        return ordered

    @staticmethod
    def enforce_path_constraints(
        path: List[Tuple[int, int, int]],
    ) -> Tuple[List[Tuple[int, int, int]], dict]:
        """
        Validate and fix the rasterized path to comply with rail placer rules.

        Runs constraint fixes in order:
          9e. Gap prevention
          9a. Vertical stacking prevention
          9b. Elevation step normalization
          9g. Diagonal path prevention
          9c. Turn flatness enforcement
          9d. Turn-to-incline buffer insertion
          9f. Branch/ambiguity prevention

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
            return (dx != 0) != (dz != 0)  # exactly one is non-zero

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
        # Verify every consecutive pair is within 1 block on all axes
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = abs(nxt[0] - curr[0])
            dy = abs(nxt[1] - curr[1])
            dz = abs(nxt[2] - curr[2])
            if dx > 1 or dy > 1 or dz > 1:
                # Fill gap with Bresenham
                gap = SplineRailPathPlacer.bresenham_3d(curr, nxt)
                for j, gv in enumerate(gap[:-1]):  # exclude last (it's nxt)
                    fixed.insert(i + 1 + j, gv)
                # print(f"  9e: gap at [{i}] {curr} -> {nxt}, inserted {len(gap)-1} blocks")
                stats["gaps_filled"] += len(gap) - 1
                i += len(gap)
            else:
                i += 1

        if stats["gaps_filled"]:
            _log_path("AFTER 9e (gap prevention)")

        # --- 9a. REMOVED (v2) ---
        # Vertical stack prevention moved to post-filter (phase 10).

        # --- 9b. Elevation Step Normalization ---
        # Every elevation change must be dy=±1 with exactly one cardinal axis
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dy != 0:
                # Both dx and dz non-zero during elevation change — fix
                if dx != 0 and dz != 0:
                    # Split into: first move on dominant horizontal axis + dy,
                    # then move on the other axis at the new Y
                    if abs(dx) >= abs(dz):
                        step_dx = 1 if dx > 0 else -1
                        step_dy = 1 if dy > 0 else -1
                        mid = (curr[0] + step_dx, curr[1] + step_dy, curr[2])
                    else:
                        step_dz = 1 if dz > 0 else -1
                        step_dy = 1 if dy > 0 else -1
                        mid = (curr[0], curr[1] + step_dy, curr[2] + step_dz)
                    # print(f"  9b: elev+dual-axis at [{i}] {curr} -> {nxt} (dx={dx},dy={dy},dz={dz}), inserted mid={mid}")
                    fixed.insert(i + 1, mid)
                    stats["elevation_steps_fixed"] += 1
                    i += 1
                # dy magnitude > 1 — break into single steps
                elif abs(dy) > 1:
                    step_dy = 1 if dy > 0 else -1
                    step_dx = 1 if dx > 0 else (-1 if dx < 0 else 0)
                    step_dz = 1 if dz > 0 else (-1 if dz < 0 else 0)
                    # If no horizontal movement, pick one from context
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
                    # print(f"  9b: elev multi-step at [{i}] {curr} -> {nxt} (dy={dy}), inserted mid={mid}")
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
        # Pure diagonal steps (both dx!=0 and dz!=0, dy=0) that aren't part of
        # a turn pattern get converted to L-shaped steps
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dx != 0 and dz != 0 and dy == 0:
                # Check if this is part of a valid turn (3-block pattern)
                # A valid turn requires single-cardinal steps on both sides,
                # on perpendicular axes, all at the same Y level
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
                    # Both sides must be single-cardinal, flat, and perpendicular
                    if (_is_single_cardinal(d_prev_x, d_prev_z) and
                            _is_single_cardinal(d_after_x, d_after_z) and
                            d_prev_y == 0 and d_after_y == 0 and
                            prev[1] == curr[1] == nxt[1] == after[1]):
                        prev_axis = 'x' if d_prev_x != 0 else 'z'
                        after_axis = 'x' if d_after_x != 0 else 'z'
                        if prev_axis != after_axis:
                            is_turn = True
                if not is_turn:
                    # Convert to L-shape: move on X first, then Z
                    mid = (nxt[0], curr[1], curr[2])
                    # print(f"  9g: diagonal at [{i}] {curr} -> {nxt} (dx={dx},dz={dz}), inserted mid={mid}")
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
        # Reshape the last few zigzag blocks before each elevation change
        # so all minor-axis movement happens first, then a straight run
        # in the ascending direction provides the 2-block buffer.
        # The zigzag L-corner preserves diagonal adjacency for turn detection.
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dy = nxt[1] - curr[1]
            if dy != 0 and _is_single_cardinal(nxt[0] - curr[0], nxt[2] - curr[2]):
                # Elevation change with single-cardinal horizontal component
                adx = nxt[0] - curr[0]
                adz = nxt[2] - curr[2]
                elev_y = curr[1]

                # The "major axis" is the one matching the ascending direction
                major_is_x = (adx != 0)

                # Look backward to find how far we can reshape (same Y, no elevation)
                reshape_start = i
                for j in range(i - 1, max(i - 8, -1), -1):
                    if j < 0:
                        break
                    if fixed[j][1] != elev_y:
                        break
                    reshape_start = j

                # Calculate total displacement of the reshape section
                start_pt = fixed[reshape_start]
                end_pt = fixed[i]  # last block before ascending
                total_dx = end_pt[0] - start_pt[0]
                total_dz = end_pt[2] - start_pt[2]

                if major_is_x:
                    major_disp = abs(total_dx)
                    minor_disp = abs(total_dz)
                else:
                    major_disp = abs(total_dz)
                    minor_disp = abs(total_dx)

                # Need at least 3 blocks on the major axis (turn exit + 2 buffer)
                # If not enough, extend reshape_start further back
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

                # Only reshape if we have enough displacement
                if major_disp >= 3 and minor_disp >= 1:
                    # Build replacement: minor axis first, then major axis
                    y = elev_y
                    x, z = start_pt[0], start_pt[2]
                    replacement = [start_pt]

                    if major_is_x:
                        # Z movement first, then X movement
                        sz = 1 if total_dz > 0 else -1
                        for _ in range(abs(total_dz)):
                            z += sz
                            replacement.append((x, y, z))
                        sx = 1 if total_dx > 0 else -1
                        for _ in range(abs(total_dx)):
                            x += sx
                            replacement.append((x, y, z))
                    else:
                        # X movement first, then Z movement
                        sx = 1 if total_dx > 0 else -1
                        for _ in range(abs(total_dx)):
                            x += sx
                            replacement.append((x, y, z))
                        sz = 1 if total_dz > 0 else -1
                        for _ in range(abs(total_dz)):
                            z += sz
                            replacement.append((x, y, z))

                    # Verify the replacement ends at the correct position
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
        # Turns (direction changes) must have dy=0 across all 3 blocks
        # Only triggers on genuine turns: single-cardinal incoming AND outgoing
        # on perpendicular axes. Skips diagonal or ascending transitions.
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
            # Both steps must be single-cardinal, flat (dy==0), and perpendicular
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
                    # print(f"  9c: turn flatten at [{i}] prev={prev} curr={curr}->{(curr[0],target_y,curr[2])} nxt={nxt}->{(nxt[0],target_y,nxt[2])}")
                    fixed[i] = (curr[0], target_y, curr[2])
                    fixed[i + 1] = (nxt[0], target_y, nxt[2])
                    stats["turns_flattened"] += 1
                i += 2
            else:
                i += 1

        if stats["turns_flattened"]:
            _log_path("AFTER 9c (turn flatness)")

        # --- 10. Post-Filter: Vertical Stack Cleanup ---
        # Runs after all path shaping is complete. Detects vertical stacks
        # (same X,Z, only Y differs) and shifts the second block 1 unit
        # horizontally in the departure direction. Minimal, surgical fix
        # that preserves curve shape.
        path_positions = set(fixed)
        i = 0
        while i < len(fixed) - 1:
            curr = fixed[i]
            nxt = fixed[i + 1]
            dx = nxt[0] - curr[0]
            dy = nxt[1] - curr[1]
            dz = nxt[2] - curr[2]
            if dx == 0 and dz == 0 and dy != 0:
                # Try departure direction first, then approach, then cardinals
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
                    # Check it doesn't collide with other path blocks
                    # (except fixed[i+2] which we might merge with)
                    if shifted in path_positions and shifted != nxt:
                        if i + 2 < len(fixed) and shifted == fixed[i + 2]:
                            pass  # will merge below
                        else:
                            continue
                    # Apply the shift
                    path_positions.discard(nxt)
                    path_positions.add(shifted)
                    fixed[i + 1] = shifted
                    stats["vertical_stacks_fixed"] += 1
                    print(f"  10: vstack fix [{i}]->[{i+1}] shifted {nxt} -> {shifted}")
                    # Merge if shifted == next block
                    if i + 2 < len(fixed) and fixed[i + 1] == fixed[i + 2]:
                        path_positions.discard(fixed[i + 2])
                        fixed.pop(i + 2)
                        print(f"  10: merged duplicate at [{i+2}]")
                    break
            i += 1

        # --- 10b. Post-Filter: Knot Detection ---
        # Flag blocks where a non-adjacent path block falls within the
        # 3x3x3 cube, creating ambiguity for the rail placer.
        for i in range(len(fixed)):
            for j in range(i + 3, len(fixed)):
                bx = abs(fixed[j][0] - fixed[i][0])
                by = abs(fixed[j][1] - fixed[i][1])
                bz = abs(fixed[j][2] - fixed[i][2])
                if bx <= 1 and by <= 1 and bz <= 1:
                    print(f"  10b: KNOT at [{i}] {fixed[i]} <-> [{j}] {fixed[j]} (dist {j-i} apart in path)")

        # --- 10c. Post-Filter: Gap Detection ---
        # Consecutive blocks must be adjacent (each axis differs by at most 1,
        # total manhattan distance at most 2).
        for i in range(len(fixed) - 1):
            curr = fixed[i]
            nxt = fixed[i + 1]
            adx = abs(nxt[0] - curr[0])
            ady = abs(nxt[1] - curr[1])
            adz = abs(nxt[2] - curr[2])
            if max(adx, ady, adz) > 1 or adx + ady + adz > 2:
                print(f"  10c: GAP at [{i}]->[{i+1}] {curr} -> {nxt} (d={adx},{ady},{adz})")

        # --- 10d. Post-Filter: Turn Before Elevation ---
        # A direction change immediately before a Y transition confuses the
        # rail placer. Flag when the step into a Y-change is on a different
        # axis than the step before it.
        for i in range(2, len(fixed)):
            curr = fixed[i - 1]
            nxt = fixed[i]
            dy = nxt[1] - curr[1]
            if dy == 0:
                continue
            # There's a Y transition at i-1 -> i. Check if i-2 -> i-1 is a turn.
            prev = fixed[i - 2]
            d1x = curr[0] - prev[0]
            d1z = curr[2] - prev[2]
            d2x = nxt[0] - curr[0]
            d2z = nxt[2] - curr[2]
            # Both steps have horizontal movement, but on different axes = turn
            if d1x != 0 and d2z != 0 and d1z == 0 and d2x == 0:
                print(f"  10d: TURN BEFORE ELEV at [{i-2}]->[{i}] {prev}->{curr}->{nxt}")
            elif d1z != 0 and d2x != 0 and d1x == 0 and d2z == 0:
                print(f"  10d: TURN BEFORE ELEV at [{i-2}]->[{i}] {prev}->{curr}->{nxt}")

        if stats["vertical_stacks_fixed"]:
            _log_path("AFTER 10 (post-filter cleanup)")

        # --- 9d. Turn-to-Incline Buffer (Minimum 2 Flat Blocks) ---
        # DISABLED: Buffer insertion creates disconnected stubs because inserted
        # blocks extend in the turn's exit direction but don't connect to the
        # next path segment. Needs a fundamentally different approach (e.g.,
        # reshaping existing path rather than inserting new blocks).
        # TODO: Revisit in a future session.

        # --- 9f. Branch/Ambiguity Prevention ---
        # No voxel should have more than 2 neighbors in the path
        path_set = set(fixed)
        to_remove = set()
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
            # In an ordered list, a block should connect to at most 2 others
            # If it has 3+ neighbors, it's a branch point — we keep it but flag it
            # (Pruning branches from an ordered list is complex; the ordered list
            #  itself prevents true branches. We just validate here.)
            if neighbors_in_path > 2:
                # print(f"  9f: branch at [{i}] {v} has {neighbors_in_path} neighbors in path")
                stats["branches_pruned"] += 1

        # Remove duplicate consecutive entries that may have been introduced
        deduped = [fixed[0]]
        for v in fixed[1:]:
            if v != deduped[-1]:
                deduped.append(v)
        fixed = deduped

        stats["total_fixes"] = sum(v for v in stats.values())
        return fixed, stats

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
            # Same level as path: side clearance only
            for dx in range(-width, width + 1):
                for dz in range(-width, width + 1):
                    if dx == 0 and dz == 0:
                        continue  # skip the path block itself
                    clearance.add((x + dx, y, z + dz))

            # Above the path: full width + height
            for dy in range(1, height + 1):
                for dx in range(-width, width + 1):
                    for dz in range(-width, width + 1):
                        clearance.add((x + dx, y + dy, z + dz))

        # Remove any voxels that are part of the path itself
        clearance -= path_voxels

        return clearance


export = {
    "name": "Spline Rail Path Placer v2",
    "operation": SplineRailPathPlacerV2,
}
