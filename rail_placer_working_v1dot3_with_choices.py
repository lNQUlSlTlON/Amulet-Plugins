# Programmatic Rail and Roadbed Placer
# Place rails along a path you define, with a roadbed underneath. 
#
# Amulet Map Editor and API Code from the Amulet Team
# All other code (c) 2024 Black Forest Creations
# Blame:  @lNQUlSlTlON

"""
This scipt was built to place rails along a path of your choice, 
defined by Pink Wool Blocks.  Air space is injected above the path to
accommodate the minecart and rider.

NumPy is used to build an array to detect the path of the Pink Wool
and then place rails and a roadbed along that path.

Bedrock doesn't handle corner stairs well, so the script currently places Air.
I'll get around to updated that for Java sooner than later.

The current version of the plug-in also allows for the placement of "cribbing"
(aka supports for the roadbed when the sides are exposed), "underpinning" (aka
supports for the roadbed when the bottom is exposed), and "support pillars".

To facilitate the placement of the support pillars and to ignore the cribbing code
when "overpasses" happen, the script accommodates the use of "Orange Wool" blocks
and "Purple Wool" blocks.
Pink = Path, Orage = Overpass, Purple = Pillar

Last, but not least, you do need the "construction.py" file and "construction" files
to be in the same folder as this script.  I did modify the "construction.py" file
from the original posted by the Amulet Team, as it wasn't working on my Win10 machine.
"""


import os
import json
import numpy as np
import wx
from collections import defaultdict
from itertools import repeat

from typing import TYPE_CHECKING
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI
from amulet_nbt import StringTag, IntTag, ByteTag
# Amulet Construction OpenSource
from construction import ConstructionReader, ConstructionSection


if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas

class Build_Railroad(wx.Panel, DefaultOperationUI):
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

        # Create a label for the dropdown
        dropdown1_label = wx.StaticText(self, label="Cribbing Blocks:")
        self._sizer.Add(dropdown1_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Create a list of choices for the dropdown
        choices1 = ["Dark Oak", "Smooth Stone", "Deepslate Tile", "Iron Block"]

        # Add a Choice control for the dropdown
        self._dropdown1 = wx.Choice(self, choices=choices1)
        self._sizer.Add(self._dropdown1, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "Pos X" as the default selection
        self._dropdown1.SetSelection(0)

        # Create a label for the dropdown
        dropdown2_label = wx.StaticText(self, label="Underpinning Blocks:")
        self._sizer.Add(dropdown2_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Create a list of choices for the dropdown
        choices2 = ["Dark Oak", "Smooth Stone", "Deepslate Tile", "Iron Block"]

        # Add a Choice control for the dropdown
        self._dropdown2 = wx.Choice(self, choices=choices2)
        self._sizer.Add(self._dropdown2, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "Pos X" as the default selection
        self._dropdown2.SetSelection(0)

        # Create a label for the dropdown
        dropdown3_label = wx.StaticText(self, label="Climbing Rails:")
        self._sizer.Add(dropdown3_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Create a list of choices for the dropdown
        choices3 = ["Powered", "Unpowered"]

        # Add a Choice control for the dropdown
        self._dropdown3 = wx.Choice(self, choices=choices3)
        self._sizer.Add(self._dropdown3, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "Pos X" as the default selection
        self._dropdown3.SetSelection(0)

        # Create a label for the dropdown
        dropdown4_label = wx.StaticText(self, label="Support Pillars:")
        self._sizer.Add(dropdown4_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Create a list of choices for the dropdown
        choices4 = ["3x3 Dark Oak", "3x5 Blackstone", "3x3 Smooth Stone"]

        # Add a Choice control for the dropdown
        self._dropdown4 = wx.Choice(self, choices=choices4)
        self._sizer.Add(self._dropdown4, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "Pos X" as the default selection
        self._dropdown4.SetSelection(0)        

        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()


    def loop_operation(self, cribbing_choice, minus1_choice, power_choice, pillar_choice, coordinates, second_block_coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_support_blocks, placed_support_block_iter, support_locations):
        continue_operation = True
        recursive = False
        while continue_operation:
            block_differential = self.rail_direction(coordinates, second_block_coordinates, world, dimension)
            # print('Second block coords before set roadbase', second_block_coordinates)
            back_to_back, continue_coordinates, recursive, placed_blocks, placed_block_iter = self.set_roadbase(coordinates, second_block_coordinates, block_differential, recursive, world, dimension, placed_blocks, placed_block_iter)

            # print('Current Path Calculation Iteration:', placed_block_iter)
            # print('set_roadbase marked recursive as:', recursive, ' for the this iteration')

            # print('Back-to-Back Diagonal Block:', back_to_back)

        ## The back_to_back dict is empty if the path is N-S or E-W, and contains the coordinates of the middle diagonal block if the path is diagonal
            if back_to_back != []:
                b2b_x = int(back_to_back[0]['x'])
                b2b_y = int(back_to_back[0]['y'])
                b2b_z = int(back_to_back[0]['z'])
                b2b_use_case = back_to_back[0]['use_case']
                b2b_coords = [{'x': b2b_x, 'y': b2b_y, 'z': b2b_z, 'value': 1, 'use_case': b2b_use_case}]
                # print('Recursively testing for back-to-back diagonal blocks at:', b2b_coords)
                self.b2b_test(b2b_coords, world, dimension, placed_blocks, placed_block_iter)

            elif back_to_back == []:
                print('No diagonal blocks found, not testing for back-to-back this iteration.')

            cont_x = int(continue_coordinates[0]['x'])
            cont_y = int(continue_coordinates[0]['y'])
            cont_z = int(continue_coordinates[0]['z'])
            if back_to_back != []:
                use_case = back_to_back[0]['use_case']
            else:
                use_case = continue_coordinates[0]['use_case']                

            coordinates = [{'x': cont_x, 'y': cont_y, 'z': cont_z, 'value': 1, 'use_case': use_case}]
            # print('Next Block for Pink Wool path testing is at:', coordinates)

            second_block_coordinates = self.start_direction(coordinates, world, dimension, placed_blocks, placed_block_iter)
            # print(placed_blocks)
            # print("After start_direction:", second_block_coordinates)

            if any(d['value'] == 1 for d in second_block_coordinates):
                # print('Second block found.  Continuing operation.')
                continue_operation = True
                continue
            else :
                # print('Second block not found.  Ending operation.')
                continue_operation = False
                break

        placed_rails, placed_rails_iter = self.set_rails(power_choice, coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter)
        placed_ballast_inner, placed_ballast_outer = self.set_ballast(coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter)

    # Uncomment to log the blocks that are placed on the "Core" path and the "Inner" & "Outer" ballast sets.
        # directory = os.getcwd()
        # with open(f'{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\placed_blocks_output.json', 'w') as f:
        #     json.dump(placed_blocks, f, indent=4)
        # with open(f'{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\inner_ballast_output.json', 'w') as f:
        #     json.dump(placed_ballast_inner, f, indent=4)
        # with open(f'{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\outer_ballast_output.json', 'w') as f:
        #     json.dump(placed_ballast_outer, f, indent=4)

        placed_block_x_z_inner, placed_block_x_z_core, placed_block_x_z_outer = self.find_solid_ground(coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_ballast_inner, placed_ballast_outer)
        support_locations = self.place_supports(cribbing_choice, minus1_choice, coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_ballast_inner, placed_ballast_outer, placed_block_x_z_inner, placed_block_x_z_core, placed_block_x_z_outer, support_locations)
        print('Total core blocks placed:', placed_block_iter)

    # Debug that Pillar choice is being passed correctly and the Support Locations list is being populated
        # print('Pillar Choice:', pillar_choice)
        # print('Support Locations:', support_locations)
        if support_locations is not None and len(support_locations) > 0:

        ## Get the current working director and return it as a variable
            directory = os.getcwd()
        # Debug print statement
            # print(directory)
        ## Use the working directory to build the path to the construction file
            if pillar_choice == "3x3 Dark Oak":
                src_file_path_ns = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\2x2_pier_NorthSouth_DarkOak.construction"
                src_file_path_ew = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\2x2_pier_EastWest_DarkOak.construction"
            elif pillar_choice == "3x5 Blackstone":
                src_file_path_ns = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\3x5_pier_NorthSouth_Blackstone.construction"
                src_file_path_ew = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\3x5_pier_EastWest_Blackstone.construction"
            elif pillar_choice == "3x3 Smooth Stone":
                src_file_path_ns = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\3x3_pier_NorthSouth_PolishedStone.construction"
                src_file_path_ew = f"{directory}\\amulet_map_editor\\programs\\edit\\plugins\\operations\\stock_plugins\\operations\\3x3_pier_EastWest_PolishedStone.construction"
        # The file opened will depend on the direction of the path
            construction_blocks_ns = self.read_construction(src_file_path_ns)
            construction_blocks_ew = self.read_construction(src_file_path_ew)
            ## Debug print statement
                # print('construction blocks dictionary:', construction_blocks)
        # Iterate over each "location" (X, Y, X) in the support_locations list
            for location in support_locations:
                location_x = location['x'][0]
                location_y = location['y'][0]
                location_z = location['z'][0]
                location_air_depth = location['air_depth'][0]
                location_water_depth = location['water_depth'][0]
                location_facing = location['facing'][0]
                total_y = int(location_air_depth) + int(location_water_depth)


                # print(f"total_y: {total_y}, support_coordinates: {support_coordinates}")  # Debug print statement

                if location_facing == 'north' or location_facing == 'south' or location_facing == 'north-northwest' or location_facing == 'north-northeast' or location_facing == 'south-southwest' or location_facing == 'south-southeast' or location_facing == 'wild':
                    if pillar_choice == "3x3 Dark Oak":
                        support_coordinates = {'x': location_x - 1, 'y': location_y, 'z': location_z - 1, 'facing': location_facing}
                    elif pillar_choice == "3x5 Blackstone":
                        support_coordinates = {'x': location_x - 1, 'y': location_y, 'z': location_z - 2, 'facing': location_facing}
                    elif pillar_choice == "3x3 Smooth Stone":
                        support_coordinates = {'x': location_x - 1, 'y': location_y, 'z': location_z - 1, 'facing': location_facing}
                    for y in range(0, total_y):
                        # print (f"y: {y}")  # Debug print statement
                        support_coordinates['y'] = int(location_y) + y
                        # print(f"support_coordinates: {support_coordinates}")  # Debug print statement
                        placed_support_blocks, placed_support_block_iter = self.set_blocks(self.world, self.canvas.dimension, support_coordinates, construction_blocks_ns, placed_support_blocks, placed_support_block_iter)
                elif location_facing == 'east' or location_facing == 'west' or location_facing == 'west-northwest' or location_facing == 'west-southwest' or location_facing == 'east-northeast' or location_facing == 'east-southeast':
                    if pillar_choice == "3x3 Dark Oak":
                        support_coordinates = {'x': location_x - 1, 'y': location_y, 'z': location_z - 1, 'facing': location_facing}
                    elif pillar_choice == "3x5 Blackstone":
                        support_coordinates = {'x': location_x - 2, 'y': location_y, 'z': location_z - 1, 'facing': location_facing}
                    elif pillar_choice == "3x3 Smooth Stone":
                        support_coordinates = {'x': location_x - 1, 'y': location_y, 'z': location_z - 1, 'facing': location_facing}
                    for y in range(0, total_y):
                        # print (f"y: {y}")  # Debug print statement
                        support_coordinates['y'] = int(location_y) + y
                        # print(f"support_coordinates: {support_coordinates}")  # Debug print statement
                        placed_support_blocks, placed_support_block_iter = self.set_blocks(self.world, self.canvas.dimension, support_coordinates, construction_blocks_ew, placed_support_blocks, placed_support_block_iter)                    


    def _run_operation(self, _):
        selection_group = self.canvas.selection.selection_group
        world = self.canvas.world  # get the world object
        dimension = self.canvas.dimension
        placed_blocks = []
        placed_block_iter = 0
        placed_rails = []
        placed_rails_iter = 0
        support_locations = []
        placed_support_blocks = []
        placed_support_block_iter = 0         
        cribbing_choice = self._dropdown1.GetStringSelection() # get the "cribbing" block choice from the dropdown
        minus1_choice = self._dropdown2.GetStringSelection() # get the "underpinning" block choice from the dropdown
        power_choice = self._dropdown3.GetStringSelection() # get the "powered/unpowered rail" block choice from the dropdown
        pillar_choice = self._dropdown4.GetStringSelection() # get the "powered/unpowered rail" block choice from the dropdown


        def operation():
            nonlocal placed_blocks, placed_block_iter, placed_support_blocks, placed_support_block_iter, support_locations
            coordinates, placed_blocks, placed_block_iter = self.read_selection(self.world, self.canvas.dimension, selection_group, placed_blocks, placed_block_iter)
            second_block_coordinates = self.start_direction(coordinates, world, dimension, placed_blocks, placed_block_iter)
            # print('Origin Selection Coordinates:', coordinates)
            # print('Second Block Coordinates:', second_block_coordinates)
            # print('Current Path Calculation Iteration:', placed_block_iter)

            self.loop_operation(cribbing_choice, minus1_choice, power_choice, pillar_choice, coordinates, second_block_coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_support_blocks, placed_support_block_iter, support_locations)

            # support_coordinates = self.start_direction(coordinates, world, dimension, placed_blocks, placed_block_iter)
        ## Debug print statement
            # print('Origin Selection Coordinates:', support_coordinates)

        # Add the operation to the operation manager
        self.canvas.run_operation(operation)
        print("Operation completed successfully.") 

###
### The "Read Selection" function is used to read the selection box and create an array of coordinates
###
### For this class, the selection should always be a single block tall in all dimensions, and made of
### "Pink Wool" or the path will not instantiate correctly.
### 


    @staticmethod
    def read_selection(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup, placed_blocks, placed_block_iter):
        placed_blocks = placed_blocks
        placed_block_iter = placed_block_iter
        coordinates, placed_blocks, placed_block_iter = Build_Railroad.get_coordinates(world, dimension, selection, placed_blocks, placed_block_iter)
        return(coordinates, placed_blocks, placed_block_iter)
        ## Print the coordinates to the console for a sanity check
        # print(coordinates)

    @staticmethod
    def get_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup, placed_blocks, placed_block_iter):
        coordinates = []
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version

        track_base_block = Block('minecraft', 'cobblestone')

        # Iterate over each coordinate in the selection box
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        block = world.get_block(x, y, z, dimension)  # get the existing block at the coordinate
                        # print('Block:', block)
                        if block.blockstate == 'universal_minecraft:wool[color=pink]':
                            value = 1
                            use_case = 'standard_path'
                        elif block.blockstate == 'universal_minecraft:wool[color=orange]':
                            value = 1
                            use_case = 'overpass'
                        elif block.blockstate == 'universal_minecraft:wool[color=purple]':
                            value = 1
                            use_case = 'drop_pillar'
                        else:
                            value = 0
                        # Append the coordinate and value to the list
                        coordinates.append({'x': x, 'y': y, 'z': z, 'value': value, 'use_case': use_case})
                        world.set_version_block(x, y, z, dimension, (platform, version_number), track_base_block, None)                        
        return coordinates, placed_blocks, placed_block_iter

###
### The "Start Direction" function is used to determine if the path selected contains a second block, if on the first iteration,
### or addtional blocks ppassed the "continue location" on subsequent iterations.
###
### The debugging print statements are useful for determining if the function is working as expected, however they generate
### a significant volume of output at the console.  It is recommended to leave them commented out unless needed.
###

    @staticmethod
    def start_direction(coordinates, world, dimension, placed_blocks, placed_block_iter):
        # Create an array at the coordinates
        second_block_coordinates = []
        placed_blocks = placed_blocks
        # print('Origin block:', coordinates[0]['x'], coordinates[0]['y'], coordinates[0]['z'])
        for item in coordinates:
            location_x = int(item['x'])
            location_y = int(item['y'])
            location_z = int(item['z'])
            use_case = item['use_case']
            # print(location_x, location_y, location_z, use_case)
            min_x = location_x - 1
            max_x = location_x + 2
            min_y = location_y - 1
            max_y = location_y + 2
            min_z = location_z - 1
            max_z = location_z + 2
            for x in range(min_x, max_x):
                for y in range(min_y, max_y):
                    for z in range(min_z, max_z):
                        # Skip the original block and any blocks in placed_blocks
                        if any(block['x'] == x and block['y'] == y and block['z'] == z for block in placed_blocks):
                            continue    
                    ## The debug statements below print the entire array... while "noisy" it is useful for debugging
                        # Debug print statement for the test location matrix
                        # print('test location:', x, y, z)                        
                        block = world.get_block(x, y, z, dimension)
                        # Debug print statement for the blockstate
                        # print(block.blockstate)
                        if block.blockstate == 'universal_minecraft:wool[color=pink]':
                            value = 1
                            use_case = 'standard_path'
                            second_block_coordinates.append({'x': x, 'y': y, 'z': z, 'value': value, 'use_case': use_case}) 
                        elif block.blockstate == 'universal_minecraft:wool[color=orange]':
                            value = 1
                            use_case = 'overpass'
                            second_block_coordinates.append({'x': x, 'y': y, 'z': z, 'value': value, 'use_case': use_case}) 
                        elif block.blockstate == 'universal_minecraft:wool[color=purple]':
                            value = 1
                            use_case = 'drop_pillar'
                            # print('found')
                            second_block_coordinates.append({'x': x, 'y': y, 'z': z, 'value': value, 'use_case': use_case}) 
                        else:
                            value = 0
                            # print('none found')
        return second_block_coordinates

    @staticmethod
    def b2b_test(b2b_coords, world, dimension, placed_blocks, placed_block_iter):
        # Create an array at the coordinates
        b2b_block_coordinates = []
        b2b_blocks = placed_blocks[0: len(placed_blocks) - 1]
    ## Debug print statements for the placed_blocks dictionary and the b2b_blocks dictionary    
        # print('Placed Blocks:', placed_blocks)
        # print('B2B Blocks:', b2b_blocks)
        # print('Origin block:', coordinates[0]['x'], coordinates[0]['y'], coordinates[0]['z'])
        for item in b2b_coords:
            location_x = int(item['x'])
            location_y = int(item['y'])
            location_z = int(item['z'])
            b2b_use_case = item['use_case']
            #print(location_x, location_y, location_z)
            min_x = location_x - 1
            max_x = location_x + 2
            min_y = location_y - 1
            max_y = location_y + 2
            min_z = location_z - 1
            max_z = location_z + 2
            for x in range(min_x, max_x):
                for y in range(min_y, max_y):
                    for z in range(min_z, max_z):
                        # Skip the original block and any blocks in placed_blocks
                        if any(block['x'] == x and block['y'] == y and block['z'] == z for block in b2b_blocks):
                            continue    
                    ## The debug statements below print the entire array... while "noisy" it is useful for debugging
                        #Debug print statement for the test location matrix
                        #print('test location:', x, y, z)                        
                        block = world.get_block(x, y, z, dimension)
                        # Debug print statement for the blockstate
                        #print(block.blockstate)
                        if block.blockstate == 'universal_minecraft:wool[color=pink]' or block.blockstate == 'universal_minecraft:wool[color=orange]' or block.blockstate == 'universal_minecraft:wool[color=purple]' or block.blockstate == 'universal_minecraft:cobblestone':
                            value = 1
                            # print('found')
                            b2b_block_coordinates.append({'x': x, 'y': y, 'z': z, 'value': value, 'use_case': b2b_use_case}) 
                        else:
                            value = 0
                            # print('none found')

        # print('Back to Back Block Coordinates:', b2b_block_coordinates)

        if len(b2b_block_coordinates) == 1:
            print('Not Back to Back')
        elif len(b2b_block_coordinates) > 1:
            # print('Back to Back, altering direction of last block in placed_blocks dict.')
            use_case = placed_blocks[-1]['use_case']
            # print('Back to Back Use Case:', use_case)
            ###
            ### Need to update the direction of the last block in the placed_blocks dictionary to reflect the back-to-back status
            ### read the direction of the -2 block and update the -1 block to reflect the appropriately connecting direction
            ###
            if placed_blocks[-2]['direction'] == 'north_west':
                placed_blocks[-1] = {'x': placed_blocks[-1]['x'], 'y': placed_blocks[-1]['y'], 'z': placed_blocks[-1]['z'], 'count': placed_block_iter - 1, 'direction': 'south_east', 'origin_direction': 'north_west', 'facing': 'wild', 'state': 'diagonal', 'b2b': True, 'use_case': use_case}
                # print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
                # print('Updated Block:', placed_blocks[-1])
            elif placed_blocks[-2]['direction'] == 'north_east':
                placed_blocks[-1] = {'x': placed_blocks[-1]['x'], 'y': placed_blocks[-1]['y'], 'z': placed_blocks[-1]['z'], 'count': placed_block_iter - 1, 'direction': 'south_west', 'origin_direction': 'north_east', 'facing': 'wild', 'state': 'diagonal', 'b2b': True, 'use_case': use_case}
                # print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
                # print('Updated Block:', placed_blocks[-1])
            elif placed_blocks[-2]['direction'] == 'south_west':
                # print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
                placed_blocks[-1] = {'x': placed_blocks[-1]['x'], 'y': placed_blocks[-1]['y'], 'z': placed_blocks[-1]['z'], 'count': placed_block_iter - 1, 'direction': 'north_east', 'origin_direction': 'south_west', 'facing': 'wild', 'state': 'diagonal', 'b2b': True, 'use_case': use_case}
                # print('Updated Block:', placed_blocks[-1])
            elif placed_blocks[-2]['direction'] == 'south_east':
                # print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
                # print('Updated Block:', placed_blocks[-1])
                placed_blocks[-1] = {'x': placed_blocks[-1]['x'], 'y': placed_blocks[-1]['y'], 'z': placed_blocks[-1]['z'], 'count': placed_block_iter - 1, 'direction': 'north_west', 'origin_direction': 'south_east', 'facing': 'wild', 'state': 'diagonal', 'b2b': True, 'use_case': use_case}            
        return

    @staticmethod
    def rail_direction(coordinates, second_block_coordinates, world, dimension):
        # print('\"Second Block Coords\" Dict:', second_block_coordinates)
        block_differential = []
        for coord in coordinates:
            x = coord['x']
            y = coord['y']
            z = coord['z']
            use_case = coord['use_case']
            # If there is at least one next block...
            if len(second_block_coordinates) >= 1:
                # Consider the last two entries if there are more than one
                last_two_blocks = second_block_coordinates[-2:] if len(second_block_coordinates) > 1 else second_block_coordinates
                for next_coord in last_two_blocks:
                    next_x = next_coord['x']
                    next_y = next_coord['y']
                    next_z = next_coord['z']
                    value = len(last_two_blocks)
                    diff_x = next_x - x
                    diff_y = next_y - y
                    diff_z = next_z - z
                    block_differential.append({'x': diff_x, 'y': diff_y, 'z': diff_z, 'value': value, 'use_case': use_case})
        # print('Block Differential output from \"block_diff_funct\":', block_differential)
        return block_differential               

###
###  Now we need to build a library of functions to place the rails and roadbed
###  along the path defined by the Pink Wool blocks.
###  Need to determine North/South/East/West direction of the path.
###  And, whether the path goes up or down.
###  The script also needs to keep track of where rails have been to exclude those checks from the next iteration.

    @staticmethod
    def set_roadbase(coordinates, second_block_coordinates, block_differential, recursive, world, dimension, placed_blocks, placed_block_iter):
        back_to_back = []
        continue_coordinates = []
        direction_dict = []
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version

        track_base_block = Block('minecraft', 'cobblestone')

        stair_northsouth_1_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(1)})
        stair_northsouth_2_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(0)})
        stair_eastwest_1_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(2)})
        stair_eastwest_2_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(3)})

        # In order to place stairs, rails, etc in the correct direction, we have to determine the direction of the path.
        # Using block_differential, we can determine the direction of the path.  The len(block_differential) == 1 when the path is straight, and 2+ when the path is complex
        # print('block differential in set roadbase', block_differential)
        if len(block_differential) == 1:
            def determine_direction(item, next_item=None):
                dx = item['x'] if item['x'] != 0 else (next_item['x'] if next_item and next_item['x'] != 0 else 0)
                dy = item['y'] if item['y'] != 0 else (next_item['y'] if next_item and next_item['y'] != 0 else 0)
                dz = item['z'] if item['z'] != 0 else (next_item['z'] if next_item and next_item['z'] != 0 else 0)

