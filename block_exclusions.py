# Block Exclusion Lists for Amulet Plugins
# Shared module for vegetation, liquid, and other non-solid block identification.
# Used by: rail_placer, light placers, and future plugins.
#
# (c) 2024 Black Forest Creations
# Blame: @lNQUlSlTlON

"""
Centralized block exclusion constants and helper functions.

Block IDs use the universal_minecraft namespace format used by Amulet's
internal block representation (e.g., 'universal_minecraft:short_grass').

Usage:
    from block_exclusions import VEGETATION_BLOCKS, WATER_STATES, LAVA_STATES, is_passthrough

    # Check if a block should be treated as "air" during depth scans:
    if is_passthrough(test_block.blockstate):
        air_depth += 1

    # Check if a block is liquid:
    if is_liquid(test_block.blockstate):
        water_depth += 1
"""


# =============================================================================
# VEGETATION BLOCKS - Non-solid blocks that should be treated as air/passthrough
# =============================================================================
# These blocks do not provide structural support and should not stop depth scans.
# Format: base block name (without namespace prefix or block states)

_VEGETATION_NAMES = {
    # ==========================================================================
    # Amulet universal format uses consolidated block names with properties.
    # E.g., all flowers/grass/ferns are "plant" with plant_type="grass", etc.
    # All leaves are "leaves" with material="oak", etc.
    # ==========================================================================

    # Consolidated vegetation blocks (cover many Minecraft blocks each)
    'plant',            # All flowers, grass, fern, dead bush (via plant_type property)
    'double_plant',     # Sunflower, lilac, rose bush, peony, tall grass, large fern
    'leaves',           # All leaf types: oak, spruce, birch, jungle, acacia, dark_oak, etc.
    'sapling',          # All sapling types: oak, spruce, birch, jungle, acacia, dark_oak, etc.

    # Crops
    'wheat',
    'carrots',
    'potatoes',
    'beetroots',
    'melon_stem',
    'pumpkin_stem',
    'sweet_berry_bush',
    'cave_vines',
    'cave_vines_body',
    'cave_vines_head',
    'nether_wart',
    'cocoa',
    'torchflower',
    'pitcher_plant',
    'pitcher_crop',

    # Vines
    'vine',
    'twisting_vines',
    'twisting_vines_plant',
    'weeping_vines',
    'weeping_vines_plant',
    'glow_lichen',

    # Mushrooms
    'brown_mushroom',
    'red_mushroom',
    'crimson_fungus',
    'warped_fungus',

    # Coral (individual names in universal format)
    'tube_coral',
    'brain_coral',
    'bubble_coral',
    'fire_coral',
    'horn_coral',
    'dead_tube_coral',
    'dead_brain_coral',
    'dead_bubble_coral',
    'dead_fire_coral',
    'dead_horn_coral',
    'tube_coral_fan',
    'brain_coral_fan',
    'bubble_coral_fan',
    'fire_coral_fan',
    'horn_coral_fan',

    # Aquatic plants
    'seagrass',
    'tall_seagrass',
    'kelp',
    'kelp_plant',
    'lily_pad',
    'small_dripleaf',
    'big_dripleaf',
    'big_dripleaf_stem',
    'spore_blossom',

    # Other vegetation / non-structural
    'bamboo',
    'bamboo_sapling',
    'sugar_cane',
    'cactus',
    'moss_carpet',
    'hanging_roots',
    'sculk_vein',
    'mangrove_roots',
    'mangrove_propagule',
    'azalea',
    'flowering_azalea',

    # Snow layer (not vegetation but non-structural)
    'snow',             # Amulet universal name for snow layer
    'snow_layer',       # Alternate name, kept for safety
}

# Build the full set with universal_minecraft: prefix for fast membership testing
VEGETATION_BLOCKS = frozenset(f'universal_minecraft:{name}' for name in _VEGETATION_NAMES)


