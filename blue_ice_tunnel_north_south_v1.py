# Programmatic Tunneling Operation for Amulet
# Builds a "subway" style tunnel 10 blocks tall in the Positive Z Direction.
#
# Make sure your selection is only 1 block cubed -- it will be the bottom-center block of the 
# operation.  If you are at the end of a tunnel you have already dug, the offset from the center 
# of the lowest visible block of the tunnel is -3 Y.
#
# The iteration count is the number of times the operation will repeat in the Z direction.
# I've tested "digging" up to 512 blocks in the Z direction, but your mileage may vary.
#
# UI  and API Code from the Amulet Team
# All other code (c) 2024 Black Forest Creations
# Blame:  @lNQUlSlTlON

from typing import TYPE_CHECKING
import wx

from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block

from amulet_nbt import StringTag, IntTag, ByteTag

from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI

if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas

class Dig_Tunnel(wx.Panel, DefaultOperationUI):
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

        # Create a list of choices for the dropdown
        choices = ["Pos Z", "Diagonal -- +Z, -X", "Diagonal -- +Z, +X"]

        # Add a Choice control for the dropdown
        self._dropdown = wx.Choice(self, choices=choices)
        self._sizer.Add(self._dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "Pos X" as the default selection
        self._dropdown.SetSelection(0)
        
        # Add a SpinCtrl for the number of iterations
        self._num_iterations = wx.SpinCtrl(self, min=-512, max=512, initial=1)
        self._sizer.Add(self._num_iterations, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

    def _run_operation(self, _):
        dir_choice = self._dropdown.GetStringSelection() # get the block choice from the dropdown        
        num_iterations = self._num_iterations.GetValue()  # get the number of iterations from the SpinCtrl
        selection_group = self.canvas.selection.selection_group

        upper_tunnel_selection_group = []
        if dir_choice == "Pos Z":        
        # Use wider tunnel for glass panes on the sides of the tunnel
    #        x_tunnel_widths = {0: 3, 1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3}  # mapping of Y levels to X widths in "Y-level: X-width" format
            x_tunnel_widths = {0: 2, 1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2}  # mapping of Y levels to X widths in "Y-level: X-width" format
        elif dir_choice == "Diagonal -- +Z, -X" or dir_choice == "Diagonal -- +Z, +X":
            x_tunnel_widths = {0: 4, 1: 4, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4}

        for box in selection_group:
            cur_iter = 0
            for z in range(num_iterations):  # iterate over the Z direction
                for y in range(0, 6):  # fixed range of ten Y levels
                    x_extension = x_tunnel_widths.get(y, 0)  # get the X width for the Y level, default to 0
                    if dir_choice == "Pos Z":
                        upper_tunnel_selection_group.append(
                            SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                        )
                    elif dir_choice == "Diagonal -- +Z, -X":
                        upper_tunnel_selection_group.append(
                            SelectionBox((box.min[0] - x_extension - cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension - cur_iter, y + box.min[1] + 1, box.max[2] + z))
                        )
                    elif dir_choice == "Diagonal -- +Z, +X":
                        upper_tunnel_selection_group.append(
                            SelectionBox((box.min[0] - x_extension + cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension + cur_iter, y + box.min[1] + 1, box.max[2] + z))
                        )
                cur_iter += 1                        

        lower_tunnel_selection_group = []
        if dir_choice == "Pos Z":         
            x_tunnel_widths = {0: 0, 1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}  # mapping of Y levels to X widths in "Y-level: X-width" format
        elif dir_choice == "Diagonal -- +Z, -X" or dir_choice == "Diagonal -- +Z, +X":
            x_tunnel_widths = {0: 0, 1: 3, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}  # mapping of Y levels to X widths in "Y-level: X-width" format                        
        for box in selection_group:
            cur_iter = 0
            for z in range(num_iterations):  # iterate over the Z direction
                y = 1  # fixed range of ten Y levels
                x_extension = x_tunnel_widths.get(y, 0)  # get the X width for the Y level, default to 0
                if dir_choice == "Pos Z":
                    lower_tunnel_selection_group.append(
                        SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                    )
                elif dir_choice == "Diagonal -- +Z, -X":
                    lower_tunnel_selection_group.append(
                        SelectionBox((box.min[0] - x_extension - cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension - cur_iter, y + box.min[1] + 1, box.max[2] + z))
                    )
                elif dir_choice == "Diagonal -- +Z, +X":
                    lower_tunnel_selection_group.append(
                        SelectionBox((box.min[0] - x_extension + cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension + cur_iter, y + box.min[1] + 1, box.max[2] + z))
                    )
                cur_iter += 1    

        air_selection_group = []
        if dir_choice == "Pos Z": 
        # Use wider tunnel for glass panes on the sides of the tunnel        
    #        x_air_widths = {0: 0, 1: 0, 2: 2, 3: 2, 4: 2, 5: 2, 6: 0}  # mapping of Y levels to X widths in "Y-level: X-width" format
            x_air_widths = {0: 0, 1: 0, 2: 1, 3: 1, 4: 1, 5: 1, 6: 0}  # mapping of Y levels to X widths in "Y-level: X-width" format
        elif dir_choice == "Diagonal -- +Z, -X" or dir_choice == "Diagonal -- +Z, +X":
            x_air_widths = {0: 0, 1: 0, 2: 3, 3: 3, 4: 3, 5: 3, 6: 0}
        for box in selection_group:
            cur_iter = 0
            for z in range(num_iterations):
                for y in range(2,5):
                    x_extension = x_air_widths.get(y, 0)
                    if dir_choice == "Pos Z":
                        air_selection_group.append(
                            SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                        )
                    elif dir_choice == "Diagonal -- +Z, -X":
                        air_selection_group.append(
                            SelectionBox((box.min[0] - x_extension - cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension - cur_iter, y + box.min[1] + 1, box.max[2] + z))
                        )
                    elif dir_choice == "Diagonal -- +Z, +X":
                        air_selection_group.append(
                            SelectionBox((box.min[0] - x_extension + cur_iter, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension + cur_iter, y + box.min[1] + 1, box.max[2] + z))
                        )
                cur_iter += 1

    ## Uncomment for glass panes on the sides of the tunnel
        # stair1_selection_group = []
        # for box in selection_group:
        #     for z in range(num_iterations):  # iterate over the Z direction
        #         y = 2  # fixed Y level
        #         x_extension_1 = -2  # fixed X extension
        #         stair1_selection_group.append(
        #             SelectionBox((box.min[0] - x_extension_1, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_1, y + box.min[1] + 1, box.max[2] + z))
        #         )
        #         x_extension_2 = 2  # fixed X extension
        #         stair1_selection_group.append(
        #             SelectionBox((box.min[0] - x_extension_2, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_2, y + box.min[1] + 1, box.max[2] + z))
        #         )


        upper_tunnel_selection_group = SelectionGroup(upper_tunnel_selection_group)
        lower_tunnel_selection_group = SelectionGroup(lower_tunnel_selection_group)
        air_selection_group = SelectionGroup(air_selection_group)
    # Uncomment for glass panes on the sides of the tunnel    
        #stair1_selection_group = SelectionGroup(stair1_selection_group)

        def operation():
            self.upper_tunnel_at_selection_coordinates(self.world, self.canvas.dimension, upper_tunnel_selection_group)            
            self.air_at_selection_coordinates(self.world, self.canvas.dimension, air_selection_group)
            self.lower_tunnel_at_selection_coordinates(self.world, self.canvas.dimension, lower_tunnel_selection_group)
            # Uncomment for glass panes on the sides of the tunnel
            # self.stair1_at_selection_coordinates(self.world, self.canvas.dimension, stair1_selection_group)


        # Add the operation to the operation manager
        self.canvas.run_operation(operation)

        print("Operation completed successfully.")

    

    @staticmethod
    def upper_tunnel_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):
        tunnel_block = Block('minecraft', 'deepslate_tiles')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        block = world.get_block(x, y, z, dimension)  # get the existing block at the coordinate
                        world.set_version_block(x, y, z, dimension, (platform, version_number), tunnel_block, None)
        return

    @staticmethod
    def lower_tunnel_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):
        ice_block = Block('minecraft', 'blue_ice')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        # block = world.get_block(x, y, z, dimension)  # get the existing block at the coordinate
                        world.set_version_block(x, y, z, dimension, (platform, version_number), ice_block, None)
                        
        return

    @staticmethod
    def air_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):
        air_block = Block('minecraft', 'air')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        block = world.get_block(x, y, z, dimension)  # get the block at the coordinate
                        world.set_version_block(x, y, z, dimension, (platform, version_number), air_block, None)

        return

    @staticmethod
    def stair1_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair1_block = Block('minecraft', 'glass_pane')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        world.set_version_block(x, y, z, dimension, (platform, version_number), stair1_block, None)
                        
        return


export = {
    "name": "Blue Ice Tunnel North-South (+Z)",  # the name of the plugin
    "operation": Dig_Tunnel,  # the actual function to call when running the plugin
}
