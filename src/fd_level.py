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

point_size = 20

level_surface = pg.Surface((level_size[0] * point_size, level_size[1] * point_size))
level_surface_damaged = []

# 0 - fully in fog
# 1 to 6 - out of fog
level_fow = [] # pg.Surface((level_size[0] * point_size, level_size[1] * point_size))

empty_visibility_blockage = 2
filled_visibility_blockage = 4

# 0 - unreachable
# 1 - reachable
#
# checks if point is reachable from base
# is si nesessary because A* can't (in reasonable amount of time) determine if end point is disconected from the navgrid 
level_navgrid = []

def init_level():
    level.clear()

    for i in range(level_size[1]):
        collum = []
        level.append(collum)

        collum_fow = []
        level_fow.append(collum_fow)

        collum_nav = []
        level_navgrid.append(collum_nav)

        for j in range(level_size[0]):
            collum.append(0)
            collum_fow.append(0) # max fog
            collum_nav.append(0)

# level

def get_pixel(pos):
    return level[pos[0]][pos[1]]

# note: do not hold on to the level buffer reference for more than a frame (could cause missed writes)
def get_level_buffer():
    return level

def set_pixel(pos, val):
    global level_surface_damaged
    level_surface_damaged.append(pos)
    level[pos[0]][pos[1]] = val

# fow

def get_pixel_fow(pos):
    return level_fow[pos[0]][pos[1]]

def get_level_buffer_fow():
    return level

def set_pixel_fow(pos, val):
    global level_surface_damaged
    level_surface_damaged.append(pos)
    level_fow[pos[0]][pos[1]] = val

# navgrid

def get_pixel_navgrid(pos):
    return level_navgrid[pos[0]][pos[1]]

def get_level_buffer_navgrid():
    return level

def set_pixel_navgrid(pos, val):
    global level_surface_damaged
    level_surface_damaged.append(pos)
    level_navgrid[pos[0]][pos[1]] = val

# generation

def inbounds(pos):
    return (clamp(pos[0], 0, level_size[0] - 1), clamp(pos[1], 0, level_size[1] - 1))

def random_fill(seed, fill_percent):
    random.seed(seed)

    for x, collum in enumerate(level):
        for y, point in enumerate(collum):
            val = random.randint(0, 100)

            set_pixel((x, y), 1 if val < fill_percent else 0)

def smooth_level():
    for x, collum in enumerate(level):
        for y, point in enumerate(collum):
            # count surrounding filled points
            count = 0

            for _x in range(-1, 3):
                for _y in range(-1, 3):
                    count += 1 if get_pixel(inbounds((_x + x, _y + y))) == 1 else 0

            # smooth by "average"
            if count > 6:
                set_pixel((x, y), 1)
            elif count < 4:
                set_pixel((x, y), 0)

def gen_level(seed, fill_percent):
    init_level()

    # generate level structure

    random_fill(seed, fill_percent)

    for i in range(7):
        smooth_level()

    # generate deposits

# checks if the navpoint would be in a wall or in fog    
def is_valid_navpoint(p):    
    valid = True if get_pixel(p) == 0 else False
    valid &= True if get_pixel_fow(p) != 0 else False

    return valid