# =============================================================================
# LIQUID STATES - Water and lava with all flowing/level variants
# =============================================================================

WATER_STATES = frozenset(
    f'universal_minecraft:water[falling=false,flowing=false,level={i}]' for i in range(16)
)

# Include the static water state that light placers check separately
WATER_STATES_ALL = WATER_STATES | frozenset({
    'universal_minecraft:water[falling=true,flowing=false,level=1]',
})

LAVA_STATES_TRUE = frozenset(
    f'universal_minecraft:lava[falling=true,flowing=false,level={i}]' for i in range(7)
)

LAVA_STATES_FALSE = frozenset(
    f'universal_minecraft:lava[falling=false,flowing=false,level={i}]' for i in range(7)
)

LAVA_STATES = LAVA_STATES_TRUE | LAVA_STATES_FALSE


# =============================================================================
# OTHER NON-SOLID BLOCKS
# =============================================================================

GRAVEL = 'universal_minecraft:gravel'
AIR = 'universal_minecraft:air'

# Existing light fixtures — don't stack lights on top of lights
LANTERN_STATES = frozenset({
    'universal_minecraft:lantern[hanging=true]',
    'universal_minecraft:lantern[hanging=false]',
})

TORCH_STATES = frozenset({
    'universal_minecraft:torch[facing=south]',
    'universal_minecraft:torch[facing=north]',
    'universal_minecraft:torch[facing=east]',
    'universal_minecraft:torch[facing=west]',
    'universal_minecraft:torch[facing=up]',
})

LIGHT_FIXTURES = LANTERN_STATES | TORCH_STATES


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_block_name(blockstate):
    """Extract the base block name from a blockstate string.

    'universal_minecraft:plant[plant_type="grass"]' -> 'universal_minecraft:plant'
    'universal_minecraft:air' -> 'universal_minecraft:air'
    """
    bracket = blockstate.find('[')
    if bracket != -1:
        return blockstate[:bracket]
    return blockstate


def is_vegetation(blockstate):
    """Return True if the blockstate is a vegetation/non-structural block.

    Strips block state properties before checking, so
    'universal_minecraft:short_grass[age=0]' matches 'universal_minecraft:short_grass'.
    """
    return _extract_block_name(blockstate) in VEGETATION_BLOCKS


def is_liquid(blockstate):
    """Return True if the blockstate is water or lava (any variant)."""
    return blockstate in WATER_STATES_ALL or blockstate in LAVA_STATES


def is_water(blockstate):
    """Return True if the blockstate is any water variant."""
    return blockstate in WATER_STATES_ALL


def is_lava(blockstate):
    """Return True if the blockstate is any lava variant."""
    return blockstate in LAVA_STATES


def is_passthrough(blockstate):
    """Return True if the block should be treated as air during depth scans.

    This includes actual air AND vegetation/non-structural blocks.
    Used by rail placer cribbing depth calculations to scan through
    flowers, grass, and other minor terrain elements.
    """
    return blockstate == AIR or is_vegetation(blockstate)


def is_non_solid(blockstate):
    """Return True if the block is not structurally solid.

    Includes air, vegetation, and liquids. Used by light placers
    to determine if a block is unsuitable for attachment.
    """
    return blockstate == AIR or is_vegetation(blockstate) or is_liquid(blockstate)


def is_light_fixture(blockstate):
    """Return True if the blockstate is an existing lantern or torch.

    Uses block name matching (strips properties) to handle any property
    encoding format from Amulet's universal representation.
    """
    name = _extract_block_name(blockstate)
    return name == 'universal_minecraft:lantern' or name == 'universal_minecraft:torch'


def is_solid_for_lantern(blockstate):
    """Return True if the block is suitable for attaching a lantern to.

    Excludes air, vegetation, liquids, AND existing light fixtures.
    Prevents lanterns from stacking on lanterns or attaching to torches.
    """
    return not is_non_solid(blockstate) and not is_light_fixture(blockstate)