##
##  Thus far, the code determines the axis or corners correctly, however, it doesn't indicate what direction the path is going.
##  So, in addition to returning the axis or corner, we need to return the direction of the path.
##  Let's add an entry to placed_blocks called "facing" to indicate the direction of the path.
##  This will allow us to determine which set of ballast blocks is on the "inside" of the path and which is on the "outside".
##  That is going to be necessary we we can test for air and water under the ballast blocks in the correct order and take actions
##  based on wether air is found under the "inside" or "outside" ballast blocks, depending on the test under the central path block.
##

                if dy > 0:
                    if dx > 0: return 'east_ascending', 'east', dx, dy, dz
                    elif dx < 0: return 'east_descending', 'west', dx, dy, dz
                    elif dz < 0: return 'north_ascending', 'north', dx, dy, dz
                    else : return 'north_descending', 'south', dx, dy, dz
                elif dy < 0:
                    if dx > 0: return 'east_descending', 'east', dx, dy, dz
                    elif dx < 0: return 'east_ascending', 'west', dx, dy, dz
                    elif dz < 0: return 'north_descending', 'north', dx, dy, dz
                    else: return 'north_ascending', 'south', dx, dy, dz
                elif dx > 0: return 'east_west', 'east', dx, dy, dz
                elif dx < 0: return 'east_west', 'west', dx, dy, dz
                elif dz > 0: return 'north_south', 'south', dx, dy, dz
                elif dz < 0: return 'north_south', 'north', dx, dy, dz
            direction, facing, dx, dy, dz = determine_direction(block_differential[0])
            direction_dict.append(direction)

    ## Corindates and block placement are working, but ascending rail placement is not if the ascending rail is not the first block placed
    ##
    ## Descending rail placement is working
    ##
    ## Theory -- we need to update the iteration prior to the current block to place the ascending rail
    ##

        ## Read coordinates list at the base location of the current iteration
            base_x = coordinates[0]['x']
            base_y = coordinates[0]['y']
            base_z = coordinates[0]['z']
            use_case = second_block_coordinates[0]['use_case']
            use_case1 = coordinates[0]['use_case']
            # print('coordinates use_case', use_case1)
            # print('second block use_case', use_case)
            # print('Base block of iteration (len 1)', placed_block_iter, ':', base_x, base_y, base_z, use_case1)
            # print('Coordinates', coordinates)
            # print('Base block rail direction:', direction)
        ## Read "use_case" at this iteration
   

        ## Add first block to placed_blocks list after determining starting direction
            if placed_block_iter == 0:
                placed_blocks.append({'x': base_x, 'y': base_y, 'z': base_z, 'count': placed_block_iter, 'direction': direction, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case})
                print('First roadbase block:', placed_blocks)
                placed_block_iter += 1
                # print('dx, dy, dz:', dx, dy, dz)

        ## Place a single block at "second block location"           
            # print('Roadbase blocks placed before current iteration:', placed_block_iter)
            # print('dx, dy, dz:', dx, dy, dz)            
            world.set_version_block(base_x + dx, base_y + dy, base_z + dz, dimension, (platform, version_number), track_base_block, None)

            if dy > 0:
                # print('dy > 1')
                placed_blocks[-1] = {'x': base_x, 'y': base_y, 'z': base_z, 'count': placed_block_iter, 'direction': direction, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case}
                placed_blocks.append({'x': base_x + dx, 'y': base_y + dy, 'z': base_z + dz, 'count': placed_block_iter, 'direction': direction, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case})                
                recursive = True
            else:
                # print(recursive)
                if recursive == True:
                    # print('Recursive!!!!')
                    # print('End of Placed Blocks Dictionary before Recursive Operation', placed_blocks[-2], placed_blocks[-1])
                    placed_blocks[-1] = {'x': base_x, 'y': base_y, 'z': base_z, 'count': placed_block_iter, 'direction': direction, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case}
                    # print('End of Placed Blocks Dictionary after Recursive Operation', placed_blocks[-2], placed_blocks[-1])
                # print('dy <= 0')
                placed_blocks.append({'x': base_x + dx, 'y': base_y + dy, 'z': base_z + dz, 'count': placed_block_iter, 'direction': direction, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case})
                recursive = False

            # print('Iteration', placed_block_iter, 'placed block at:', base_x + dx, base_y + dy, base_z + dz)
            placed_block_iter += 1
            # print('Roadbase blocks placed through current iteration:', placed_block_iter)
        # Print the updated placed blocks                 
            # print('Updated placed blocks dict:', placed_blocks)
            print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
        ## back_to_back should stay empty if the path is N-S or E-W
        ## Continue testing at the block
            continue_coordinates.append({'x': base_x + dx, 'y': base_y + dy, 'z': base_z + dz, 'value': direction, 'use_case': use_case})
            # print('N-S or E-W direction, continuing pathfinding at:', continue_coordinates, 'facing:', facing)                             

        elif len(block_differential) == 2:

            base_x = coordinates[0]['x']
            base_y = coordinates[0]['y'] 
            base_z = coordinates[0]['z']
            use_case = second_block_coordinates[0]['use_case']
            use_case2 = second_block_coordinates[1]['use_case']

            # print('Base block of iteration (len 2):', base_x, base_y, base_z, use_case)
            # print('2nd Coordinates', second_block_coordinates)
            # if placed_blocks:
            #     print('Current Iteration is:', placed_block_iter - 1, 'Block is:', placed_blocks[-1])
            # else:
            #     print('Current Iteration is:', placed_block_iter - 1, 'Block is: List is empty')

            def determine_direction(item, base_x, base_y, base_z, placed_block_iter):
            ## Use the value of the first two items in the block_differential list to determine the direction of the path 
                x1 = item[0]['x']
                y1 = item[0]['y']
                z1 = item[0]['z']
                value1 = item[0]['value']
                d1 = ''
                d2 = ''
                d3 = ''
                x2 = item[1]['x']
                y2 = item[1]['y']
                z2 = item[1]['z']
                value2 = item[1]['value']
                if x1 == -1 and y1 == 0 and z1 == 1 and value1 == 2 and x2 == 0 and y2 == 0 and z2 == 1 and value2 == 2:
                #reverese the order of the coordinates to properly check the blocks in the correct order
                    x1 = item[1]['x']
                    y1 = item[1]['y']
                    z1 = item[1]['z']
                    x2 = item[0]['x']
                    y2 = item[0]['y']
                    z2 = item[0]['z']
                    d1 = 'north_south'
                    d2 = 'north_west'
                    d3 = 'east_west'                    
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ns_block, None)
                    return 'west-southwest', 'west-southwest', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == -1 and y1 == 0 and z1 == 0 and value1 == 2 and x2 == -1 and y2 == 0 and z2 == 1 and value2 == 2:
                    d1 = 'east_west'
                    d2 = 'south_east'
                    d3 = 'north_south'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ew_block, None)
                    return 'south-southwest', 'south-southwest', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == 0 and y1 == 0 and z1 == 1 and value1 == 2 and x2 == 1 and y2 == 0 and z2 == 1 and value2 == 2:
                    d1 = 'north_south'
                    d2 = 'north_east'
                    d3 = 'east_west'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ns_block, None)                     
                    return 'east-southeast', 'east-southeast', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == 1 and y1 == 0 and z1 == 0 and value1 == 2 and x2 == 1 and y2 == 0 and z2 == 1 and value2 == 2:
                    d1 = 'east_west'
                    d2 = 'south_west'
                    d3 = 'north_south'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ew_block, None)
                    return 'south-southeast', 'south-southeast', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == 0 and y1 == 0 and z1 == -1 and value1 == 2 and x2 == 1 and y2 == 0 and z2 == -1 and value2 == 2:
                    d1 = 'north_south'
                    d2 = 'south_east'
                    d3 = 'east_west'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ns_block, None)
                    return 'east-northeast','east-northeast', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == 1 and y1 == 0 and z1 == -1 and value1 == 2 and x2 == 1 and y2 == 0 and z2 == 0 and value2 == 2: 
                #reverese the order of the coordinates to properly check the blocks in the correct order
                    x1 = item[1]['x']
                    y1 = item[1]['y']
                    z1 = item[1]['z']
                    x2 = item[0]['x']
                    y2 = item[0]['y']
                    z2 = item[0]['z']
                    d1 = 'east_west'
                    d2 = 'north_west'
                    d3 = 'north_south'                    
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ew_block, None)                       
                    return 'north-northeast', 'north-northeast', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == -1 and y1 == 0 and z1 == -1 and value1 == 2 and x2 == -1 and y2 == 0 and z2 == 0 and value2 == 2:
                #reverese the order of the coordinates to properly check the blocks in the correct order
                    x1 = item[1]['x']
                    y1 = item[1]['y']
                    z1 = item[1]['z']
                    x2 = item[0]['x']
                    y2 = item[0]['y']
                    z2 = item[0]['z']
                    d1 = 'east_west'
                    d2 = 'north_east'
                    d3 = 'north_south'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ew_block, None)                                            
                    return 'north-northwest', 'north-northwest', x1, y1, z1, x2, y2, z2, d1, d2, d3
                elif x1 == -1 and y1 == 0 and z1 == -1 and value1 == 2 and x2 == 0 and y2 == 0 and z2 == -1 and value2 == 2:
                #reverese the order of the coordinates to properly check the blocks in the correct order
                    x1 = item[1]['x']
                    y1 = item[1]['y']
                    z1 = item[1]['z']
                    x2 = item[0]['x']
                    y2 = item[0]['y']
                    z2 = item[0]['z']
                    d1 = 'north_south'
                    d2 = 'south_west'
                    d3 = 'east_west'
                    if placed_block_iter == 1:
                        world.set_version_block(base_x, base_y + 1, base_z, dimension, (platform, version_number), rail_ns_block, None)                                            
                    return 'west-northwest', 'west-northwest', x1, y1, z1, x2, y2, z2, d1, d2, d3                
            direction, facing, x1, y1, z1, x2, y2, z2, d1, d2, d3  = determine_direction(block_differential, base_x, base_y, base_z, placed_block_iter)
            direction_dict.append(direction)
        ## Debug print statement for the direction of the path    
            # print(direction_dict)    

        ## Add first block to placed_blocks list after determining starting direction
            if placed_block_iter == 0:
                placed_blocks.append({'x': base_x, 'y': base_y, 'z': base_z, 'count': placed_block_iter, 'direction': d1, 'origin_direction': direction, 'facing': 'unknown', 'state': 'cardinal', 'b2b': False, 'use_case': use_case})
                # print('starting block @:', placed_blocks)                
                placed_block_iter += 1
        ## If recursive, we need to go back and change the "ascending" blok to the direction of D1
            if recursive == True:
                # print('Recursive!!!!')
                # print('End of Placed Blocks Dictionary before Recursive Operation', placed_blocks[-2], placed_blocks[-1])
                placed_blocks[-1] = {'x': base_x, 'y': base_y, 'z': base_z, 'count': placed_block_iter, 'direction': d1, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case}
                # print('End of Placed Blocks Dictionary after Recursive Operation', placed_blocks[-2], placed_blocks[-1])
                recursive = False
        ## Place first of two blocks
            # print('placed count before current iteration:', placed_block_iter)
            world.set_version_block(base_x + x1, base_y + y1, base_z + z1, dimension, (platform, version_number), track_base_block, None)
            placed_blocks.append({'x': base_x + x1, 'y': base_y + y1, 'z': base_z + z1, 'count': placed_block_iter, 'direction': d2, 'origin_direction': direction, 'facing': facing, 'state': 'corner', 'b2b': False, 'use_case': use_case})
            # print('Block 1 placed block at:', base_x + x1, base_y + y1, base_z + z1, 'count:', placed_block_iter, 'use_case:', use_case)
            placed_block_iter += 1
            # print('placed count after current iteration:', placed_block_iter)
        ## Place second of two blocks
            # print('placed count before current iteration:', placed_block_iter)
            world.set_version_block(base_x + x2, base_y + y2, base_z + z2, dimension, (platform, version_number), track_base_block, None)
            placed_blocks.append({'x': base_x + x2, 'y': base_y + y2, 'z': base_z + z2, 'count': placed_block_iter, 'direction': d3, 'origin_direction': direction, 'facing': facing, 'state': 'cardinal', 'b2b': False, 'use_case': use_case2})
            # print('Block 2 placed block at:', base_x + x2, base_y + y2, base_z + z2, 'count:', placed_block_iter, 'use_case:', use_case2)            
            placed_block_iter += 1
            # print('placed count after current iteration:', placed_block_iter)    
        ## Print the updated placed blocks           
            # print('updated placed blocks:', placed_blocks)        
        ## Continue testing at the second placed block
            back_to_back.append({'x': base_x + x1, 'y': base_y + y1, 'z': base_z + z1, 'value': direction, 'use_case': use_case2})
            continue_coordinates.append({'x': base_x + x2, 'y': base_y + y2, 'z': base_z + z2, 'value': direction, 'use_case': use_case})
            # print('multiple blocks set, continue at:', continue_coordinates)  
        return back_to_back, continue_coordinates, recursive, placed_blocks, placed_block_iter


    @staticmethod
    def set_rails(power_choice, coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter):
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version

        air_block = Block('minecraft', 'air')

        if power_choice == 'Powered':
            rail_north_ascending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(4)})
            rail_north_descending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(5)})
            rail_east_ascending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(2)})
            rail_east_descending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(3)})
        else:
            rail_north_ascending = Block('minecraft', 'rail', {"rail_direction": IntTag(4)})
            rail_north_descending = Block('minecraft', 'rail', {"rail_direction": IntTag(5)})
            rail_east_ascending = Block('minecraft', 'rail', {"rail_direction": IntTag(2)})
            rail_east_descending = Block('minecraft', 'rail', {"rail_direction": IntTag(3)})

        rail_north_south = Block('minecraft', 'rail', {"rail_direction": IntTag(0)})
        # rail_north_ascending = Block('minecraft', 'rail', {"rail_direction": IntTag(4)})
        # rail_north_descending = Block('minecraft', 'rail', {"rail_direction": IntTag(5)})                   
        rail_east_west = Block('minecraft', 'rail', {"rail_direction": IntTag(1)})
        # rail_east_ascending = Block('minecraft', 'rail', {"rail_direction": IntTag(2)})
        # rail_east_descending = Block('minecraft', 'rail', {"rail_direction": IntTag(3)})
        rail_north_west = Block('minecraft', 'rail', {"rail_direction": IntTag(8)})
        rail_north_east = Block('minecraft', 'rail', {"rail_direction": IntTag(9)})
        rail_south_west = Block('minecraft', 'rail', {"rail_direction": IntTag(7)})
        rail_south_east = Block('minecraft', 'rail', {"rail_direction": IntTag(6)})                                                   

        powered_rail_north_south = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(0)})
        powered_rail_north_ascending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(4)})
        powered_rail_north_descending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(5)})                   
        powered_rail_east_west = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(1)})
        powered_rail_east_ascending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(2)})
        powered_rail_east_descending = Block('minecraft', 'golden_rail', {"rail_data_bit": ByteTag(0), "rail_direction": IntTag(3)})

        rail_directions = {
            'north_south': rail_north_south,
            'north_ascending': rail_north_ascending,
            'north_descending': rail_north_descending,
            'east_west': rail_east_west,
            'east_ascending': rail_east_ascending,
            'east_descending': rail_east_descending,
            'north_west': rail_north_west,
            'north_east': rail_north_east,
            'south_west': rail_south_west,
            'south_east': rail_south_east
        }

        powered_rail_directions = {
            'north_south': powered_rail_north_south,
            'north_ascending': powered_rail_north_ascending,
            'north_descending': powered_rail_north_descending,
            'east_west': powered_rail_east_west,
            'east_ascending': powered_rail_east_ascending,
            'east_descending': powered_rail_east_descending
        }

        ascending_directions = {
            'north_ascending': rail_north_ascending,
            'north_descending': rail_north_descending,
            'east_ascending': rail_east_ascending,
            'east_descending': rail_east_descending,
            'north_ascending': powered_rail_north_ascending,
            'north_descending': powered_rail_north_descending,
            'east_ascending': powered_rail_east_ascending,
            'east_descending': powered_rail_east_descending            
        }

        invalid_powered_rail_direction = {
            'north_west',
            'north_east',
            'south_west',
            'south_east'
        }

        # print('placed rail count:', placed_rails_iter)
        # print('first rail:', placed_blocks[placed_rails_iter])

        for i in range(len(placed_blocks)):
            x1 = placed_blocks[i]['x']
            y1 = placed_blocks[i]['y']
            z1 = placed_blocks[i]['z']
            direction = placed_blocks[i]['direction']
            facing = placed_blocks[i]['facing']
            if placed_rails_iter % 16 == 16:
                powered = True
            else:
                powered = False
        # Place a rail at the base block location (+1 Y) based on the direction of the path
            if powered == True and direction != invalid_powered_rail_direction:                
                rail_block = powered_rail_directions[direction]
                world.set_version_block(x1, y1 + 1, z1, dimension, (platform, version_number), rail_block, None)
                world.set_version_block(x1, y1 + 2, z1, dimension, (platform, version_number), air_block, None)
                if direction in ascending_directions:
                    world.set_version_block(x1, y1 + 3, z1, dimension, (platform, version_number), air_block, None)
                placed_rails_iter += 1
                # print('placed powered rail at:', x1, y1 + 1, z1, 'direction:', direction, 'facing:', facing, 'count:', placed_rails_iter)
            else:
                rail_block = rail_directions[direction]    
                world.set_version_block(x1, y1 + 1, z1, dimension, (platform, version_number), rail_block, None)
                world.set_version_block(x1, y1 + 2, z1, dimension, (platform, version_number), air_block, None)
                if direction in ascending_directions:
                    world.set_version_block(x1, y1 + 3, z1, dimension, (platform, version_number), air_block, None)                
                placed_rails_iter += 1
                # print('placed rail at:', x1, y1 + 1, z1, 'direction:', direction, 'facing:', facing, 'count:', placed_rails_iter)

        return placed_rails, placed_rails_iter              

