import random
import time
import pygame as pg
from pygame.math import clamp

import src.fd_config as conf
import src.fd_camera as cam
import src.fd_entity as en

import src.fd_render as ren
import src.fd_render_lib as rlib

if conf.dev_fastmap:
    import pickle

# == Far Depths Level Storage and Generator ==

# storage

# 0 - empty
# 1 - stone
# 2 - oxy ore
# 3 - goal ore
# positive values - filled (by material type)

level = []

point_size = 20
mark_margin = 5

level_surface = pg.Surface((conf.level_size[0] * point_size, conf.level_size[1] * point_size))
level_fow_surface = pg.Surface((conf.level_size[0] * point_size, conf.level_size[1] * point_size), flags=pg.SRCALPHA)
level_surface_damaged = []

level_surface.fill(conf.empty_color)
level_fow_surface.fill(conf.fog_color)

# 0 - fully in fog
# 1 to 18 - out of fog
level_fow = []

empty_visibility_blockage = 2
filled_visibility_blockage = 4

# 0 - unreachable
# 1 - reachable
#
# checks if point is reachable from base
# is si nesessary because A* can't (in reasonable amount of time) determine if end point is disconected from the navgrid 
level_navgrid = []

# 0 - unmarked
# > 0 - maked by that number of units
# 
# overlay for player to see what blocks are marked for mining
level_mark = []

def init_level():
    level.clear()

    for i in range(conf.level_size[1]):
        collum = []
        level.append(collum)

        collum_fow = []
        level_fow.append(collum_fow)

        collum_nav = []
        level_navgrid.append(collum_nav)

        collum_mark = []
        level_mark.append(collum_mark)

        for j in range(conf.level_size[0]):
            collum.append(0)
            collum_fow.append(0) # max fog
            collum_nav.append(0)
            collum_mark.append(0)

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
    # global level_surface_damaged
    # level_surface_damaged.append(pos)
    level_navgrid[pos[0]][pos[1]] = val

# mark

def get_pixel_mark(pos):
    return level_mark[pos[0]][pos[1]]

def get_level_buffer_mark():
    return level

def set_pixel_mark(pos, val):
    global level_surface_damaged
    level_surface_damaged.append(pos)
    level_mark[pos[0]][pos[1]] = val

def offset_by_pixel_mark(pos, val):
    global level_surface_damaged
    level_surface_damaged.append(pos)
    level_mark[pos[0]][pos[1]] += val

# level utils

def set_circle(pos, radius_squared, val):
    for x in range(pos[0] - radius_squared, pos[1] + radius_squared):
        for y in range(pos[0] - radius_squared, pos[1] + radius_squared):
            if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 < radius_squared:
                set_pixel((x, y), val)

