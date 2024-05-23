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

        # Add a SpinCtrl for the number of iterations
        self._num_iterations = wx.SpinCtrl(self, min=-512, max=512, initial=1)
        self._sizer.Add(self._num_iterations, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

    def _run_operation(self, _):
        num_iterations = self._num_iterations.GetValue()  # get the number of iterations from the SpinCtrl

        selection_group = self.canvas.selection.selection_group

        upper_tunnel_selection_group = []
        x_tunnel_widths = {0: 2, 1: 4, 2: 5, 3: 6, 4: 6, 5: 6, 6: 6, 7: 5, 8: 4, 9: 2}  # mapping of Y levels to X widths in "Y-level: X-width" format
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                for y in range(3, 10):  # fixed range of ten Y levels
                    x_extension = x_tunnel_widths.get(y, 0)  # get the X width for the Y level, default to 0
                    upper_tunnel_selection_group.append(
                        SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                    )

        lower_tunnel_selection_group = []
        x_tunnel_widths = {0: 2, 1: 4, 2: 5, 3: 6, 4: 6, 5: 6, 6: 6, 7: 5, 8: 4, 9: 2}  # mapping of Y levels to X widths in "Y-level: X-width" format
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                for y in range(0, 3):  # fixed range of ten Y levels
                    x_extension = x_tunnel_widths.get(y, 0)  # get the X width for the Y level, default to 0
                    lower_tunnel_selection_group.append(
                        SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                    )

        air_selection_group = []
        x_air_widths = {0: 0, 1: 0, 2: 0, 3: 5, 4: 5, 5: 5, 6: 5, 7: 3, 8: 2, 9: 0}  # mapping of Y levels to X widths in "Y-level: X-width" format
        for box in selection_group:
            for z in range(num_iterations):
                for y in range(3,9):
                    x_extension = x_air_widths.get(y, 0)
                    air_selection_group.append(
                        SelectionBox((box.min[0] - x_extension, y + box.min[1], box.min[2] + z), (box.max[0] + x_extension, y + box.min[1] + 1, box.max[2] + z))
                    )

        stair1_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 3  # fixed Y level
                x_extension_1 = 1  # fixed X extension
                stair1_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_1, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_1, y + box.min[1] + 1, box.max[2] + z))
                )
                x_extension_2 = -3  # fixed X extension
                stair1_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_2, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_2, y + box.min[1] + 1, box.max[2] + z))
                )

        stair2_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 3  # fixed Y level
                x_extension_3 = 3  # fixed X extension
                stair2_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_3, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_3, y + box.min[1] + 1, box.max[2] + z))
                )
                x_extension_4 = -1  # fixed X extension
                stair2_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_4, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_4, y + box.min[1] + 1, box.max[2] + z))
                )                

        stair3_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 3  # fixed Y level
                x_extension_5 = -5  # fixed X extension
                stair3_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_5, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_5, y + box.min[1] + 1, box.max[2] + z))
                )

        stair4_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 6  # fixed Y level, lower
                x_extension_5 = -5  # fixed X extension
                stair4_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_5, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_5, y + box.min[1] + 1, box.max[2] + z))
               )
                y = 8  # fixed Y level, upper
                x_extension_6 = -2  # fixed X extension
                stair4_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_6, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_6, y + box.min[1] + 1, box.max[2] + z))
               )
                
        stair5_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 3  # fixed Y level
                x_extension_7 = 5  # fixed X extension
                stair5_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_7, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_7, y + box.min[1] + 1, box.max[2] + z))
                )                

        stair6_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 6  # fixed Y level, lower
                x_extension_7 = 5  # fixed X extension
                stair6_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_7, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_7, y + box.min[1] + 1, box.max[2] + z))
               )
                y = 8  # fixed Y level, upper
                x_extension_8 = 2  # fixed X extension
                stair6_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_8, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_8, y + box.min[1] + 1, box.max[2] + z))
               )
                
        track_base_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 3  # fixed Y level
                x_extension_3 = 2  # fixed X extension
                track_base_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_3, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_3, y + box.min[1] + 1, box.max[2] + z))
                )
                x_extension_4 = -2  # fixed X extension
                track_base_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_4, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_4, y + box.min[1] + 1, box.max[2] + z))
                )    

        rails_selection_group = []
        for box in selection_group:
            for z in range(num_iterations):  # iterate over the Z direction
                y = 4  # fixed Y level
                x_extension_3 = 2  # fixed X extension
                rails_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_3, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_3, y + box.min[1] + 1, box.max[2] + z))
                )
                x_extension_4 = -2  # fixed X extension
                rails_selection_group.append(
                    SelectionBox((box.min[0] - x_extension_4, y + box.min[1], box.min[2] + z), (box.max[0] - x_extension_4, y + box.min[1] + 1, box.max[2] + z))
                )   

        upper_tunnel_selection_group = SelectionGroup(upper_tunnel_selection_group)
        lower_tunnel_selection_group = SelectionGroup(lower_tunnel_selection_group)
        air_selection_group = SelectionGroup(air_selection_group)
        stair1_selection_group = SelectionGroup(stair1_selection_group)
        stair2_selection_group = SelectionGroup(stair2_selection_group)
        stair3_selection_group = SelectionGroup(stair3_selection_group)
        stair4_selection_group = SelectionGroup(stair4_selection_group)
        stair5_selection_group = SelectionGroup(stair5_selection_group)
        stair6_selection_group = SelectionGroup(stair6_selection_group)
        track_base_selection_group = SelectionGroup(track_base_selection_group)
        rails_selection_group = SelectionGroup(rails_selection_group)

        def operation():
            self.upper_tunnel_at_selection_coordinates(self.world, self.canvas.dimension, upper_tunnel_selection_group)            
            self.lower_tunnel_at_selection_coordinates(self.world, self.canvas.dimension, lower_tunnel_selection_group)
            self.air_at_selection_coordinates(self.world, self.canvas.dimension, air_selection_group)
            self.stair1_at_selection_coordinates(self.world, self.canvas.dimension, stair1_selection_group)
            self.stair2_at_selection_coordinates(self.world, self.canvas.dimension, stair2_selection_group)
            self.stair3_at_selection_coordinates(self.world, self.canvas.dimension, stair3_selection_group)
            self.stair4_at_selection_coordinates(self.world, self.canvas.dimension, stair4_selection_group)
            self.stair5_at_selection_coordinates(self.world, self.canvas.dimension, stair5_selection_group)
            self.stair6_at_selection_coordinates(self.world, self.canvas.dimension, stair6_selection_group)
            self.track_base_at_selection_coordinates(self.world, self.canvas.dimension, track_base_selection_group)
            self.rails_at_selection_coordinates(self.world, self.canvas.dimension, rails_selection_group)

        # Add the operation to the operation manager
        self.canvas.run_operation(operation)

        print("Operation completed successfully.")

    pass

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
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            #world.set_version_block(x, y, z, dimension, 'universal_minecraft:air', {})
                            #print(f"Block type: {block.blockstate} at coordinates: ({x}, {y}, {z})")
                            world.set_version_block(x, y, z, dimension, (platform, version_number), tunnel_block, None)
                        #print(f"Block type: {block.blockstate} at coordinates: ({x}, {y}, {z})")
                            pass
        pass

    @staticmethod
    def lower_tunnel_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):
        tunnel_block = Block('minecraft', 'deepslate_tiles')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        # block = world.get_block(x, y, z, dimension)  # get the existing block at the coordinate
                        world.set_version_block(x, y, z, dimension, (platform, version_number), tunnel_block, None)
                        pass
        pass

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
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            #world.set_version_block(x, y, z, dimension, 'universal_minecraft:air', {})
                            #print(f"Block type: {block.blockstate} at coordinates: ({x}, {y}, {z})")
                            world.set_version_block(x, y, z, dimension, (platform, version_number), air_block, None)
                        #print(f"Block type: {block.blockstate} at coordinates: ({x}, {y}, {z})")
                            pass
        pass

    @staticmethod
    def stair1_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair1_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(1)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        world.set_version_block(x, y, z, dimension, (platform, version_number), stair1_block, None)
                        pass
        pass

    @staticmethod
    def stair2_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair2_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(0)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        world.set_version_block(x, y, z, dimension, (platform, version_number), stair2_block, None)
                        pass
        pass

    @staticmethod
    def stair3_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair3_block = Block('minecraft', 'deepslate_tile_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(0)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        x = x + 1
                        block = world.get_block(x, y, z, dimension)  # get the block at the coordinate
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            x = x -1
                            world.set_version_block(x, y, z, dimension, (platform, version_number), stair3_block, None)
                        pass
        pass

    @staticmethod
    def stair4_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair4_block = Block('minecraft', 'deepslate_tile_stairs', {"upside_down_bit": ByteTag(1), "weirdo_direction": IntTag(0)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        x = x + 1
                        block = world.get_block(x, y, z, dimension)  # get the block at the coordinate
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            x = x - 1
                            world.set_version_block(x, y, z, dimension, (platform, version_number), stair4_block, None)
                        pass
        pass

    @staticmethod
    def stair5_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair5_block = Block('minecraft', 'deepslate_tile_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(1)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        x = x - 1
                        block = world.get_block(x, y, z, dimension)  # get the block at the coordinate
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            x = x + 1
                            world.set_version_block(x, y, z, dimension, (platform, version_number), stair5_block, None)
                        pass
        pass

    @staticmethod
    def stair6_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        stair6_block = Block('minecraft', 'deepslate_tile_stairs', {"upside_down_bit": ByteTag(1), "weirdo_direction": IntTag(1)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        x = x - 1
                        block = world.get_block(x, y, z, dimension)  # get the block at the coordinate
                        if block.blockstate == 'universal_minecraft:air':
                            pass
                        else:
                            x = x + 1
                            world.set_version_block(x, y, z, dimension, (platform, version_number), stair6_block, None)
                        pass
        pass

    @staticmethod
    def track_base_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        track_base_block = Block('minecraft', 'cobblestone')
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        world.set_version_block(x, y, z, dimension, (platform, version_number), track_base_block, None)
                        pass
        pass               

    @staticmethod
    def rails_at_selection_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup):

        # the properties of the "stairs" block are set through the very arcane "amulet_nbt" module's translation of String, Byte, and Int tags.
        # further reading is here:  https://amulet-nbt.readthedocs.io/en/3.0/
           
        rail_block = Block('minecraft', 'rail', {"rail_direction": IntTag(0)})
        # get the platform and version number of the game
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        world.set_version_block(x, y, z, dimension, (platform, version_number), rail_block, None)
                        pass
        pass    

export = {
    "name": "Tunnel North-South (+Z)",  # the name of the plugin
    "operation": Dig_Tunnel,  # the actual function to call when running the plugin
}
