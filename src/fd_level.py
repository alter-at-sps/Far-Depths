import random
import pygame as pg
from pygame.math import clamp

import src.fd_camera as cam

# == Far Depths Level Storage, Generator and Pathfinder ==

# storage

# 0 - undefined
# negative values - filled (by material type)
# positive values - empty (room id)

level = []
level_size = (250, 250)

# contains room id to room mappings
#   used for checking if both point A and B are in the same room (multiple room ids can point to the same room) 
#   this is important as A* cannot check (in a resonable amount of time) if a path from point A to point B exists

room_dict = {}

def init_level():
    level.clear()

    for i in range(level_size[1]):
        collum = []
        level.append(collum)

        for j in range(level_size[0]):
            collum.append(0)

def get_pixel(pos):
    return level[pos[0]][pos[1]]

def get_level_buffer():
    return level

def set_pixel(pos, val):
    level[pos[0]][pos[1]] = val

# generation

def inbounds(pos):
    return (clamp(pos[0], 0, level_size[0] - 1), clamp(pos[1], 0, level_size[1] - 1))

next_room_id = 1
def flood_room(pos):
    global next_room_id

    room_id = next_room_id
    next_room_id += 1

    # by default each room id is a unique room (until they start merging at play time)
    room_dict[room_id] = room_id

    to_check = [ pos ]

    while True:
        new_to_check = []

        for p in to_check:
            if get_pixel(inbounds((p[0], p[1] + 1))) == 0:
                new_to_check.append(inbounds((p[0], p[1] + 1)))
                set_pixel(inbounds((p[0], p[1] + 1)), room_id)

            if get_pixel(inbounds((p[0], p[1] - 1))) == 0:
                new_to_check.append(inbounds((p[0], p[1] - 1)))
                set_pixel(inbounds((p[0], p[1] - 1)), room_id)

            if get_pixel(inbounds((p[0] + 1, p[1]))) == 0:
                new_to_check.append(inbounds((p[0] + 1, p[1])))
                set_pixel(inbounds((p[0] + 1, p[1])), room_id)

            if get_pixel(inbounds((p[0] - 1, p[1]))) == 0:
                new_to_check.append(inbounds((p[0] - 1, p[1])))
                set_pixel(inbounds((p[0] - 1, p[1])), room_id)

        if len(new_to_check) == 0:
            break

        to_check = new_to_check


# floods a newly generated level and precalculates in room ids (used for pathfinding)
def flood_fill_rooms():
    for x, collum in enumerate(level):
        for y, point in enumerate(collum):
            # 0 means empty but not room indexed yet
            
            if point == 0:
                flood_room((x, y))

def random_fill(seed, fill_percent):
    random.seed(seed)

    for x, collum in enumerate(level):
        for y, point in enumerate(collum):
            val = random.randint(0, 100)

            set_pixel((x, y), -1 if val < fill_percent else 0)

def smooth_level():
    for x, collum in enumerate(level):
        for y, point in enumerate(collum):
            # count surrounding filled points
            count = 0

            for _x in range(-1, 3):
                for _y in range(-1, 3):
                    count += 1 if get_pixel(inbounds((_x + x, _y + y))) == -1 else 0

            # smooth by "average"
            if count > 6:
                set_pixel((x, y), -1)
            elif count < 4:
                set_pixel((x, y), 0)

def gen_level(seed, fill_percent):
    init_level()

    # generate level structure

    random_fill(seed, fill_percent)

    for i in range(7):
        smooth_level()

    flood_fill_rooms()

    # generate deposits


color_lib = [
    (102, 255, 255),
    (255, 0, 0),
    (128, 255, 0),
    (127, 0, 255),
    (255, 128, 0)
]

def render_level(sur):
    for y, collum in enumerate(level):
        for x, point in enumerate(collum):
            if point < 0:
                pg.draw.rect(sur, (200, 200, 200), cam.translate((x * 20, y * 20), (20, 20)))
            elif point > 0:
                pg.draw.rect(sur, color_lib[point % 5], cam.translate((x * 20, y * 20), (20, 20)))