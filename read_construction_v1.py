# Programmatic Rail and Roadbed Placer
# Place rails along a path you define, with a roadbed underneath. 
#
# Make sure your selection is only 1 block tall in all dimensions.
# Pink Wool is the path definition block
#
# UI and API Code from the Amulet Team
# All other code (c) 2024 Black Forest Creations
# Blame:  @lNQUlSlTlON

import os
import json
import numpy as np
import wx
import amulet_nbt

from typing import TYPE_CHECKING

# Amulet Construction OpenSource
from construction import ConstructionReader, ConstructionSection
# Amulet Core and Map Editor
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI
from amulet.api.wrapper import Interface
from amulet.level import load_level
from amulet.api.data_types import Dimension
from amulet.api.errors import LoaderNoneMatched
from amulet.operations.paste import paste


if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas


class Paste_At_Selection(wx.Panel, DefaultOperationUI):
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

        # Add a spacer of 10 pixels
        self._sizer.AddSpacer(10)        

        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

    def _run_operation(self, _):
        selection_group = self.canvas.selection.selection_group
        world = self.canvas.world  # get the world object
        dimension = self.canvas.dimension
        directory = os.getcwd()
        print(directory)

        src_file_path=f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\3x3_pier_EastWest.construction"

        def operation():
            construction_blocks = self.read_construction(src_file_path)

            print('construction blocks dictionary:', construction_blocks)

        # Add the operation to the operation manager
        self.canvas.run_operation(operation)
        print("Operation completed successfully.") 

    @staticmethod
    def read_construction(src_file_path):
        construction_blocks = []
        print('source file path:', src_file_path)
        with ConstructionReader(src_file_path) as reader:

            construction_blocks = reader.read(0).palette
        # Debug print statement    
            for i in range(len(construction_blocks)):
                print('block:', i, ' = ', construction_blocks[i])

            offset_x, offset_y, offset_z = 0 - reader.read(0).sx, 0 - reader.read(0).sy, 0 - reader.read(0).sz
        # Debug print statement    
            # print('offsets:', offset_x, offset_y, offset_z)

            for i in range(len(reader.sections)):
            # the "reader.read(i)" call pulls from the "construction.py" file's "ConstructionReader" class:"read" method
            # the method returns the origina coords, shape, and an array of blocks in the section where the integer
            # for each block corresponse to the index in the "palette" list
                section = reader.read(i)
                origin_x, origin_y, origin_z = section.sx, section.sy, section.sz
            # Debug print statement    
                # print('section origin:', origin_x, origin_y, origin_z)
        ###
        ###  Woot! Getting the block types from the construction file and in a matrix
        ###  Last step is to normalize the X,Z coords to "0, 0" and build a matrix of
        ###  all of the blocks.  That can then be used with the "set_blocks" method
        ###  The "offset" should be calculated once based on the first section's origin being 0,0,0
        ###  For now, this will iterate only X, Z and not Y.
        ###    
                normalized_origin_x, normalized_origin_y, normalized_origin_z = origin_x + offset_x, origin_y + offset_y, origin_z + offset_z
            # Debug print statement
                # print('normalized origin:', normalized_origin_x, normalized_origin_y, normalized_origin_z)
                shape = section.shape
            # Debug print statement
                # print(shape)
                block_array = section.blocks
            ## The following section takes the numpy array that is being returned from the construction file and
            ## converts it to an entry per block in the array that can be used with the "set_block" method
                for x in range(len(block_array)):
                    for z in range(len(block_array[x][0])):
                        block_value = block_array[x][0][z]
                        block_type = construction_blocks[block_value]
                    ## The block_type is a string that needs to be parsed to be used with the "set_block" method
                    ## The "parse_block_type" method will take the string and return a string that can be used
                    ## without further formatting in the origin script that calls this Class     
                        parsed_block = Paste_At_Selection.parse_block_type(block_type)
                    # Block dump debug from the construction file    
                        # print('block at position', normalized_origin_x + x, normalized_origin_z + z, '=', parsed_block)
                        construction_blocks.append({'x': normalized_origin_x + x, 'y': normalized_origin_y, 'z': normalized_origin_z + z, 'block': parsed_block})

        return construction_blocks
        ###
        ###  world.set_version_block(x, y, z, dimension, (platform, version_number), stair_eastwest_1_block, None)
        ###

    @staticmethod
    def parse_block_type(block_type):
        parsed_block_type = str(block_type)
        library = parsed_block_type[0: parsed_block_type.find(':')]
    # Debug print statement    
        # print('library:', library)        
        family = parsed_block_type[parsed_block_type.find(':') + 1: parsed_block_type.find('[')]
    # Debug print statement
        # print('family:', family)
        if '__version__=18100737' in parsed_block_type:
            if parsed_block_type.find('[') + 21 < len(parsed_block_type) and parsed_block_type[parsed_block_type.find('[') + 21] == ',':
                block_tags = parsed_block_type[parsed_block_type.find(',') + 1: parsed_block_type.find(']')]
            # Debug print statement
                # print('block tags:', block_tags)
                if 'wall' in block_tags:
                    split_tags = block_tags.split(',')
                    east = split_tags[0].split('"')[1]
                    north = split_tags[1].split('"')[1]
                    south = split_tags[2].split('"')[1]
                    west = split_tags[3].split('"')[1]
                    post = split_tags[4].split('=')[1]
                # Debug print statement                     
                    # print('wall tags:', east, north, south, west, post)
                    parsed_block = "Block('{}', '{}', {{\"wall_connection_type_east\": StringTag(\"{}\"), \"wall_connection_type_north\": StringTag(\"{}\"), \"wall_connection_type_south\": StringTag(\"{}\"), \"wall_connection_type_west\": StringTag(\"{}\"), \"wall_post_bit\": ByteTag(1)}})".format(library, family, east, north, south, west)
            else:
                parsed_block = "Block('{}', '{}')".format(library, family)
    # Debug print statement
        # print(parsed_block)
    # Construction file block type examples
    # These strings have to be parsed to use them with the set_block method    
        # minecraft:polished_blackstone[__version__=18100737]
        # minecraft:polished_blackstone_wall[__version__=18100737,wall_connection_type_east="short",wall_connection_type_north="none",wall_connection_type_south="short",wall_connection_type_west="none",wall_post_bit=1b]
        return parsed_block

                     

                
                

          


export = {
    "name": "Read Construction",  # the name of the plugin
    "operation": Paste_At_Selection,  # the actual function to call when running the plugin
}