def world_to_grid_space(pos):
    return ((pos[0] + level_surface.get_width() // 2) // point_size, (pos[1] + level_surface.get_height() // 2) // point_size)

def grid_to_world_space(pos):
    return (pos[0] * point_size - level_surface.get_width() // 2, pos[1]  * point_size - level_surface.get_height() // 2)

# generation

def inbounds(pos):
    return (clamp(pos[0], 0, conf.level_size[0] - 1), clamp(pos[1], 0, conf.level_size[1] - 1))

def refresh_loading_status(loading_percent):
    en.get_entity("loading_status")["status_text"] = conf.loading_status_texts[int(len(conf.loading_status_texts) * loading_percent)] + f" ({int(loading_percent * 100)}%)"

last_frame_update = 0

# level generator "once in a while" call this function to draw a new frame of the loading screen and prevent windows thinking the app is frozen
def level_gen_yield():
    global last_frame_update

    if time.time() - last_frame_update < (1 / 7):
        return

    last_frame_update = time.time()

    # minimal event loop

    for e in pg.event.get():
            if e.type == pg.QUIT:
                quit()
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)
    
    ren.get_surface().fill(conf.ui_background_color)
    en.render_entities(ren.get_surface())
    ren.submit()

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

        level_gen_yield()

def gen_level(seed, fill_percent):
    init_level()

    if conf.dev_fastmap:
        try:
            file = open("dev_map.pickle", mode='br')

            print("loading dev map...")
            pregen_map = pickle.load(file)
            file.close()

            global level, level_fow, level_navgrid, level_surface, level_fow_surface
            level, level_fow, level_navgrid, level_surface, level_fow_surface = (*pregen_map[0:3], pg.image.fromstring(pregen_map[3], (conf.level_size[0] * point_size, conf.level_size[1] * point_size), 'RGB'), pg.image.fromstring(pregen_map[4], (conf.level_size[0] * point_size, conf.level_size[1] * point_size), 'RGBA'))

            del pregen_map
            return

        except OSError:
            pass

    global last_frame_update
    last_frame_update = time.time()

    # setup loading screen scene
    status = en.create_entity("loading_status", {
        "transform": [
            (0, 0),
            (480, 20)
        ],

        "on_frame": rlib.loading_status_renderer,

        # status components

        "status_text": None,
    })

    # generate level structure

    status["status_text"] = "> Undocking..."
    level_gen_yield()

    random_fill(seed, fill_percent)

    for i in range(7):
        refresh_loading_status(i * .5 / 7)

        smooth_level()

    # generate deposits

    # prevents a crash when generating deposits outside of the level
    min_deposit_border_margin = 35

    oxy_deposit_count = random.randint(*conf.num_of_oxy_deposits_min_max)
    
    for i in range(oxy_deposit_count):
        x = random.randint(min_deposit_border_margin, conf.level_size[0] - min_deposit_border_margin)
        y = random.randint(min_deposit_border_margin, conf.level_size[1] - min_deposit_border_margin)

        size = random.randint(*conf.oxy_deposit_size_min_max)

        set_circle((x, y), size ** 2, 2)

        level_gen_yield()

    goal_deposit_count = random.randint(*conf.num_of_goal_deposits_min_max)
    
    for i in range(goal_deposit_count):
        x = random.randint(min_deposit_border_margin, conf.level_size[0] - min_deposit_border_margin)
        y = random.randint(min_deposit_border_margin, conf.level_size[1] - min_deposit_border_margin)

        size = random.randint(*conf.goal_deposit_size_min_max)

        set_circle((x, y), size ** 2, 3)

        level_gen_yield()

    # pre render level
        
    # sets its status_text by its own
    pre_render_level(status)

    # clear loading screen scene

    en.reset()

    if conf.dev_fastmap:
        file = open("dev_map.pickle", mode='bw')

        print("dumping dev map...")
        pickle.dump((level, level_fow, level_navgrid, pg.image.tostring(level_surface, 'RGB'), pg.image.tostring(level_fow_surface, 'RGBA')), file)
        file.close()

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

    # finds all points *next* to reachable points

    for p in touched_points:
        if get_pixel_navgrid(p) == 0:
            continue # flooding *only* from reachable navpoints

        p1 = inbounds((p[0], p[1] + 1))
        if is_valid_navpoint(p1) and get_pixel_navgrid(p1) == 0:
            edge_points.append(p1)
            set_pixel_navgrid(p1, 1)

        p2 = inbounds((p[0], p[1] - 1))
        if is_valid_navpoint(p2) and get_pixel_navgrid(p2) == 0:
            edge_points.append(p2)
            set_pixel_navgrid(p2, 1)

        p3 = inbounds((p[0] + 1, p[1]))
        if is_valid_navpoint(p3) and get_pixel_navgrid(p3) == 0:
            edge_points.append(p3)
            set_pixel_navgrid(p3, 1)

        p4 = inbounds((p[0] - 1, p[1]))
        if is_valid_navpoint(p4) and get_pixel_navgrid(p4) == 0:
            edge_points.append(p4)
            set_pixel_navgrid(p4, 1)

    # flood fill from edge_points
            
    to_check = edge_points

    while True:
        new_to_check = []

        for p in to_check:
            p1 = inbounds((p[0], p[1] + 1))
            if is_valid_navpoint(p1) and get_pixel_navgrid(p1) == 0:
                new_to_check.append(p1)
                set_pixel_navgrid(p1, 1)

            p2 = inbounds((p[0], p[1] - 1))
            if is_valid_navpoint(p2) and get_pixel_navgrid(p2) == 0:
                new_to_check.append(p2)
                set_pixel_navgrid(p2, 1)

            p3 = inbounds((p[0] + 1, p[1]))
            if is_valid_navpoint(p3) and get_pixel_navgrid(p3) == 0:
                new_to_check.append(p3)
                set_pixel_navgrid(p3, 1)

            p4 = inbounds((p[0] - 1, p[1]))
            if is_valid_navpoint(p4) and get_pixel_navgrid(p4) == 0:
                new_to_check.append(p4)
                set_pixel_navgrid(p4, 1)

        if len(new_to_check) == 0:
            break

        to_check = new_to_check

color_lib = [
    conf.empty_color,
    conf.stone_color,
    conf.oxy_color,
    conf.goal_color,
]

def pre_render_level(render_status):
    global level_surface_damaged

    # level_surface.fill((16, 16, 16))

    for i, p in enumerate(level_surface_damaged):
        x, y = p
        val = get_pixel(p)

        pg.draw.rect(level_fow_surface, pg.Color(*conf.fog_color, int((18 - min(level_fow[x][y], 18)) * (255 / 18))), (x * point_size, y * point_size, point_size, point_size))

        pg.draw.rect(level_surface, color_lib[val], (x * point_size, y * point_size, point_size, point_size))

        if level_mark[x][y] > 0:
            pg.draw.rect(level_surface, (255, 0, 0), (x * point_size + mark_margin, y * point_size + mark_margin, point_size - mark_margin * 2, point_size - mark_margin * 2))
        # elif level_navgrid[x][y] == 1:
            # pg.draw.rect(level_surface, (102, 255, 255), (x * point_size, y * point_size, point_size, point_size))

        if not render_status == None: 
            # pro rendering on loading time
            refresh_loading_status(.5 + (i * .5 / len(level_surface_damaged)))
            
            level_gen_yield()

    level_surface_damaged.clear()

def render_level(sur):
    if not len(level_surface_damaged) == 0:
        pre_render_level(None)

    sur.blit(level_surface, cam.translate((0, 0), level_surface.get_size()))

def render_fow(sur):
    if not len(level_surface_damaged) == 0:
        pre_render_level(None)

    sur.blit(level_fow_surface, cam.translate((0, 0), level_fow_surface.get_size()), special_flags=pg.BLEND_ALPHA_SDL2)