###
###
###  Time to start placing the "ballast" blocks to the sides of the roadbed
###  These blocks will be heavily dependent on the direction of the roadbed, and the rails ahead
###  and behind the current block.
###
###  Goal 1) Cobblestone stairs on the sides of the roadbed
###  Goal 2) Test for air under all blocks
###  Goal 3) Create a "support" under the "ballast" and "roadbed" blocks
###  Goal 4) Paste a schematic under the roadbed if air depth exceeds 3 blocks
###

    @staticmethod
    def set_ballast(coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter):
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version

        placed_ballast_inner = []
        placed_ballast_outer = []

##
##  The stairs are being set correctly.  Now, we need to confirm path-finding is able to tell the "inside" from the "outside" of the path
##  To do that, we'll change the blocks below to be a different color and use the "facing" key in the placed_blocks dictionary to determine
##  which set of stairs to place.
##
##  The "inside" will be blue wool and the "outside" will be red wool.  Corners will be green wool.
##
        # stair_northsouth_1_block = Block('minecraft', 'blue_wool')
        # stair_northsouth_2_block = Block('minecraft', 'red_wool')
        # stair_eastwest_1_block = Block('minecraft', 'blue_wool')
        # stair_eastwest_2_block = Block('minecraft', 'red_wool')
        # stair_corner_1_block = Block('minecraft', 'green_wool')
        # stair_corner_2_block = Block('minecraft', 'green_wool')
        # stair_corner_3_block = Block('minecraft', 'green_wool')
        # stair_corner_4_block = Block('minecraft', 'green_wool')
        # stair_corner_5_block = Block('minecraft', 'green_wool')
        # stair_corner_6_block = Block('minecraft', 'green_wool')
        # stair_corner_7_block = Block('minecraft', 'green_wool')
        # stair_corner_8_block = Block('minecraft', 'green_wool')

        stair_northsouth_1_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(0)})
        stair_northsouth_2_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(1)})
        stair_eastwest_1_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(2)})
        stair_eastwest_2_block = Block('minecraft', 'stone_stairs', {"upside_down_bit": ByteTag(0), "weirdo_direction": IntTag(3)})

    ## Since I only play Bedrock, and Bedrock is pants at explicit stair placement, I am going to leave these entries here for future development
    ## Giant has also said that he is going to be obfuscating the "Universal" block refs, so these will need to be updated to the new format
        # stair_corner_1_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("north"), "half": StringTag("bottom"), "shape": StringTag("inner_left")})
        # stair_corner_2_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("north"), "half": StringTag("bottom"), "shape": StringTag("inner_right")})
        # stair_corner_3_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("north"), "half": StringTag("bottom"), "shape": StringTag("outer_left")})
        # stair_corner_4_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("north"), "half": StringTag("bottom"), "shape": StringTag("outer_right")})
        # stair_corner_5_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("south"), "half": StringTag("bottom"), "shape": StringTag("inner_left")})
        # stair_corner_6_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("south"), "half": StringTag("bottom"), "shape": StringTag("inner_right")})
        # stair_corner_7_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("south"), "half": StringTag("bottom"), "shape": StringTag("outer_left")})
        # stair_corner_8_block = Block('universal_minecraft', 'stairs', {"material": StringTag("cobblestone"), "facing": StringTag("south"), "half": StringTag("bottom"), "shape": StringTag("outer_right")})

        air_block = Block('minecraft', 'air')
        stair_corner_1_block = Block('minecraft', 'air')
        stair_corner_2_block = Block('minecraft', 'air')
        stair_corner_3_block = Block('minecraft', 'air')
        stair_corner_4_block = Block('minecraft', 'air')
        stair_corner_5_block = Block('minecraft', 'air')
        stair_corner_6_block = Block('minecraft', 'air')
        stair_corner_7_block = Block('minecraft', 'air')
        stair_corner_8_block = Block('minecraft', 'air')

        print('Ballast Function!')
        # print('Beginning function...')

        placed_ballast_iter = 0

        # print('Placed Ballast Function Iteration:', placed_ballast_iter)

        for item in placed_blocks:
            x = item['x']
            y = item['y']
            z = item['z']
            direction = item['direction']
            origin_direction = placed_blocks[placed_ballast_iter]['origin_direction']
            facing = item['facing']
            b2b = item['b2b']
            count = item['count']
            use_case = item['use_case']


            if placed_ballast_iter == 0:
                # print('First Block in Ballast Funtion:', x, y, z, 'direction:', direction, 'origin_direction:', origin_direction, 'facing:', facing, 'count:', count, 'b2b:', b2b, 'use_case:', use_case)
                print('\n')

            elif placed_ballast_iter > 0:
                # print(placed_ballast_iter)
                print('\n')
                # print('Current Block in Ballast Funtion:', x, y, z, 'direction:', direction, 'origin_direction:', origin_direction, 'facing:', facing, 'count:', count, 'b2b:', b2b, 'use_case:', use_case)                