# incremental fow and navmesh flood fill (hot func; must be pretty fast)    
def unfog_area(points, visibility_strenght):
    # fow

    for p in points:
        set_pixel_fow(p, visibility_strenght)

    to_check = points

    touched_points = points.copy()

    while True:
        new_to_check = []

        for p in to_check:
            #if get_pixel_fow(p) <= 0:
            #    set_pixel_fow(p, 0)
            #    continue
            
            p1 = inbounds((p[0], p[1] + 1))

            v = get_pixel_fow(p) - (empty_visibility_blockage if get_pixel(p1) == 0 else filled_visibility_blockage)
            if get_pixel_fow(p1) < v:
                new_to_check.append(p1)
                touched_points.append(p1)
                set_pixel_fow(p1, v)

            p2 = inbounds((p[0], p[1] - 1))

            v = get_pixel_fow(p) - (empty_visibility_blockage if get_pixel(p2) == 0 else filled_visibility_blockage)
            if get_pixel_fow(p2) < v:
                new_to_check.append(p2)
                touched_points.append(p2)
                set_pixel_fow(p2, v)

            p3 = inbounds((p[0] + 1, p[1]))

            v = get_pixel_fow(p) - (empty_visibility_blockage if get_pixel(p3) == 0 else filled_visibility_blockage)
            if get_pixel_fow(p3) < v:
                new_to_check.append(p3)
                touched_points.append(p3)
                set_pixel_fow(p3, v)

            p4 = inbounds((p[0] - 1, p[1]))

            v = get_pixel_fow(p) - (empty_visibility_blockage if get_pixel(p4) == 0 else filled_visibility_blockage)
            if get_pixel_fow(p4) < v:
                new_to_check.append(p4)
                touched_points.append(p4)
                set_pixel_fow(p4, v)

        if len(new_to_check) == 0:
            break
            
        to_check = new_to_check

    # navgrid

    edge_points = []

    # finds all points *next* to a reachable point

    for p in touched_points:
        if get_pixel_navgrid(p) == 0:
            continue # flooding *only* from reachable navpoints

        if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0], p[1] + 1))) == 0:
            edge_points.append(inbounds((p[0], p[1] + 1)))
            set_pixel_navgrid(inbounds((p[0], p[1] + 1)), 1)

        if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0], p[1] - 1))) == 0:
            edge_points.append(inbounds((p[0], p[1] - 1)))
            set_pixel_navgrid(inbounds((p[0], p[1] - 1)), 1)

        if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0] + 1, p[1]))) == 0:
            edge_points.append(inbounds((p[0] + 1, p[1])))
            set_pixel_navgrid(inbounds((p[0] + 1, p[1])), 1)

        if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0] - 1, p[1]))) == 0:
            edge_points.append(inbounds((p[0] - 1, p[1])))
            set_pixel_navgrid(inbounds((p[0] - 1, p[1])), 1)

    # flood fill from edge_points
            
    to_check = edge_points

    while True:
        new_to_check = []

        for p in to_check:
            if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0], p[1] + 1))) == 0:
                new_to_check.append(inbounds((p[0], p[1] + 1)))
                set_pixel_navgrid(inbounds((p[0], p[1] + 1)), 1)

            if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0], p[1] - 1))) == 0:
                new_to_check.append(inbounds((p[0], p[1] - 1)))
                set_pixel_navgrid(inbounds((p[0], p[1] - 1)), 1)

            if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0] + 1, p[1]))) == 0:
                new_to_check.append(inbounds((p[0] + 1, p[1])))
                set_pixel_navgrid(inbounds((p[0] + 1, p[1])), 1)

            if is_valid_navpoint(p) and get_pixel_navgrid(inbounds((p[0] - 1, p[1]))) == 0:
                new_to_check.append(inbounds((p[0] - 1, p[1])))
                set_pixel_navgrid(inbounds((p[0] - 1, p[1])), 1)

        if len(new_to_check) == 0:
            break

        to_check = new_to_check

color_lib = [
    (102, 255, 255),
    (255, 0, 0),
    (128, 255, 0),
    (127, 0, 255),
    (255, 128, 0)
]

def pre_render_level():
    global level_surface_damaged

    # level_surface.fill((16, 16, 16))

    for p in level_surface_damaged:
        x, y = p
        val = get_pixel(p)

        if level_fow[x][y]:
            pg.draw.rect(level_surface, color_lib[2 % 5], (x * point_size, y * point_size, point_size, point_size))

        if val == 1:
            pg.draw.rect(level_surface, (200, 200, 200), (x * point_size, y * point_size, point_size, point_size))
        elif level_navgrid[x][y] == 1:
            pg.draw.rect(level_surface, color_lib[0], (x * point_size, y * point_size, point_size, point_size))

    level_surface_damaged.clear()

def render_level(sur):
    # causes hitching on every pixel change but its good enough
    if not len(level_surface_damaged) == 0:
        pre_render_level()

    sur.blit(level_surface, cam.translate((0, 0), level_surface.get_size()))