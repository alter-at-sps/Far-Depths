import random
import pygame as pg
from pygame.math import clamp

import src.fd_camera as cam

# == Far Depths Level Storage, Generator and Pathfinder ==

# storage

# 0 - empty
# positive values - filled (by material type)

level = []
level_size = (250, 250)

level_surface = pg.Surface((level_size[0] * 20, level_size[1] * 20))
level_surface_damaged = True

# 0 - out of fog
# 1 to 6 - in fog

level_fow = []

def init_level():
    level.clear()

    for i in range(level_size[1]):
        collum = []
        level.append(collum)

        collum_fow = []
        level_fow.append(collum_fow)

        for j in range(level_size[0]):
            collum.append(0)
            collum_fow.append(6) # max fog

def get_pixel(pos):
    return level[pos[0]][pos[1]]

# note: do not hold on to the level buffer reference for more than a frame (could cause missed writes)
def get_level_buffer():
    global level_surface_damaged
    level_surface_damaged = True
    return level

def set_pixel(pos, val):
    global level_surface_damaged
    level_surface_damaged = True
    level[pos[0]][pos[1]] = val

# generation

def inbounds(pos):
    return (clamp(pos[0], 0, level_size[0] - 1), clamp(pos[1], 0, level_size[1] - 1))

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

    # generate deposits


color_lib = [
    (102, 255, 255),
    (255, 0, 0),
    (128, 255, 0),
    (127, 0, 255),
    (255, 128, 0)
]

def pre_render_level():
    global level_surface_damaged

    level_surface.fill((16, 16, 16))

    for y, collum in enumerate(level):
        for x, point in enumerate(collum):
            if point < 0:
                pg.draw.rect(level_surface, (200, 200, 200), (x * 20, y * 20, 20, 20))
            elif point > 0:
                pg.draw.rect(level_surface, color_lib[point % 5], (x * 20, y * 20, 20, 20))

    level_surface_damaged = False

def render_level(sur):
    # causes hitching on every pixel change but its good enough
    if level_surface_damaged:
        pre_render_level()

    sur.blit(level_surface, cam.translate((0, 0), level_surface.get_size()))