###
### Now that we have the first, current/previous pieces passing the direction and origin_direction, we can start placing the ballast blocks
### I think it makes sense top test the origin_direction first, then the direction of the current block
### If the origin_direction is the same as the current direction, we can place the ballast blocks on the sides of the roadbed
### Otherwise, we get granular with the N-NE, N-NW, S-SE, S-SW, etc directions and the eight different stair configurations
###
### NOTE -- Ascending and Descending blocks need additional overhead clearance, so there is one additional air block above the ballast blocks
###         when the direction is ascending or descending.
###
            if origin_direction == direction:
                # NOTE -- The last block in "back-to-back" series will test as a "simple happy path"
                # So, we we need to test each N-S/E-W block to see if there is a b2b block before them
                # print('This is a simple, happy path!')
                print('\n')
                
            ##
            ## NOTE -- "Inner"/"Outer" designator on the blocks in the placed_ballast list, based on the "facing" key in the placed_blocks dictionary
            ## Using blue wool to indicate "inner" edges and red wool to indicated the "outer" edges of the path for now for debugging purposes
            ##

                ## North-South Facing North
                if (direction in ['north_south', 'north_ascending', 'north_descending']) and (facing == 'north'):
                    if len(placed_blocks) == 0:
                            # print('North-South Ballast Placement, facing North')                                           
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            if direction == 'north_ascending' or direction == 'north_descending':
                                world.set_version_block(x - 1, y + 3, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            if direction == 'north_ascending' or direction == 'north_descending':
                                world.set_version_block(x + 1, y + 3, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                    elif len(placed_blocks) > 0:
                        prev_b2b = placed_blocks[placed_ballast_iter - 1]['b2b']
                        prev_dir = placed_blocks[placed_ballast_iter - 1]['direction']                        
                        # print('Previous Block b2b:', prev_b2b, 'Previous Block Direction:', prev_dir)
                        if prev_b2b == False:     
                            # print('North-South Ballast Placement, facing North')                                           
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)   
                            if direction == 'north_ascending' or direction == 'north_descending':
                                world.set_version_block(x - 1, y + 3, z, dimension, (platform, version_number), air_block, None)                                                     
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            if direction == 'north_ascending' or direction == 'north_descending':
                                world.set_version_block(x + 1, y + 3, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                        elif prev_b2b == True and prev_dir == 'north_west':
                            # print('North-South Ballast Placement, facing North from East-Northeast b2b')
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_northsouth_2_block'})
                            placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})
                        elif prev_b2b == True and prev_dir == 'north_east':
                            # print('North-South Ballast Placement, facing North from West-Northwest b2b')
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_northsouth_1_block'})
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})

                ## North-South Facing South
                elif (direction in ['north_south', 'north_ascending', 'north_descending']) and (facing == 'south'):
                    if len(placed_blocks) == 0:
                        # print('North-South Ballast Placement, facing South') 
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)                                           
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                                                
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                    elif len(placed_blocks) > 0:
                        prev_b2b = placed_blocks[placed_ballast_iter - 1]['b2b']
                        prev_dir = placed_blocks[placed_ballast_iter - 1]['direction']                        
                        # print('Previous Block b2b:', prev_b2b, 'Previous Block Direction:', prev_dir)        
                        if prev_b2b == False:
                            # print('North-South Ballast Placement, facing South')                                                                                    
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                        elif prev_b2b == True and prev_dir == 'south_west':
                            # print('North-South Ballast Placement, facing South from East-Southeast b2b')
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_northsouth_2_block'})
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                        elif prev_b2b == True and prev_dir == 'south_east':
                            # print('North-South Ballast Placement, facing South from West-Northwest b2b')                                                        
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_northsouth_1_block'})
                            placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})
                ## East-West Facing East            
                elif (direction in ['east_west', 'east_ascending','east_descending']) and (facing == 'east'):
                    if len(placed_blocks) == 0:
                        # print('East-West Ballast Placement, facing East')
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})                    
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})                                            
                    elif len(placed_blocks) > 0:
                        prev_b2b = placed_blocks[placed_ballast_iter - 1]['b2b']
                        prev_dir = placed_blocks[placed_ballast_iter - 1]['direction']
                        # print('Previous Block b2b:', prev_b2b, 'Previous Block Direction:', prev_dir)
