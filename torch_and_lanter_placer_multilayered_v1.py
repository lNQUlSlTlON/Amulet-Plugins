import os
import json
import numpy as np
import wx

from typing import TYPE_CHECKING
from amulet.api.selection import SelectionBox, SelectionGroup
from amulet.api.data_types import Dimension
from amulet.api.block import Block
from amulet_map_editor.programs.edit.api.operations import DefaultOperationUI
from amulet_nbt import StringTag, IntTag, ByteTag

if TYPE_CHECKING:
    from amulet.api.level import BaseLevel
    from amulet_map_editor.programs.edit.api.canvas import EditCanvas

class TorchFound(Exception):
    pass

class Detect_Edges(wx.Panel, DefaultOperationUI):
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

        dropdown1_label = wx.StaticText(self, label="LIghting Choice:")
        self._sizer.Add(dropdown1_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Create a list of choices for the dropdown
        choices = ["both", "torch", "lantern"]

        # Add a Choice control for the dropdown
        self._dropdown = wx.Choice(self, choices=choices)
        self._sizer.Add(self._dropdown, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)
        # Set "torch" as the default selection
        self._dropdown.SetSelection(0)

        dropdown2_label = wx.StaticText(self, label="Detection Radius:")
        self._sizer.Add(dropdown2_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Add a SpinCtrl for the detection radius
        self._detect_radius = wx.SpinCtrl(self, min=0, max=14, initial=6)
        self._sizer.Add(self._detect_radius, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        dropdown3_label = wx.StaticText(self, label="Lowest Y Layer:")
        self._sizer.Add(dropdown3_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Add a SpinCtrl for the Minimum Y value
        self._min_y = wx.SpinCtrl(self, min=-56, max=255, initial=0)
        self._sizer.Add(self._min_y, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        dropdown4_label = wx.StaticText(self, label="Highest Y Layer:")
        self._sizer.Add(dropdown4_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)        

        # Add a SpinCtrl for the Maximum Y value
        self._max_y = wx.SpinCtrl(self, min=-55, max=256, initial=256)
        self._sizer.Add(self._max_y, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        dropdown5_label = wx.StaticText(self, label="Height Between Lighting Layers:")
        self._sizer.Add(dropdown5_label, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        # Add a SpinCtrl for the step value between layers
        self._step = wx.SpinCtrl(self, min=1, max=15, initial=1)
        self._sizer.Add(self._step, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)                

        self._run_button = wx.Button(self, label="Run Operation")
        self._run_button.Bind(wx.EVT_BUTTON, self._run_operation)
        self._sizer.Add(self._run_button, 0, wx.ALL | wx.ALIGN_CENTRE_HORIZONTAL, 5)

        self.Layout()
        self.Thaw()

    def _run_operation(self, _):
        selection_group = self.canvas.selection.selection_group
        world = self.canvas.world  # get the world object
        dimension = self.canvas.dimension
        block_choice = self._dropdown.GetStringSelection() # get the block choice from the dropdown
        detect_radius = self._detect_radius.GetValue()  # get the number of iterations from the SpinCtrl
        min_y = self._min_y.GetValue()  # get the minimum Y value from the SpinCtrl
        max_y = self._max_y.GetValue()  # get the maximum Y value from the SpinCtrl
        step = self._step.GetValue()  # get the step value from the SpinCtrl
        ## Debug print statement for the coordinates
        # print(coordinates)
        # print("Min Y:", min_y, "Max Y:", max_y, "Step:", step)


        def operation():
            # Build a dictionary of Y Values based to iterate over, based on the min and max Y values and the step value
            y_values = []
            for y in range(min_y, max_y, step):
                y_values.append(y)
            ## Debug print statement for the y_values
            # print(y_values)

            # Iterate over the Y values and run the operation for each one
            for y in y_values:
                current_y = int(y)  # Convert to int for compatibility with the world.get_block method
                coordinates = self.read_selection(self.world, self.canvas.dimension, selection_group, current_y)
                ## Debug print statement for the coordinates at the current Y level
                # print(coordinates)
                lighting_coordinates = self.detect_edges(coordinates, block_choice, detect_radius, self.world, self.canvas.dimension)
                ## Debug print statement for the lighting_coordinates at the current Y level
                #print(f"Lighting coordinates at Y={current_y}: {lighting_coordinates}")

        # Add the operation to the operation manager
        self.canvas.run_operation(operation)

        print("Operation completed successfully.")            

    @staticmethod
    def read_selection(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup, current_y):
        current_y = int(current_y)  # Convert to int for compatibility with the world.get_block method
        ## Modify the "y" value to the current "y" value in the loop of the Operation by passing it to the get_coordinates method     
        coordinates = Detect_Edges.get_coordinates(world, dimension, selection, current_y)


        # Write the coordinates to a JSON file
        file_path = os.path.join(os.getcwd(), 'selection_to_array.json')
        with open(file_path, 'w') as f:
            json.dump({'coordinates': coordinates}, f)

        return(coordinates)
        ## Print the coordinates to the console for a sanity check
        # print(coordinates)

    @staticmethod
    def get_coordinates(world: "BaseLevel", dimension: Dimension, selection: SelectionGroup, current_y):
        coordinates = []
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version

        # Iterate over each coordinate in the selection box
        for box in selection.selection_boxes:
            for x in range(box.min[0], box.max[0]):
                for y in range(box.min[1], box.max[1]):
                    for z in range(box.min[2], box.max[2]):
                        # Check if the coordinate is within the selection box in X and Z, using the current Y value
                        block = world.get_block(x, current_y, z, dimension)  # get the existing block at the coordinate

                        if block.blockstate == 'universal_minecraft:air':
                            value = 0
                        else:
                            value = 1
                        # Append the coordinate and value to the list
                        coordinates.append({'x': x, 'y': current_y, 'z': z, 'value': value})
        return coordinates

    @staticmethod
    def detect_edges(coordinates, block_choice, detect_radius, world, dimension):
        # Confirm block choice has been passed from the UX Panel
        # print(block_choice)

        # Step 1.5: Convert the 'x', 'y', 'z', and 'value' fields to integers
        for item in coordinates:
            item['x'] = int(item['x'])
            item['y'] = int(item['y'])
            item['z'] = int(item['z'])
            item['value'] = int(item['value'])

        # Step 2: Determine the size of the array based on the data
        min_x = min(item['x'] for item in coordinates)
        min_z = min(item['z'] for item in coordinates)
        max_x = max(item['x'] for item in coordinates)
        max_z = max(item['z'] for item in coordinates)
        y = min(item['y'] for item in coordinates)

        ## Debug print statements for the min and max values
        # print('min_x:', min_x)
        # print('min_z:', min_z)
        # print('max_x:', max_x)
        # print('max_z:', max_z)
        #print('y:', y)

        # print('Min:', min_x, min_z, 'Max:', max_x, max_z, 'y:', y, '\n')

        # Adjust the size of the array based on the minimum values
        array_size_x = max_x - min_x + 1
        array_size_z = max_z - min_z + 1

        array = np.zeros((array_size_x, array_size_z))
        #print('\n', array, '\n')

        # Step 2.5: Convert the dictionary into a 2D numpy array
        for item in coordinates:
            value_x = item['x'] - min_x
            value_z = item['z'] - min_z
            # value = item['value']
            array[value_x][value_z] = item['value']
        
        #print(array)

        # # Step 2.5: Visualize the input array and save it as a .png file
        # plt.imshow(array, cmap='gray_r', interpolation='none')  # Use the 'gray_r' color map to make 1s grey and 0s white
        # plt.savefig('array.png')

        # Step 4: Initialize a new 2D list for storing edge information
        edge_array = [[(False, None, None, None, None) for _ in range(array_size_z)] for _ in range(array_size_x)]


        #print(edge_array)

        # Step 5: Iterate over the array in both X and Y directions
        for i in range(array.shape[0] - 1):  # Subtract 1 here
            for j in range(array.shape[1] - 1):  # And here
                # Check neighbors in X direction
                if (array[i][j] == 0 and array[i+1][j] == 1):
                    edge_array[i][j] = (True, "east", "x", "+", "1")
                if (array[i][j] == 1 and array[i+1][j] == 0):
                    edge_array[i+1][j] = (True, "west", "x", "-", "1")    
                # Check neighbors in Y direction
                if (array[i][j] == 1 and array[i][j+1] == 0):  # Change j-1 to j+1 here
                    edge_array[i][j+1] = (True, "north", "z", "-", "1")
                if (array[i][j] == 0 and array[i][j+1] == 1):  # And here
                    edge_array[i][j] = (True, "south", "z", "+", "1")

        #print(edge_array)

        # Step 6: Convert the edge array back into a dictionary format
        edge_data = []
        for i in range(array.shape[0]):
            for j in range(array.shape[1]):
                edge_value, edge_direction, edge_axis, edge_operator, edge_offset = edge_array[i][j]  # Unpack the tuple here
                if edge_value:  # Check if edge_value is True before appending
                    edge_data.append({
                        'x': str(i),
                        'z': str(j),
                        'value': str(edge_value),
                        'edge': edge_direction.lower(),  # Use the edge_direction variable here
                        'axis': edge_axis,
                        'operator': edge_operator,
                        'offset': edge_offset
                    })

        # Step 7: Write the dictionary back into a new JSON file
        file_path = os.path.join(os.getcwd(), 'edges_detected.json')
        with open(file_path, 'w') as f:
            json.dump(edge_data, f)

        # Step 8: Create an array with the center being the coordinates of the "True" blocks
        true_blocks = []
        for i in range(array.shape[0]):
            for j in range(array.shape[1]):
                if edge_array[i][j][0]:
                    edge = edge_array[i][j][1]
                    axis = edge_array[i][j][2]
                    operator = edge_array[i][j][3]
                    offset = edge_array[i][j][4]
                    true_blocks.append((i + min_x, y, j + min_z, edge, axis, operator, offset))

        # Debug print statement for the true_blocks dictionary
        # print(true_blocks)

        # Step 9: Create a 15x15 numpy array centered around each true_block
        platform, version_number = world.level_wrapper.platform, world.level_wrapper.version
        block_logging = []
        # Declare a counter variable for the number of lights placed
        torch_placement_count = 0        
        for block in true_blocks:
            place_torch = True
            torch_block = Block('minecraft', 'torch', {"torch_facing_direction": StringTag(block[3])})
            lantern_block_standing = Block('minecraft', 'lantern', {"hanging": ByteTag(0)})
            lantern_block_hanging = Block('minecraft', 'lantern', {"hanging": ByteTag(1)})
            block_x = block[0]
            block_y = block[1]
            block_z = block[2]
            facing = block[3]
            axis = block[4]
            operator = block[5]
            offset = int(block[6])
            array_size_x = detect_radius * 2 + 1
            array_size_z = detect_radius * 2 + 1
            torch_array = []
            torch_array = np.zeros((array_size_x, array_size_z), dtype=tuple)
            

            ## Test that the array is being built correctly
            # print(torch_array)
            # print('\n', '\n')

            # Step 9.5: Populate the array with coordinates with the "block" at the center
            for i in range(array_size_x):
                for j in range(array_size_z):
                    torch_array[i][j] = (block_x - detect_radius + i, block_y, block_z - detect_radius + j)
                    ## Test that the coorindates are populating the array correctly
                    #print(torch_array)
            
            try:
                for i in range(array_size_x):
                    for j in range(array_size_z):
                        coordinate = torch_array[i][j]
                        if isinstance(coordinate, tuple) and len(coordinate) > 0:
                            tested_block_x, tested_block_y, tested_block_z = coordinate
                            block = world.get_block(tested_block_x, block_y, tested_block_z, dimension)  # get the block at the coordinate
                        if block is not None:
                            # print(block.blockstate)  # Debug print statement
                            lava_states_true = [f'universal_minecraft:lava[falling=true,flowing=false,level={i}]' for i in range(7)]
                            lava_states_false = [f'universal_minecraft:lava[falling=false,flowing=false,level={i}]' for i in range(7)]    
                            if block.blockstate in lava_states_true or block.blockstate in lava_states_false or block.blockstate == 'universal_minecraft:torch[facing=south]' or block.blockstate == 'universal_minecraft:torch[facing=north]' or block.blockstate == 'universal_minecraft:torch[facing=east]' or block.blockstate == 'universal_minecraft:torch[facing=west]' or block.blockstate == 'universal_minecraft:torch[facing=up]':
                                place_torch = False
                                ## Debug "torch found" test
                                # print("Torch found at", coordinate)
                                ## Enable logging for "torch found" martices
                                # block_logging.append({'status': 'torch_found', 'x': tested_block_x, 'y': tested_block_y, 'z': tested_block_z, 'blockstate': block.blockstate})
                                raise TorchFound
                            elif block.blockstate == 'universal_minecraft:lantern[hanging=true]' or block.blockstate == 'universal_minecraft:lantern[hanging=false]':
                                place_torch = False
                                ## Debug "lantern found" test
                                # print("Lantern found at", coordinate)
                                ## Enable logging for "torch found" martices                                
                                # block_logging.append({'status': 'lantern_found', 'x': tested_block_x, 'y': tested_block_y, 'z': tested_block_z, 'blockstate': block.blockstate})
                                raise TorchFound
            except TorchFound:
                pass
            ## Debug print statement for the place_torch variable
            # print(place_torch)

            if place_torch:
                ## Debug print statement for the lighitng test = pass
                # print("Place lighting test passed at", block_x, block_y, block_z, facing, "-- test coords for same Y level", axis, operator, offset)
                if block_choice == "lantern":
                    # Declare all of the water and lava states as variables
                    water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
                    lava_states_true = [f'universal_minecraft:lava[falling=true,flowing=false,level={i}]' for i in range(7)]
                    lava_states_false = [f'universal_minecraft:lava[falling=false,flowing=false,level={i}]' for i in range(7)]  
                    # Lanterns should not be suspended in mid-air, so we need to check for air blocks above and below the block
                    air_test_up = world.get_block(block_x, block_y + 1, block_z, dimension)
                    air_test_down = world.get_block(block_x, block_y - 1, block_z, dimension)
                    # If there is a block above, place a hanging lantern.  
                    if air_test_up.blockstate != 'universal_minecraft:air':
                        world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), lantern_block_hanging, None)
                        # Increment the counter variable
                        torch_placement_count += 1
                        # Write the block placement to the block_logging dictionary                        
                        block_logging.append({'status': 'lantern placed', 'x':block_x, 'y': block_y, 'z': block_z, 'blockstate': 'hanging', 'count': torch_placement_count})

                    # If there is a block below, place a standing lantern.
                    elif air_test_down.blockstate != 'universal_minecraft:air' and not air_test_down.blockstate in water_states and not air_test_down.blockstate in lava_states_true and not air_test_down.blockstate in lava_states_false:
                        world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), lantern_block_standing, None)
                        # Increment the counter variable
                        torch_placement_count += 1
                        # Write the block placement to the block_logging dictionary                        
                        block_logging.append({'status': 'lantern placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': 'standing', 'count': torch_placement_count})
                    # If there is no block above or below, place nothing.
                    else:
                        ## Debug print statement for the lantern placement test
                        # print("No block above or below.  Skipping.")
                        continue        
                if block_choice == "torch":
                    # Declare all of the water and lava states as variables
                    water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
                    lava_states_true = [f'universal_minecraft:lava[falling=true,flowing=false,level={i}]' for i in range(7)]
                    lava_states_false = [f'universal_minecraft:lava[falling=false,flowing=false,level={i}]' for i in range(7)]                  
                    # Torches should not be placed on water, so we need to check for water blocks in the X and Z directions
                    if axis == "x" and operator == "+":
                        state_test = world.get_block(block_x + 1, block_y, block_z, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})

                    elif axis == "x" and operator == "-":
                        state_test = world.get_block(block_x - 1, block_y, block_z, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
                    elif axis == "z" and operator == "+":
                        state_test = world.get_block(block_x, block_y, block_z + 1, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
                    elif axis == "z" and operator == "-":
                        state_test = world.get_block(block_x, block_y, block_z - 1, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
    
                if block_choice == "both":
                    air_test_up = world.get_block(block_x, block_y + 1, block_z, dimension)
                    air_test_down = world.get_block(block_x, block_y - 1, block_z, dimension)
                    # Declare all of the water and lava states as variables
                    water_states = [f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)]
                    lava_states_true = [f'universal_minecraft:lava[falling=true,flowing=false,level={i}]' for i in range(7)]
                    lava_states_false = [f'universal_minecraft:lava[falling=false,flowing=false,level={i}]' for i in range(7)]
                    # If there is a block above, place a hanging lantern.  
                    if air_test_up.blockstate != 'universal_minecraft:air':
                        world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), lantern_block_hanging, None)
                        # Increment the counter variable
                        torch_placement_count += 1
                        # Write the block placement to the block_logging dictionary                        
                        block_logging.append({'status': 'lantern placed', 'x':block_x, 'y': block_y, 'z': block_z, 'blockstate': 'hanging', 'count': torch_placement_count})

                    # If there is a block below, place a standing lantern.
                    elif air_test_down.blockstate != 'universal_minecraft:air' and not air_test_down.blockstate in water_states and not air_test_down.blockstate in lava_states_true and not air_test_down.blockstate in lava_states_false:
                        world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), lantern_block_standing, None)
                        # Increment the counter variable
                        torch_placement_count += 1
                        # Write the block placement to the block_logging dictionary                        
                        block_logging.append({'status': 'lantern placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': 'standing', 'count': torch_placement_count})
                    # Torches should not be placed on water, so we need to check for water blocks in the X and Z directions
                    elif axis == "x" and operator == "+":
                        state_test = world.get_block(block_x + 1, block_y, block_z, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
                    elif axis == "x" and operator == "-":
                        state_test = world.get_block(block_x - 1, block_y, block_z, dimension)
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
                    elif axis == "z" and operator == "+":
                        state_test = world.get_block(block_x, block_y, block_z + 1, dimension)                      
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})
                    elif axis == "z" and operator == "-":
                        state_test = world.get_block(block_x, block_y, block_z - 1, dimension)                       
                        if state_test.blockstate in lava_states_true or state_test.blockstate in lava_states_false or state_test.blockstate in water_states or state_test.blockstate == 'universal_minecraft:water[falling=true,flowing=false,level=1]' or state_test.blockstate == 'universal_minecraft:gravel':
                            ## Debug print statement for the lava, water, or gravel test
                            # print("Found lava, water or gravel.  Skipping")
                            continue
                        else:    
                            ## Debug print statement for the torch placement
                            # print("Place torch at", block_x, block_y, block_z, facing)
                            world.set_version_block(block_x, block_y, block_z, dimension, (platform, version_number), torch_block, None)
                            # Increment the counter variable
                            torch_placement_count += 1
                            # Write the block placement to the block_logging dictionary                        
                            block_logging.append({'status': 'torch placed', 'x': block_x, 'y': block_y, 'z': block_z, 'blockstate': facing, 'count': torch_placement_count})

        ## Debug print statement for the block_logging dictionary
        # print(block_logging)

        # It's always nice to log results to a file so...
        # Let's dump the block_logging dictionary to a JSON file
        file_path = os.path.join(os.getcwd(), 'torch_log.json')
        with open(file_path, 'w') as f:
            json.dump(block_logging, f, indent=4)

        print("Lighting pass complete.")




###
### Now we need to start reading the "true" edges and plopping torches and lanterns.
### 
###
### Done:
###
### // then... make it area based.  should only have one torch or lantern ever 6x6 blocks
### // read all blocks +/- 6 from block in X and Z.  If torch or lantern, pass.  Else, place.
### // if y + 1 = gravel, pass
### // if y + 1 = !air, lantern
### // if y + 1 = air and y - 1 != air, lantern
### // if y + 1 = air and y - 1 = air, torch
### // if y + 1 = air and y - 1 = anything else, lantern
### // test in +/- X or +/- Z for water or lava.  If found, no lighting
### // test in +/- Y for water or lava.  If found, no lighting
###
### and... if a single block is surrounded by air on all sides, place a torch on each side of the block
      

export = {
    "name": "Place Lights on Multiple Y Levels",  # the name of the plugin
    "operation": Detect_Edges,  # the actual function to call when running the plugin
}
