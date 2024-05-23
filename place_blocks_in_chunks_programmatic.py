import pyautogui as pt
import time
from time import sleep
import os
import json

# Wait 1 seconds to start the program
sleep(1)

def ResumeGame():
    pt.keyDown('alt')
    pt.keyDown('tab')
    sleep(.2)
    pt.keyUp('tab')
    pt.keyUp('alt')
    sleep(3)
    # pt.press('tab')
    # sleep(.5)
    # pt.press('left')
    # sleep(.2)
    # pt.press('up')
    # sleep(.2)
    # pt.press('up')
    # sleep(.2)
    # pt.press('up')
    # sleep(.2)
    # pt.press('enter')
    # sleep(2)

def teleport(x, y, z):
    pt.keyDown('/')
    pt.keyUp('/')
    sleep(2)
    pt.typewrite(f'tp {x} {y} {z}', interval=.2)
    pt.keyDown('enter')
    pt.keyUp('enter')
    sleep(1)

def teleport2(x, y, z):
    pt.keyDown('/')
    pt.keyUp('/')
    sleep(.5)
    pt.typewrite(f'tp {x} {y} {z}')
    pt.keyDown('enter')
    pt.keyUp('enter')
    sleep(1)

def set_block(block):
    pt.keyDown('/')
    pt.keyUp('/')
    sleep(.5)
    pt.typewrite(f'setblock ~ ~ ~ {block}')
    pt.keyDown('enter')
    pt.keyUp('enter')
    sleep(1)

def save_progress():
    pt.press('esc')
    sleep(1)
    pt.press('tab')
    sleep(.2)
    pt.press('left')
    sleep(.2)
    pt.press('enter')

# Tab over to Minecraft and resume the game
ResumeGame()

# Iterate over each object in the coordinate array
iter_count = 0

# Define the range and step

# xstart, xend, xstep = -16, 16, 16
# zstart, zend, zstep = -16, 16, 16

xstart, xend, xstep = 256, 512, 16
zstart, zend, zstep = -512, -256, 16

# Start the timer
start_time = time.time()

# Iterate over x and z from -1024 to 1024 in increments of 16
for x in range(xstart, xend + 1, xstep):
    for z in range(zstart, zend + 1, zstep):
        y = 260
        #print(f'x: {x}, y: 200, z: {z}')

        # Teleport to the coordinates
        if iter_count == 0:
            teleport(x, y, z)
            iter_count += 1
        else:
            teleport2(x, y, z)
            iter_count += 1
        # Calculate and print the elapsed time
        elapsed_time = time.time() - start_time
        print(f'Iteration: {iter_count}, Total Time: {elapsed_time} seconds')
        # Drop a block
        set_block('stone')

# Calculate and print the elapsed time
elapsed_time = time.time() - start_time
print(f'Total Iterations: {iter_count}, Final Time Elapsed: {elapsed_time} seconds')

# Save level and exit to level menu
save_progress()