##
##  Expanded this test of states to include the prev_dir when prev_b2b == false because of unexpected behavior on the last block of a east-southeast series
##                         
                        if prev_b2b == False and (prev_dir == 'east_west' or prev_dir == 'north_south'): 
                            # print('East-West Ballast Placement, facing East')                                              
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})                    
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})
                        elif (prev_b2b == True or prev_b2b == False) and prev_dir == 'south_east':
                            # print('East-West Ballast Placement, facing East from South-Southeast b2b')
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_eastwest_2_block'}) 
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                        elif (prev_b2b == True or prev_b2b == False) and prev_dir == 'north_east':
                            # print('East-West Ballast Placement, facing East from North-Northeast b2b')                            
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                              
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_eastwest_1_block'})
                            placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})
                ## East-West Facing West
                elif (direction in ['east_west', 'east_ascending','east_descending']) and (facing == 'west'):
                    if len(placed_blocks) == 0:                    
                        # print('East-West Ballast Placement, facing West')
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})                    
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                          
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})                                            
                    if len(placed_blocks) > 0:
                        prev_b2b = placed_blocks[placed_ballast_iter - 1]['b2b']
                        prev_dir = placed_blocks[placed_ballast_iter - 1]['direction']                        
                        # print('Previous Block b2b:', prev_b2b, 'Previous Block Direction:', prev_dir)
                        if prev_b2b == False: 
                            # print('East-West Ballast Placement, facing West')                      
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                                
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})                    
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                                 
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})
                        elif prev_b2b == True and prev_dir == 'north_west':
                            # print('East-West Ballast Placement, facing West from South-Southwest b2b')                              
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                                 
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_eastwest_1_block'})
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                        elif prev_b2b == True and prev_dir == 'south_west':
                            # print('East-West Ballast Placement, facing West from North-Northwest b2b')                              
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                              
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_eastwest_2_block'})
                            placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})
                placed_ballast_iter += 1

            else:
                # print('This is a complex path!')
                print('\n')
        ###
        ### Sooo... fun fact, Bedrock does not handle the programmatic setting of Diagonal Stairs.
        ### So, the logic is here, but it will not work in Bedrock.
        ###
                if origin_direction == 'north-northeast':
                    # print('North-Northeast Ballast Placement, facing East and Turning North')
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above
                    if direction == 'east_west':                        
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                         
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})
                     
                ## Always Block 1
                    elif direction == 'north_west':
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks
                        if next_b2b == False:   
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_7_block'})                         
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_3_block'}) 
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_northsouth_2_block'}) 
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)  
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_eastwest_2_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:  
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_7_block'})                         
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'}) 
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                               
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_eastwest_2_block'})
                ## Only Block 2 if "next back-to-back" = False
                    elif direction == 'north_south':
                        #world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_northsouth_2_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})                        
            
                elif origin_direction == 'west-southwest':
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above                    
                    # print('West-Southwest Ballast Placement, facing South and turning West')                    
                    if direction == 'north_south':
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                          
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                ## Always Block 1                                                 
                    elif direction == 'north_west':
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                        if next_b2b == False:
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks  
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_7_block'})                         
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_3_block'}) 
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_northsouth_2_block'}) 
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)  
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_eastwest_2_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_7_block'})                         
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_3_block'}) 
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_northsouth_2_block'}) 
                ## Only Block 2 if "next back-to-back" = False                                                                                                                
                    elif direction == 'east_west':
                        #world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                          
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_eastwest_2_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})

            ## (direction == 'south_east' and origin_direction == 'north_west')
            ## True for both N-NE b2b and W-SW b2b    
                elif (direction == 'south_east' and origin_direction == 'north_west'):
                    prev_origin = placed_blocks[placed_ballast_iter - 1]['origin_direction']
                ## Only Block 2 if "next back-to-back" = True and previous origin is "north-northeast"
                    if direction == 'south_east' and prev_origin == 'north-northeast':
                        world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'})
                        world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                        world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_6_block'})                                                      
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_eastwest_2_block'}) 
                ## Only Block 2 if "next back-to-back" = True and previous origin is "west-southwest"                           
                    elif direction == 'south_east' and prev_origin == 'west-southwest':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_northsouth_1_block'})
                        world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'})
                        world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_3_block'})  

                elif origin_direction == 'east-northeast':
                    # print('East-Northeast Ballast Placement, facing North and turning East')
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above
                    if direction == 'north_south':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'}) 
                ## Always Block 1                                                
                    elif direction == 'south_east':
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks                        
                        if next_b2b == False:
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_7_block'})                          
                        ## This block is redundant to the cardinal direction when b2b = False
                            # world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_northsouth_2_block, None)
                            # world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            # world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            # placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_1_block'})                          
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_northsouth_1_block'})                          
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_eastwest_1_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_7_block'})                          
                        ## This block is NOT redundant in a B2B scenario
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_1_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_1_block'})                          
                            placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_northsouth_1_block'})                          
                ## Only Block 2 if "next back-to-back" = False 
                    elif direction == 'east_west':
            #Debugging 90 deg turns...
                        #print('YOU GOT ME!  THIS IS EAST-WEST IN A EAST-NORTHEAST LOOP!!!')
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_eastwest_1_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})                         
                        #world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)

                elif origin_direction == 'south-southwest':
                    # print('Souht-Southwest Ballast Placement, facing West and turning South')
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above                    
                    if direction == 'east_west':
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})                                          
                ## Always Block 1                        
                    elif direction == 'south_east':
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                        if next_b2b == False:
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_7_block'})                          
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_1_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_1_block'})                          
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_northsouth_1_block'})                          
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_eastwest_1_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                            world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_7_block'})                          
                            world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_1_block, None)
                            world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_1_block'})                          
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_eastwest_1_block'})                                                      
                ## Only Block 2 if "next back-to-back" = False 
                    if direction == 'north_south':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_northsouth_1_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})

            ## (direction = 'north_west' and origin_direction == 'south_east')
            ## True for both E-NE b2b and S-SW b2b
                elif (direction == 'north_west' and origin_direction == 'south_east'):
                    prev_origin = placed_blocks[placed_ballast_iter - 1]['origin_direction']
                ## Only Block 2 if "next back-to-back" = True and previous origin is "east-northeast"                    
                    if direction == 'north_west' and prev_origin == 'east-northeast':
                        world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                        world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)  
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_7_block'})
                        world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_1_block, None)
                        world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                           
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_1_block'})  
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_northsouth_2_block'})
                ## Only Block 2 if "next back-to-back" = True and previous origin is "south-southwest"   
                    elif direction == 'north_west' and prev_origin == 'south-southwest':
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_eastwest_1_block'})
                        world.set_version_block(x - 1, y, z - 1, dimension, (platform, version_number), stair_corner_7_block, None)
                        world.set_version_block(x - 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                          
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_7_block'})
                        world.set_version_block(x + 1, y, z + 1, dimension, (platform, version_number), stair_corner_1_block, None)
                        world.set_version_block(x + 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                           
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_1_block'})

                elif origin_direction == 'south-southeast':
                    # print('South-Southeast Ballast Placement, facing East turning South')                            
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above    
                    if direction == 'east_west':
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_1_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'}) 
                ## Always Block 1                 
                    elif direction == 'south_west':    
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks                        
                        if next_b2b == False:
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_2_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_2_block'})                            
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_8_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_8_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_northsouth_2_block'})                            
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_eastwest_1_block'})                            
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_2_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_2_block'}) 
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_8_block, None)      
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                                                  
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_8_block'})
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_eastwest_1_block'})
                ## Only Block 2 if "next back-to-back" = False                          
                    elif direction == 'north_south':
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_northsouth_2_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})

                elif origin_direction == 'west-northwest':
                    # print('West-Northwest Ballast Placement, facing North and turning West')                            
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above   
                    if direction == 'north_south':
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_2_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})                
                ## Always Block 1   
                    elif direction == 'south_west':    
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks                          
                        if next_b2b == False:
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_2_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_2_block'})                            
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_8_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_8_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_northsouth_2_block'})                            
                            world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_eastwest_1_block'})                            
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_2_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_2_block'})                            
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_8_block'})
                            world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_northsouth_2_block'})                            
                ## Only Block 2 if "next back-to-back" = False 
                    elif direction == 'east_west':
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_eastwest_1_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})

            ## (direction == 'north_east' and origin_direction == 'south_west')
            ## True for both S-SE b2b and W-NW b2b
                elif (direction == 'north_east' and origin_direction == 'south_west'):
                    prev_origin = placed_blocks[placed_ballast_iter - 1]['origin_direction']
                ## Only Block 2 if "next back-to-back" = True and previous origin is "south-southeast"                                           
                    if direction == 'north_east' and prev_origin == 'south-southeast':
                        world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_6_block, None)
                        world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_6_block'})                         
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_eastwest_2_block'})
                        world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_3_block'})                          
                ## Only Block 2 if "next back-to-back" = True and previous origin is "west-northwest"                           
                    elif direction == 'north_east' and prev_origin == 'west-northwest':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_northsouth_1_block'})                         
                        world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_3_block'})
                        world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'})                          

                elif origin_direction == 'east-southeast':
                    # print('East-Southeast Ballast Placement, facing North and turning East')                        
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above                   
                    if direction == 'north_south':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_2_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'cardinal', 'value': 'stair_northsouth_1_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})                         
                ## Always Block 1                     
                    elif direction == 'north_east':    
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks   
                        if next_b2b == False:
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_6_block'})                          
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_4_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_4_block'})  
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_northsouth_1_block'})                           
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_eastwest_2_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_6_block'})                          
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_4_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_4_block'})  
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_northsouth_1_block'})
                ## Only Block 2 if "next back-to-back" = False                                                        
                    elif direction == 'east_west':
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_2_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'transition', 'value': 'stair_eastwest_2_block'})
                        placed_ballast_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'skip', 'value': 'skip'})

                elif origin_direction == 'north-northwest':
                    # print('North-Northwest Ballast Placement, facing West and turning North')                        
                ## ALways Block 0; also Block 3 if Block 1 "next back-to-back" = True, however, will be reported as Happy Path, so logic embedded in the Happy Path Test above                   
                    if direction == 'east_west':
                        world.set_version_block(x, y, z + 1, dimension, (platform, version_number), stair_eastwest_1_block, None)
                        world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'cardinal', 'value': 'stair_eastwest_2_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'}) 
                ## Always Block 1                     
                    elif direction == 'north_east':    
                        next_b2b = placed_blocks[placed_ballast_iter + 1]['b2b']
                    ## If the next block in the sequence is not a back-to-back diagonal, set four blocks   
                        if next_b2b == False:
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'corner', 'value': 'stair_corner_6_block'})                          
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_4_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_corner_4_block'})  
                            world.set_version_block(x - 1, y, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_northsouth_1_block'})                           
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'corner', 'value': 'stair_eastwest_2_block'})
                    ## If the next block in the sequence is a back-to-back diagonal, set three blocks to accomodate the addional corner
                        else:
                            world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                            world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_6_block'})                          
                            world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_4_block, None)
                            world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_4_block'})  
                            world.set_version_block(x, y, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                            world.set_version_block(x, y + 2, z + 1, dimension, (platform, version_number), air_block, None)                            
                            placed_ballast_inner.append({'x': x, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_eastwest_2_block'})
                ## Only Block 2 if "next back-to-back" = False                                                        
                    elif direction == 'north_south':
                        world.set_version_block(x - 1, y, z, dimension, (platform, version_number), stair_northsouth_1_block, None)
                        world.set_version_block(x - 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'transition', 'value': 'stair_northsouth_1_block'})
                        placed_ballast_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'skip', 'value': 'skip'})

            ## (direction == 'south_west' and origin_direction == 'north_east')
            ## True for both E-SE b2b and N-NW b2b
                elif (direction == 'south_west' and origin_direction == 'north_east'):
                    prev_origin = placed_blocks[placed_ballast_iter - 1]['origin_direction']
                ## Only Block 2 if "next back-to-back" = True and previous origin is "east-southeast"                                           
                    if direction == 'south_west' and prev_origin == 'east-southeast':
                        world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_6_block, None)
                        world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_6_block'})                         
                        world.set_version_block(x + 1, y, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 1, z, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z, dimension, (platform, version_number), air_block, None)                                                
                        placed_ballast_inner.append({'x': x + 1, 'y': y, 'z': z, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_northsouth_2_block'})
                        world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x - 1, 'y': y, 'z': z + 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'})                          
                ## Only Block 2 if "next back-to-back" = True and previous origin is "north-northwest"                           
                    elif direction == 'south_west' and prev_origin == 'north-northwest':
                        world.set_version_block(x, y, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_outer.append({'x': x, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_eastwest_2_block'})                         
                        world.set_version_block(x - 1, y, z + 1, dimension, (platform, version_number), stair_corner_6_block, None)
                        world.set_version_block(x - 1, y + 1, z + 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x - 1, y + 2, z + 1, dimension, (platform, version_number), air_block, None)
                        placed_ballast_inner.append({'x': x - 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'inner', 'state': 'diagonal', 'value': 'stair_corner_6_block'})
                        world.set_version_block(x + 1, y, z - 1, dimension, (platform, version_number), stair_corner_3_block, None)
                        world.set_version_block(x + 1, y + 1, z - 1, dimension, (platform, version_number), air_block, None)
                        world.set_version_block(x + 1, y + 2, z - 1, dimension, (platform, version_number), air_block, None)                        
                        placed_ballast_outer.append({'x': x + 1, 'y': y, 'z': z - 1, 'count': placed_ballast_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'position': 'outer', 'state': 'diagonal', 'value': 'stair_corner_3_block'}) 

                placed_ballast_iter += 1

        return placed_ballast_inner, placed_ballast_outer   

###
### In order to place supports where we want them, we need to test if there is solid ground beneath the placed blocks.
### The functions below will test the "placed_ballast_inner", "placed_blocks", and "placed_ballast_outer" lists to determine if there is solid ground beneath them.
### We'll return three lists: "placed_ballast_inner", "placed_ballast_outer", and "placed_ballast_core" with the results of the tests.
###
    @staticmethod
    def find_solid_ground(coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_ballast_inner, placed_ballast_outer):
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        placed_block_x_z_inner = []
        placed_block_x_z_core = []
        placed_block_x_z_outer = []
        print('Find Solid Ground Function!')
        placed_block_inner_test_iter = 0
        placed_block_core_test_iter = 0
        placed_block_outer_test_iter = 0

    ###
    ###  LOOP 1 -- The "Inner" Ballast Blocks
    ###
        def test_inner_block_air_loop(placed_block_x_z_inner, air_depth, water_depth, count):
            x = placed_block_x_z_inner[-1]['x']
            y = placed_block_x_z_inner[-1]['y']
            z = placed_block_x_z_inner[-1]['z']
            direction = placed_block_x_z_inner[-1]['direction']
            origin_direction = placed_block_x_z_inner[-1]['origin_direction']
            facing = placed_block_x_z_inner[-1]['facing']
            b2b = placed_block_x_z_inner[-1]['b2b']
            state = placed_block_x_z_inner[-1]['state']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]            
            if test_block.blockstate == 'universal_minecraft:air':
                placed_block_x_z_inner[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'air', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                air_depth += 1
                # print('Air block found at:', x, y - 1, z)
                # print(placed_block_x_z_inner)
                return placed_block_x_z_inner, air_depth, water_depth, True, True
            elif test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_inner[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_inner)
                return placed_block_x_z_inner, air_depth, water_depth, False, True                
            else:
                solid_block_y = str(air_depth + 1)
                # print('Air block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of:', air_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_inner[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                return placed_block_x_z_inner, air_depth, water_depth, False, False                 

        def test_block_water_loop(placed_block_x_z_inner, air_depth, water_depth, count):
            x = placed_block_x_z_inner[-1]['x']
            y = placed_block_x_z_inner[-1]['y']
            z = placed_block_x_z_inner[-1]['z']
            direction = placed_block_x_z_inner[-1]['direction']
            origin_direction = placed_block_x_z_inner[-1]['origin_direction']
            facing = placed_block_x_z_inner[-1]['facing']
            b2b = placed_block_x_z_inner[-1]['b2b']
            state = placed_block_x_z_inner[-1]['state']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]          
            if test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_inner[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_air)
                return placed_block_x_z_inner, water_depth, True
            else:
                solid_block_y = str(air_depth + water_depth + 1)
                # print('Water block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of: ', air_depth, 'and water depth of: ', water_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_inner[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                return placed_block_x_z_inner, water_depth, False   


## We need to handle the 'skip' state blocks differently than other states.  However, we don't want to completely skip the test.
## So, we let's sort this out properly after dinner. . . .


        for block in placed_ballast_inner:
            state = block['state']
            x = block['x']
            y = block['y']
            z = block['z']
            air_depth = 0
            water_depth = 0
            count = block['count']
            direction = block['direction']
            origin_direction = block['origin_direction']
            facing = block['facing']
            b2b = block['b2b']
            state = block['state']
            if state == 'skip':
                placed_block_x_z_inner.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'status': 'NA', 'air_depth': 'NA', 'water_depth': 'NA', 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                continue
            test_block = world.get_block(x, y - 1, z, dimension)
            # print('Test Block:', test_block.blockstate)
            keep_testing_for_air = True
            keep_testing_for_water = True
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
            if test_block.blockstate == 'universal_minecraft:air':
                air_depth_1 = str(air_depth + 1)
                placed_block_x_z_inner.append({'x': x, 'y': y - 1, 'z': z, 'status': 'air at y - ' + air_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                air_depth += 1
                # print('Air block found at:', x, y - 1, z)                        
                keep_testing_for_air = True
                keep_testing_for_water = True
            elif test_block.blockstate in water_states:
                water_depth_1 = str(air_depth + 1)
                placed_block_x_z_inner.append({'x': x, 'y': y - 1, 'z': z, 'status': 'water at y - ' + water_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                # print('Water block found at:', x, y - 1, z)                        
                keep_testing_for_air = False
                keep_testing_for_water = True
            else:                
                placed_block_x_z_inner.append({'x': x, 'y': y, 'z': z, 'status': 'solid block at y - 1', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_inner_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                # print('No air blocks at this x, z location:', x, z)
                keep_testing_for_air = False
                keep_testing_for_water = False
            # print('At x = ', x, 'z = ', z, 'keep testing for air:', keep_testing_for_air)
            # print('At x = ', x, 'z = ', z, 'keep testing for water:', keep_testing_for_water)                                
            while keep_testing_for_air:
                placed_block_x_z_inner, air_depth, water_depth, keep_testing_for_air, keep_testing_for_water =  test_inner_block_air_loop(placed_block_x_z_inner, air_depth, water_depth, count)
            while keep_testing_for_water:
                placed_block_x_z_inner, water_depth, keep_testing_for_water = test_block_water_loop(placed_block_x_z_inner, air_depth, water_depth, count)
            placed_block_inner_test_iter += 1
    ## Uncomment the print statements below to see the results of Inner the tests
        # print('Inner Test Block Dict', placed_block_x_z_inner)
        # print('\n')
        # print('Core Blocks Placed = ', placed_block_iter, 'vs ', 'Inner Test Iterations = ', placed_block_inner_test_iter)

    ###
    ###  LOOP 2 -- The "Core" Roadbed Blocks
    ###

        def test_core_block_air_loop(placed_block_x_z_core, air_depth, water_depth, count):
            x = placed_block_x_z_core[-1]['x']
            y = placed_block_x_z_core[-1]['y']
            z = placed_block_x_z_core[-1]['z']
            direction = placed_block_x_z_core[-1]['direction']
            origin_direction = placed_block_x_z_core[-1]['origin_direction']
            facing = placed_block_x_z_core[-1]['facing']
            b2b = placed_block_x_z_core[-1]['b2b']
            state = placed_block_x_z_core[-1]['state']
            use_case = placed_block_x_z_core[-1]['use_case']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]            
            if test_block.blockstate == 'universal_minecraft:air':
                placed_block_x_z_core[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'air', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case}
                air_depth += 1
                # print('Air block found at:', x, y - 1, z)
                # print(placed_block_x_z_core)
                return placed_block_x_z_core, air_depth, water_depth, True, True
            elif test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_core[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_core)
                return placed_block_x_z_core, air_depth, water_depth, False, True                
            else:
                solid_block_y = str(air_depth + 1)
                # print('Air block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of:', air_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_core[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case}
                return placed_block_x_z_core, air_depth, water_depth, False, False                 

        def test_core_block_water_loop(placed_block_x_z_core, air_depth, water_depth, count):
            x = placed_block_x_z_core[-1]['x']
            y = placed_block_x_z_core[-1]['y']
            z = placed_block_x_z_core[-1]['z']
            direction = placed_block_x_z_core[-1]['direction']
            origin_direction = placed_block_x_z_core[-1]['origin_direction']
            facing = placed_block_x_z_core[-1]['facing']
            b2b = placed_block_x_z_core[-1]['b2b']
            state = placed_block_x_z_core[-1]['state']
            use_case = placed_block_x_z_core[-1]['use_case']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]          
            if test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_core[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_air)
                return placed_block_x_z_core, water_depth, True
            else:
                solid_block_y = str(air_depth + water_depth + 1)
                # print('Water block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of: ', air_depth, 'and water depth of: ', water_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_core[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case}
                return placed_block_x_z_core, water_depth, False   

        for block in placed_blocks:
            x = block['x']
            y = block['y']
            z = block['z']
            air_depth = 0
            water_depth = 0
            count = block['count']
            direction = block['direction']
            origin_direction = block['origin_direction']
            facing = block['facing']
            b2b = block['b2b']
            state = block['state']
            use_case = block['use_case']
            test_block = world.get_block(x, y - 1, z, dimension)
            #print('Test Block:', test_block.blockstate)
            keep_testing_for_air = True
            keep_testing_for_water = True
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
            if test_block.blockstate == 'universal_minecraft:air':
                air_depth_1 = str(air_depth + 1)
                placed_block_x_z_core.append({'x': x, 'y': y - 1, 'z': z, 'status': 'air at y - ' + air_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case})
                air_depth += 1
                #print('Air block found at:', x, y - 1, z)                        
                keep_testing_for_air = True
                keep_testing_for_water = True
            elif test_block.blockstate in water_states:
                water_depth_1 = str(air_depth + 1)
                placed_block_x_z_core.append({'x': x, 'y': y - 1, 'z': z, 'status': 'water at y - ' + water_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case})
                #print('Water block found at:', x, y - 1, z)                        
                keep_testing_for_air = False
                keep_testing_for_water = True
            else:                
                placed_block_x_z_core.append({'x': x, 'y': y, 'z': z, 'status': 'solid block at y - 1', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_core_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state, 'use_case': use_case})
                # print('No air blocks at this x, z location:', x, z)
                keep_testing_for_air = False
                keep_testing_for_water = False
            #print('At x = ', x, 'z = ', z, 'keep testing for air:', keep_testing_for_air)
            #print('At x = ', x, 'z = ', z, 'keep testing for water:', keep_testing_for_water)                                
            while keep_testing_for_air:
                placed_block_x_z_core, air_depth, water_depth, keep_testing_for_air, keep_testing_for_water =  test_core_block_air_loop(placed_block_x_z_core, air_depth, water_depth, count)
            while keep_testing_for_water:
                placed_block_x_z_core, water_depth, keep_testing_for_water = test_core_block_water_loop(placed_block_x_z_core, air_depth, water_depth, count)
            placed_block_core_test_iter += 1
    ## Uncomment to print the results of the Core Block Tests
        # print('Core Test Block Dict', placed_block_x_z_core)
        # print('\n')
        # print('Core Blocks placed = ', placed_block_iter, 'vs ', 'Core Test Iterations = ', placed_block_core_test_iter)

    ###
    ###  LOOP 3 -- The "Outer" Roadbed Blocks
    ###

        def test_outer_block_air_loop(placed_block_x_z_outer, air_depth, water_depth, count):
            x = placed_block_x_z_outer[-1]['x']
            y = placed_block_x_z_outer[-1]['y']
            z = placed_block_x_z_outer[-1]['z']
            direction = placed_block_x_z_outer[-1]['direction']
            origin_direction = placed_block_x_z_outer[-1]['origin_direction']
            facing = placed_block_x_z_outer[-1]['facing']
            b2b = placed_block_x_z_outer[-1]['b2b']
            state = placed_block_x_z_outer[-1]['state']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]            
            if test_block.blockstate == 'universal_minecraft:air':
                placed_block_x_z_outer[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'air', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count,'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                air_depth += 1
                # print('Air block found at:', x, y - 1, z)
                # print(placed_block_x_z_outer)
                return placed_block_x_z_outer, air_depth, water_depth, True, True
            elif test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_outer[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count,'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_outer)
                return placed_block_x_z_outer, air_depth, water_depth, False, True                
            else:
                solid_block_y = str(air_depth + 1)
                # print('Air block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of:', air_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_outer[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                return placed_block_x_z_outer, air_depth, water_depth, False, False                 

        def test_outer_block_water_loop(placed_block_x_z_outer, air_depth, water_depth, count):
            x = placed_block_x_z_outer[-1]['x']
            y = placed_block_x_z_outer[-1]['y']
            z = placed_block_x_z_outer[-1]['z']
            direction = placed_block_x_z_outer[-1]['direction']
            origin_direction = placed_block_x_z_outer[-1]['origin_direction']
            facing = placed_block_x_z_outer[-1]['facing']
            b2b = placed_block_x_z_outer[-1]['b2b']
            state = placed_block_x_z_outer[-1]['state']
            test_block = world.get_block(x, y - 1, z, dimension)
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]          
            if test_block.blockstate in water_states:
                water_depth += 1
                placed_block_x_z_outer[-1] = {'x': x, 'y': y - 1, 'z': z, 'status': 'water', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                # print('Water block found at:', x, y - 1, z)
                # print(placed_block_x_z_air)
                return placed_block_x_z_outer, water_depth, True
            else:
                solid_block_y = str(air_depth + water_depth + 1)
                # print('Water block test ended for x = ', x, 'z = ', z, 'at y = ', y - 1, 'with air depth of: ', air_depth, 'and water depth of: ', water_depth, 'solid block at y - ', solid_block_y)
                placed_block_x_z_outer[-1] = {'x': x, 'y': y, 'z': z, 'status': 'solid block at y - ' + solid_block_y, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state}
                return placed_block_x_z_outer, water_depth, False   

        for block in placed_ballast_outer:
            x = block['x']
            y = block['y']
            z = block['z']
            air_depth = 0
            water_depth = 0
            count = block['count']
            direction = block['direction']
            origin_direction = block['origin_direction']
            facing = block['facing']
            b2b = block['b2b']
            state = block['state']
            if state == 'skip':
                placed_block_x_z_outer.append({'x': 'NA', 'y': 'NA', 'z': 'NA', 'status': 'NA', 'air_depth': 'NA', 'water_depth': 'NA', 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                continue
            test_block = world.get_block(x, y - 1, z, dimension)
            #print('Test Block:', test_block.blockstate)
            keep_testing_for_air = True
            keep_testing_for_water = True
            water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
            if test_block.blockstate == 'universal_minecraft:air':
                air_depth_1 = str(air_depth + 1)
                placed_block_x_z_outer.append({'x': x, 'y': y - 1, 'z': z, 'status': 'air at y - ' + air_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                air_depth += 1
                #print('Air block found at:', x, y - 1, z)                        
                keep_testing_for_air = True
                keep_testing_for_water = True
            elif test_block.blockstate in water_states:
                water_depth_1 = str(air_depth + 1)
                placed_block_x_z_outer.append({'x': x, 'y': y - 1, 'z': z, 'status': 'water at y - ' + water_depth_1, 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                # print('Water block found at:', x, y - 1, z)                        
                keep_testing_for_air = False
                keep_testing_for_water = True
            else:                
                placed_block_x_z_outer.append({'x': x, 'y': y, 'z': z, 'status': 'solid block at y - 1', 'air_depth': air_depth, 'water_depth': water_depth, 'count': count, 'iteration': placed_block_outer_test_iter, 'direction': direction, 'origin_direction': origin_direction, 'facing': facing, 'b2b': b2b, 'state': state})
                # print('No air blocks at this x, z location:', x, z)
                keep_testing_for_air = False
                keep_testing_for_water = False
            #print('At x = ', x, 'z = ', z, 'keep testing for air:', keep_testing_for_air)
            #print('At x = ', x, 'z = ', z, 'keep testing for water:', keep_testing_for_water)                                
            while keep_testing_for_air:
                placed_block_x_z_outer, air_depth, water_depth, keep_testing_for_air, keep_testing_for_water =  test_outer_block_air_loop(placed_block_x_z_outer, air_depth, water_depth, count)
            while keep_testing_for_water:
                placed_block_x_z_outer, water_depth, keep_testing_for_water = test_outer_block_water_loop(placed_block_x_z_outer, air_depth, water_depth, count)
            placed_block_outer_test_iter += 1
    ## Uncomment to print the results of the Outer Block Tests        
        # print('Outer Test Block Dict', placed_block_x_z_outer)
        # print('\n')
        # print('Core Blocks placed = ', placed_block_iter, 'vs ', 'Outer Test Iterations = ', placed_block_outer_test_iter)

        return placed_block_x_z_inner, placed_block_x_z_core, placed_block_x_z_outer

#
#
#   YEEEEEEE HAWWWWWWW
#
#   We have successfully tested the blocks beneath the placed ballast, placed blocks, and placed ballast outer blocks
#
#   Now we need to test the three against each other at each "count" and figure out which blocks to put under them
#
#


    @staticmethod
    def place_supports(cribbing_choice, minus1_choice, coordinates, world, dimension, placed_blocks, placed_block_iter, placed_rails, placed_rails_iter, placed_ballast_inner, placed_ballast_outer, placed_block_x_z_inner, placed_block_x_z_core, placed_block_x_z_outer, support_locations):
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        print('Support Function!')
        # print('Cribbing Choice:', cribbing_choice)
        # print('Underpinning Choice:', minus1_choice)

        if cribbing_choice == 'Dark Oak':
            cribbing_block = Block('minecraft', 'dark_oak_log', {"pillar_axis": StringTag("y")})
        elif cribbing_choice == "Smooth Stone":
            cribbing_block = Block('minecraft', 'smooth_stone')
        elif cribbing_choice ==  "Deepslate Tile":
            cribbing_block = Block('minecraft', 'deepslate_tiles')
        elif cribbing_choice == "Iron Block":
            cribbing_block = Block('minecraft', 'iron_block')

        if minus1_choice == 'Dark Oak':
            underpinning_block = Block('minecraft', 'dark_oak_log', {"pillar_axis": StringTag("y")})
        elif minus1_choice == "Smooth Stone":
            underpinning_block = Block('minecraft', 'smooth_stone')
        elif minus1_choice ==  "Deepslate Tile":
            underpinning_block = Block('minecraft', 'deepslate_tiles')
        elif minus1_choice == "Iron Block":
            underpinning_block = Block('minecraft', 'iron_block')

        def group_by_count(dictionaries):
            grouped_data = defaultdict(list)
            for i, dictionary in enumerate(dictionaries):
                for item in dictionary:
                    # Add a new field to the item indicating its source dictionary
                    item['source'] = i
                    grouped_data[item['count']].append(item)
            return grouped_data

    # Define the dictionaries to group
        dict1 = placed_block_x_z_inner
        dict2 = placed_block_x_z_core
        dict3 = placed_block_x_z_outer
    # Group the dictionaries by the 'count' field
        grouped_blocks = group_by_count([dict1, dict2, dict3])
    ## Debugging print statement for block data aggregated by count # in their respective lists
        # print('Grouped Blocks:', grouped_blocks)        

    # Initialize "consolidated_by_count" to store the results
        consolidated_by_count = {}    
    # Iterate over the grouped data

        for count, objects in grouped_blocks.items():
            # Initialize lists to store the air_depth and water_depth values
            x_values = [[], [], []]
            y_values = [[], [], []]
            z_values = [[], [], []]
            air_depths = [[], [], []]
            water_depths = [[], [], []]
            direction = [[], [], []]
            origin_direction = [[], [], []]
            facing = [[], [], []]
            b2b = [[], [], []]
            states = [[], [], []]
            use_cases = [[], [], []]

            # Initialize a list to store the indices of 'NA' entries
            na_indices = []

            # Iterate over the objects in this count group
            for obj in objects:
                # Use the 'source' field to determine the index
                index = obj['source']
                # Add the x, y, and z values to the appropriate lists
                x_values[index].append(obj['x'] if obj['x'] is not None else "None")
                y_values[index].append(obj['y'] if obj['y'] is not None else "None")
                z_values[index].append(obj['z'] if obj['z'] is not None else "None")
                # Add the air_depth and water_depth values to the appropriate lists
                air_depths[index].append(obj['air_depth'] if obj['air_depth'] is not None else "None")
                water_depths[index].append(obj['water_depth'] if obj['water_depth'] is not None else "None")
                # Check if the keys are in the dictionary before trying to access them
                direction[index].append(obj['direction'] if 'direction' in obj else "None")
                origin_direction[index].append(obj['origin_direction'] if 'origin_direction' in obj else "None")
                facing[index].append(obj['facing'] if 'facing' in obj else "None")
                b2b[index].append(obj['b2b'] if 'b2b' in obj else "None")
                states[index].append(obj['state'] if 'state' in obj else "None")
                use_cases[index].append(obj['use_case'] if 'use_case' in obj else "None")

        # Add the values to the consolidated_by_count dictionary
            consolidated_by_count[count] = {
                'Direction': {'Inner': direction[0], 'Core': direction[1], 'Outer': direction[2]},
                'Origin Direction': {'Inner': origin_direction[0], 'Core': origin_direction[1], 'Outer': origin_direction[2]},
                'Facing': {'Inner': facing[0], 'Core': facing[1], 'Outer': facing[2]},
                'Back_to_Back': {'Inner': b2b[0], 'Core': b2b[1], 'Outer': b2b[2]},
                'States': {'Inner': states[0], 'Core': states[1], 'Outer': states[2]},
                'Use Cases': {'Inner': use_cases[0], 'Core': use_cases[1], 'Outer': use_cases[2]},
                'X': {'Inner': x_values[0], 'Core': x_values[1], 'Outer': x_values[2]},
                'Y': {'Inner': y_values[0], 'Core': y_values[1], 'Outer': y_values[2]},
                'Z': {'Inner': z_values[0], 'Core': z_values[1], 'Outer': z_values[2]},
                'Air Depths': {'Inner': air_depths[0], 'Core': air_depths[1], 'Outer': air_depths[2]},
                'Water Depths': {'Inner': water_depths[0], 'Core': water_depths[1], 'Outer': water_depths[2]},
                'Span': {'Inner': False, 'Core': False, 'Outer': False},
                'Span Length': {'Inner': 0, 'Core': 0, 'Outer': 0},
                'Span Type': 'None',
                'Span Count': {'Number_of_Spans': 0}
            }

        def mark_floating_blocks(consolidated_by_count):
        # Now we can access the consolidated data for each count
            # Now we can access the consolidated data for each count
            for count, data in consolidated_by_count.items():
                # Convert all 'NA' depths to 0 before continuing
                air_depths = [0 if depth == 'NA' else int(depth) for depth in data['Air Depths']['Inner'] + data['Air Depths']['Core'] + data['Air Depths']['Outer']]
                water_depths = [0 if depth == 'NA' else int(depth) for depth in data['Water Depths']['Inner'] + data['Water Depths']['Core'] + data['Water Depths']['Outer']]
                states = data['States']['Inner'] + data['States']['Core'] + data['States']['Outer']
                directions = data['Direction']['Inner'] + data['Direction']['Core'] + data['Direction']['Outer']
                facings = data['Facing']['Inner'] + data['Facing']['Core'] + data['Facing']['Outer']
                b2b = data['Back_to_Back']['Inner'] + data['Back_to_Back']['Core'] + data['Back_to_Back']['Outer']
                use_cases = data['Use Cases']['Inner'] + data['Use Cases']['Core'] + data['Use Cases']['Outer']
                # print('Span Testing...')
                # print(directions)
                # print(facings)
                if count == 0:
                    # print('First floating iteration in the path.')
                    print('\n')
                else:
                    previous_count = count - 1
                # Let's access the data for the previous count for comparison
                    previous_data = consolidated_by_count[previous_count]
                    previous_span_type = previous_data['Span Type']
                    def try_parse_int(s, default=0):
                        try:
                            return int(s)
                        except ValueError:
                            return default
                    previous_span_count = try_parse_int(previous_data['Span Count']['Number_of_Spans'])
                    previous_span_length_inner = try_parse_int(previous_data['Span Length']['Inner'])
                    previous_span_length_core = try_parse_int(previous_data['Span Length']['Core'])
                    previous_span_length_outer = try_parse_int(previous_data['Span Length']['Outer'])

                if any(use_case == 'drop_pillar' for use_case in use_cases):
                    x_values = data['X']['Core']
                    y_values = data['Y']['Core']
                    z_values = data['Z']['Core']
                    facings = data['Facing']['Core']
                    air_depths = data['Air Depths']['Core']
                    water_depths = data['Water Depths']['Core']
                    # print('Drop Pillar Found!', x_values, y_values, z_values, air_depths, water_depths, 'Facing:', facings)
                    support_locations.append({'x': x_values, 'y': y_values, 'z': z_values, 'air_depth': air_depths, 'water_depth': water_depths, 'facing': facings})

            # Check if 'Air Depths' for 'Inner', 'Core', and 'Outer' are all greater than zero
                elif all(air_depth > 0 for state, air_depth in zip(states, air_depths) if state != 'skip') or any(use_case == 'overpass' for use_case in use_cases):
                    # print("All 'Air Depths' are greater than zero.")
                # Increment 'Span Length' for 'Inner', 'Core', and 'Outer'
                    data['Span']['Inner'] = True
                    data['Span']['Core'] = True
                    data['Span']['Outer'] = True
                    data['Span Type'] = 'Air_Bridge'
                    if count == 0:
                        # print('Start of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
                    elif previous_span_type == 'Air_Bridge' or previous_span_type == 'Dual_Bridge' or previous_span_type == 'Water_Bridge':
                        # print('Continuation of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1
                    else:
                        # print('Start of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1

                elif any((state == 'skip' and air_depth == 0) for state, air_depth in zip(states, air_depths)) and all(air_depth > 0 for state, air_depth in zip(states, air_depths) if state != 'skip'):
                    # print("All 'Air Depths' are greater than zero.")
                # Increment 'Span Length' for 'Inner', 'Core', and 'Outer'
                    data['Span']['Inner'] = True
                    data['Span']['Core'] = True
                    data['Span']['Outer'] = True
                    data['Span Type'] = 'Air_Bridge'
                    if count == 0:
                        # print('Start of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
                    elif previous_span_type == 'Air_Bridge' or previous_span_type == 'Dual_Bridge' or previous_span_type == 'Water_Bridge':
                        # print('Continuation of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1
                    else:
                        # print('Start of Air Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1

                elif any((state == 'skip' and water_depth == 0) for state, water_depth in zip(states, water_depths)) and all(water_depth > 0 for state, water_depth in zip(states, water_depths) if state != 'skip'):
                    # print("All 'Water Depths' are greater than zero.")
                # Increment 'Span Length' for 'Inner', 'Core', and 'Outer'
                    data['Span']['Inner'] = True
                    data['Span']['Core'] = True
                    data['Span']['Outer'] = True
                    data['Span Type'] = 'Water_Bridge'
                    if count == 0:
                        # print('Start of Water Bridge Span')
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
                    elif previous_span_type == 'Water_Bridge' or previous_span_type == 'Dual_Bridge' or previous_span_type == 'Air_Bridge':
                        # print('Continuation of Water Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count                        
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1
                    else:
                        # print('Start of Water Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1                        

                elif all(air_depth > 0 for air_depth in air_depths) and all(water_depth > 0 for water_depth in water_depths):
                    # print("All 'Air Depths' and 'Water Depths' are greater than zero.")
                # Increment 'Span Length' for 'Inner', 'Core', and 'Outer'
                    data['Span']['Inner'] = True
                    data['Span']['Core'] = True
                    data['Span']['Outer'] = True
                    data['Span Type'] = 'Dual_Bridge'
                    if count == 0:
                        # print('Start of Dual Bridge Span')
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
                    elif previous_span_type == 'Dual_Bridge' or previous_span_type == 'Air_Bridge' or previous_span_type == 'Water_Bridge':
                        # print('Continuation of Dual Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count                        
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1  
                    else:
                        # print('Start of Dual Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1                                                                   

            ##
            ## Diagonals are going to be just as much fun as they were up above, or even more so, maybe
            ##
                elif any(state == 'diagonal' for state in states) or any(state == 'corner' for state in states):
                    # print("Diagonal span found.")
                    data['Span']['Inner'] = True
                    data['Span']['Core'] = True
                    data['Span']['Outer'] = True
                    data['Span Type'] = 'Diagonal_Bridge'
                    if count == 0:
                        # print('Start of Diagonal Bridge Span')
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
                    elif previous_span_type == 'Diagonal_Bridge':
                        # print('Continuation of Diagonal Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count                        
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1
                    else:
                        # print('Start of Diagonal Bridge Span')
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1

            # Check if 'Air Depths' for 'Inner' are greater than zero
                elif any(air_depth != 'NA' and air_depth > 0 for air_depth in data['Air Depths']['Inner']):
                # They are, so check if 'Air Depths' for 'Outer' are also greater than zero    
                    if any(air_depth != 'NA' and air_depth > 0 for air_depth in data['Air Depths']['Outer']):
                        if count == 0:
                            # print('Start of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Dual_Cribbing'
                            data['Span Count']['Number_of_Spans'] = 1
                            data['Span Length']['Inner'] = 1
                            data['Span Length']['Outer'] = 1
                        elif previous_span_type == 'Dual_Cribbing':
                            # print('Continuation of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Count']['Number_of_Spans'] = previous_span_count                            
                            data['Span Type'] = 'Dual_Cribbing'                            
                            data['Span Length']['Inner'] = previous_span_length_inner + 1
                            data['Span Length']['Core'] = previous_span_length_core                            
                            data['Span Length']['Outer'] = previous_span_length_outer + 1 
                        else:
                            # print('Start of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Dual_Cribbing'                            
                            data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                            data['Span Length']['Inner'] = 1
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Outer'] = 1                        
                    else:    
                        if count == 0:
                            # print('Start of Inner Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = False
                            data['Span Type'] = 'Inner_Cribbing'                               
                            data['Span Count']['Number_of_Spans'] = 1                            
                            data['Span Length']['Inner'] = 1
                        elif previous_span_type == 'Inner_Cribbing':
                            # print('Continuation of Inner Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = False
                            data['Span Count']['Number_of_Spans'] = previous_span_count                            
                            data['Span Type'] = 'Inner_Cribbing'                             
                            data['Span Length']['Inner'] = previous_span_length_inner + 1
                            data['Span Length']['Core'] = previous_span_length_core
                            data['Span Length']['Outer'] = previous_span_length_outer
                        else:
                            # print('Start of Inner Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = False
                            data['Span Type'] = 'Inner_Cribbing'                            
                            data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                            data['Span Length']['Inner'] = 1
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Outer'] = 0

            # Check if 'Air Depths' for 'Outer' are greater than zero
                elif any(air_depth != 'NA' and air_depth > 0 for air_depth in data['Air Depths']['Outer']):
                # They are, so check if 'Air Depths' for 'Inner' are also greater than zero    
                    if any(air_depth != 'NA' and air_depth > 0 for air_depth in data['Air Depths']['Inner']):
                        if count == 0:
                            # print('Start of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Dual_Cribbing'                             
                            data['Span Count']['Number_of_Spans'] = 1
                            data['Span Length']['Inner'] = 1
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Outer'] = 1
                        elif previous_span_type == 'Dual_Cribbing':
                            # print('Continuation of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Dual_Cribbing'
                            data['Span Count']['Number_of_Spans'] = previous_span_count                                                         
                            data['Span Length']['Inner'] = previous_span_length_inner + 1
                            data['Span Length']['Core'] = previous_span_length_core                            
                            data['Span Length']['Outer'] = previous_span_length_outer + 1
                        else:
                            # print('Start of Dual Cribbing Span')
                            data['Span']['Inner'] = True
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Dual_Cribbing'                             
                            data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                            data['Span Length']['Inner'] = 1
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Outer'] = 1  
                    else:    
                        if count == 0:
                            # print('Start of Outer Cribbing Span')
                            data['Span']['Inner'] = False
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Outer_Cribbing'                               
                            data['Span Count']['Number_of_Spans'] = 1
                            data['Span Length']['Outer'] = 1
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Inner'] = 0
                        elif previous_span_type == 'Outer_Cribbing':
                            # print('Continuation of Outer Cribbing Span')
                            data['Span']['Inner'] = False
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Outer_Cribbing'
                            data['Span Count']['Number_of_Spans'] = previous_span_count                                                          
                            data['Span Length']['Outer'] = previous_span_length_outer + 1
                            data['Span Length']['Core'] = previous_span_length_core
                            data['Span Length']['Inner'] = previous_span_length_inner
                        else:
                            # print('Start of Outer Cribbing Span')
                            data['Span']['Inner'] = False
                            data['Span']['Core'] = False
                            data['Span']['Outer'] = True
                            data['Span Type'] = 'Outer_Cribbing'                              
                            data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                            data['Span Length']['Inner'] = 0
                            data['Span Length']['Core'] = 0
                            data['Span Length']['Outer'] = 1    
            # Solid ground beneath all blocks
                else:
                    # print("No 'Air Depths' are greater than zero.")
                    if count == 0:
                        # print('Start of Solid Span')
                        data['Span']['Inner'] = False
                        data['Span']['Core'] = False
                        data['Span']['Outer'] = False
                        data['Span Type'] = 'Solid'
                        data['Span Count']['Number_of_Spans'] = 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1

                    elif previous_span_type == 'Solid':
                        # print('Continuation of Solid Span')
                        data['Span Type'] = 'Solid'                        
                        data['Span Count']['Number_of_Spans'] = previous_span_count
                        data['Span Length']['Inner'] = previous_span_length_inner + 1
                        data['Span Length']['Core'] = previous_span_length_core + 1
                        data['Span Length']['Outer'] = previous_span_length_outer + 1
                    else:
                        # print('Start of Solid Span')
                        data['Span Type'] = 'Solid'                        
                        data['Span Count']['Number_of_Spans'] = previous_span_count + 1
                        data['Span Length']['Inner'] = 1
                        data['Span Length']['Core'] = 1
                        data['Span Length']['Outer'] = 1
            ## All the debugging!
            ## This gives us a complete view of the data for each count    
                # print(f'Count {count}:')
                # print(f"Direction: {data['Direction']}")
                # print(f"Origin Direction: {data['Origin Direction']}")            
                # print(f"Facing: {data['Facing']}")
                # print(f"Back-to-Back: {data['Back_to_Back']}")
                # print(f"States: {data['States']}")
                # print(f"Use Cases: {data['Use Cases']}")
                # print(f"X: {data['X']}")
                # print(f"Y: {data['Y']}")
                # print(f"Z: {data['Z']}")
                # print(f"Air Depths: {air_depths}")
                # print(f"Water Depths: {water_depths}")
                # print(f"Span Type: {data['Span Type']}")
                # print(f"Span Len Inner: {data['Span Length']['Inner']}")
                # print(f"Span Len Core: {data['Span Length']['Core']}")
                # print(f"Span Len Outer: {data['Span Length']['Outer']}")

            return consolidated_by_count, support_locations       

        consolidated_by_count, support_locations = mark_floating_blocks(consolidated_by_count)
        #print('Consolidated by Count:', consolidated_by_count)

        def place_support_blocks(consolidated_by_count):
            print('Placing Support Blocks!')

            def consolidate_by_span(consolidated_by_count):
                def try_int(value, default=0):
                    try:
                        return int(value)
                    except ValueError:
                        return default

                flattened_data = {}
                positions = ['Inner', 'Core', 'Outer']
                for count, data in consolidated_by_count.items():
                    for index, position in enumerate(positions):
                        states = data.get('States', {}).get(position, [''])
                        directions = data.get('Direction', {}).get(position, [''])
                        origin_directions = data.get('Origin Direction', {}).get(position, [''])
                        facings = data.get('Facing', {}).get(position, [''])
                        x_values = data['X'][position] if isinstance(data['X'], dict) else []
                        y_values = data['Y'][position] if isinstance(data['Y'], dict) else []
                        z_values = data['Z'][position] if isinstance(data['Z'], dict) else []
                        span_type = data.get('Span Type', '')
                        span_length = try_int(data['Span Length'][position]) if isinstance(data['Span Length'], dict) else 0
                        span_count = try_int(data['Span Count']['Number_of_Spans']) if isinstance(data['Span Count'], dict) else 0
                        air_depth = data['Air Depths'][position] if isinstance(data['Air Depths'], dict) and data['Air Depths'][position] else 0
                        water_depth = data['Water Depths'][position] if isinstance(data['Water Depths'], dict) and data['Water Depths'][position] else 0
                        max_length = max(len(x_values), len(y_values), len(z_values))
                        directions.extend([''] * (max_length - len(directions)))
                        origin_directions.extend([''] * (max_length - len(origin_directions)))
                        facings.extend([''] * (max_length - len(facings)))
                        states.extend([''] * (max_length - len(states)))
                        if states != 'skip':
                            for i in range(max_length):
                                block_data = {
                                    'count': count,
                                    'position': position,
                                    'x': x_values[i] if i < len(x_values) else '',
                                    'y': y_values[i] if i < len(y_values) else '',
                                    'z': z_values[i] if i < len(z_values) else '',
                                    'span_type': span_type,
                                    'span_length': span_length,
                                    'direction': directions[i] if i < len(directions) else '',
                                    'origin_direction': origin_directions[i] if i < len(origin_directions) else '',
                                    'facing': facings[i] if i < len(facings) else '',
                                    'state': states[i] if i < len(states) else '',
                                    'use_case': states[i] if i < len(states) else '',
                                    'air_depth': air_depth[i] if i < len(air_depth) else '',
                                    'water_depth': water_depth[i] if i < len(water_depth) else ''
                                }
                                if span_count not in flattened_data:
                                    flattened_data[span_count] = []
                                flattened_data[span_count].append(block_data)
                return flattened_data

            consolidated_by_span = consolidate_by_span(consolidated_by_count)
            # print('Data by Span Number:', consolidated_by_span)

            def find_and_label_max_span_length(data):
                span_labels = {
                    1: "short",
                    2: "medium",
                    3: "long"
                }
                labeled_data = {}
                for span, blocks in data.items():
                    # Ignore 'NA' entries when calculating max_span_length
                    span_lengths = [int(block['span_length']) for block in blocks if block['span_length'] != 'NA']
                    if span_lengths:  # Check if the list is not empty
                        max_span_length = max(span_lengths)
                        if max_span_length <= 10:
                            span_label = span_labels[1]
                        elif max_span_length <= 20:
                            span_label = span_labels[2]
                        else:
                            span_label = span_labels[3]
                        labeled_data[span] = {
                            'blocks': blocks,
                            'max_span_length': max_span_length,
                            'span_label': span_label
                        }
                return labeled_data
            
            labeled_data = find_and_label_max_span_length(consolidated_by_span)

            def set_support_blocks(labeled_data):
                for span, data in labeled_data.items():
                    blocks = data['blocks']
                    max_length = data['max_span_length']  # reference max_length from data
                    span_label = data['span_label']  # reference span_label from data
                    for block in blocks:
                        if block['state'] == 'skip':
                            continue
                        block['span'] = span
                        block['max_length'] = max_length
                        block['span_label'] = span_label
                    ## Debug statements for the block data to compare to the other data above    
                        # print('block data:')
                        # print(block)
                        if block['span_type'] == 'Outer_Cribbing' and block['position'] == 'Outer':
                            if block['air_depth'] > 8:
                                y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                                world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                            else:
                                for y in range(block['y'], block['y'] + block['air_depth'] + block['water_depth']):
                                    world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), cribbing_block, None)
                        elif block['span_type'] == 'Inner_Cribbing' and block['position'] == 'Inner':
                            if block['air_depth'] > 8:
                                y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                                world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                            else:
                                for y in range(block['y'], block['y'] + block['air_depth'] + block['water_depth']):
                                    world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), cribbing_block, None)
                        elif block['span_type'] == 'Dual_Cribbing' and (block['position'] == 'Outer' or block['position'] == 'Inner'):
                            if block['air_depth'] > 8:
                                y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                                world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                            else:
                                for y in range(block['y'], block['y'] + block['air_depth'] + block['water_depth']):
                                    world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), cribbing_block, None)
                        elif block['span_type'] == 'Air_Bridge' and block['position'] in ['Inner', 'Core', 'Outer']:
                            y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                            world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                        elif block['span_type'] == 'Water_Bridge' and block['position'] in ['Inner', 'Core', 'Outer']:
                            y = block['y'] + block['water_depth'] + block['water_depth'] - 1
                            world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                        elif block['span_type'] == 'Dual_Bridge' and block['position'] in ['Inner', 'Core', 'Outer']:
                            y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                            world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)
                        elif block['span_type'] == 'Diagonal_Bridge' and block['position'] in ['Inner', 'Core', 'Outer']:
                            y = block['y'] + block['air_depth'] + block['water_depth'] - 1
                            world.set_version_block(block['x'], y, block['z'], dimension, (platform, version_number), underpinning_block, None)

            set_support_blocks(labeled_data)

        place_support_blocks(consolidated_by_count)

        return support_locations

    @staticmethod
    def read_construction(src_file_path):
        construction_blocks = []
        # print('source file path:', src_file_path)
        with ConstructionReader(src_file_path) as reader:

            construction_blocks = reader.read(0).palette
        # Debug print statement    
            # for i in range(len(construction_blocks)):
            #     print('block:', i, ' = ', construction_blocks[i])

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
                        parsed_block = Build_Railroad.parse_block_type(block_type)
                    # Block dump debug from the construction file    
                        # print('block at position', normalized_origin_x + x, normalized_origin_z + z, '=', parsed_block)
                        construction_blocks.append({'x': normalized_origin_x + x, 'y': normalized_origin_y, 'z': normalized_origin_z + z, 'block': parsed_block})

        return construction_blocks
        ###
        ###  world.set_version_block(x, y, z, dimension, (platform, version_number), stair_eastwest_1_block, None)
        ###

##
## When parsing the block types from the imported Censtuction File, the "version" string needs to be parsed
## These are VERY specific for each block type.
##

    @staticmethod
    def parse_block_type(block_type):
        parsed_block_type = str(block_type)
        # print('parsed block type:', parsed_block_type)
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
        elif '__version__=18108419' in parsed_block_type:
            if 'minecraft:dark_oak_log' in parsed_block_type:
                block_tags = parsed_block_type[parsed_block_type.find('[') + 1: parsed_block_type.find(']')]
                if 'pillar_axis' in block_tags:
                    split_tags = block_tags.split(',')
                    for tag in split_tags:
                        if 'pillar_axis' in tag:
                            axis = tag.split('=')[1].replace('"', '')  # Remove quotes
                            # print('pillar axis:', axis)
                            parsed_block = "Block('{}', '{}', {{\"pillar_axis\": StringTag(\"{}\")}})".format(library, family, axis)
            elif parsed_block_type.find('[') + 21 < len(parsed_block_type) and parsed_block_type[parsed_block_type.find('[') + 21] == ',':
                block_tags = parsed_block_type[parsed_block_type.find(',') + 1: parsed_block_type.find(']')]
                if 'wall' in block_tags:
                    split_tags = block_tags.split(',')
                    east = split_tags[1].split('=')[1].replace('"', '')
                    north = split_tags[2].split('=')[1].replace('"', '')
                    south = split_tags[3].split('=')[1].replace('"', '')
                    west = split_tags[4].split('=')[1].replace('"', '')
                    post = int(split_tags[5].split('=')[1].replace('b', '').replace(']', ''))  # Remove 'b' and ']', then convert to int
                    # print('wall tags:', east, north, south, west, post)
                    parsed_block = "Block('{}', '{}', {{\"wall_connection_type_east\": StringTag(\"{}\"), \"wall_connection_type_north\": StringTag(\"{}\"), \"wall_connection_type_south\": StringTag(\"{}\"), \"wall_connection_type_west\": StringTag(\"{}\"), \"wall_post_bit\": ByteTag({})}})".format(library, family, east, north, south, west, post)
            else:
                parsed_block = "Block('{}', '{}')".format(library, family)

        else:
            parsed_block = "Block('{}', '{}')".format(library, family)


    # Debug print statement
        # print(parsed_block)
    # Construction file block type examples
    # These strings have to be parsed to use them with the set_block method    
        # minecraft:polished_blackstone[__version__=18100737]
        # minecraft:polished_blackstone_wall[__version__=18100737,wall_connection_type_east="short",wall_connection_type_north="none",wall_connection_type_south="short",wall_connection_type_west="none",wall_post_bit=1b]
        return parsed_block

###
### With the coordinates and the blocks, the "set_blocks" method can be called to place the blocks in the world
### We will use the coordinates as the starting point and iterate over the blocks in the "construction_blocks" dictionary
### to place them in the world with the offset coordinates in the dictionary
###

    @staticmethod
    def set_blocks(world: "BaseLevel", dimension: Dimension, support_coordinates, construction_blocks, placed_support_blocks, placed_support_block_iter):
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version        
        for i in range(len(construction_blocks)):
            if isinstance(construction_blocks[i], dict):
                x = support_coordinates['x'] + construction_blocks[i]['x']
                y = support_coordinates['y'] + construction_blocks[i]['y']
                z = support_coordinates['z'] + construction_blocks[i]['z']
                block = eval(construction_blocks[i]['block'])
            else:
                block = construction_blocks[i]
                x, y, z = support_coordinates['x'], support_coordinates['y'], support_coordinates['z']
            world.set_version_block(x, y, z, dimension, (platform, version_number), block, None)
            placed_support_blocks.append({'x': x, 'y': y, 'z': z, 'block': block})

        placed_support_block_iter += 1
    # DEBUG print statement
        # print('Placed Support Blocks:', placed_support_blocks)
        return placed_support_blocks, placed_support_block_iter


export = {
    "name": "Place Rails",  # the name of the plugin
    "operation": Build_Railroad,  # the actual function to call when running the plugin
}