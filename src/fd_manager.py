import pygame as pg
import random

import src.fd_render as ren
import src.fd_render_lib as rlib

import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_entity as en
import src.fd_units as un
import src.fd_astar as astar
import src.fd_notif as nls
import src.fd_config as conf

# == Far Depths Main Event Loop ==

def in_game_loop():
    pg.display.set_caption("Far Depths - Traveling to a forbidden location")

    lvl.gen_level(None, 25)

    pg.display.set_caption("Far Depths - Scanning and Mining" if random.randint(0, 100) > 40 else random.choice(conf.secret_titles)) 

    # generate base

    base_pos = (conf.level_size[0] // 2, conf.level_size[1] // 2)
    base_world_pos = lvl.grid_to_world_space(base_pos)

    base = en.create_entity("player_base", {
        "transform": [ # base at world root
            (base_world_pos[0] + 30, base_world_pos[1] + 20),
            (60, 40)
        ],

        "on_frame": rlib.rect_renderer,
        "rect_color": (254, 254, 254)

        # "tick": None,
    })

    lvl.set_circle(base_pos, 100, 0) # clear spawn location
    lvl.set_pixel_navgrid(base_pos, 1) # initial navgrid origin
    lvl.unfog_area([ base_pos ], 64) # initial unfoged area

    for i, unit in enumerate([ (0, -1), (1, -1), (-1, 0), (-1, 1) ], 1):
        en.create_entity(f"unit_{i}", {
            "transform": [
                None, # set on ticks
                (15, 15) 
            ],

            "grid_trans": (base_pos[0] + unit[0], base_pos[1] + unit[1]),

            "on_frame": rlib.rect_renderer,
            "rect_color": (128, 128, 128),

            "tick": un.unit_tick,

            # unit components

            "unit_index": i,
            "stored_materials": [
                None, # air (unused)
                0, # rock
                0, # oxy
                0, # goal
            ],

            "task_queue": [],
            "mining_queue": set(),

            "already_idle": True,
        })

    is_dragging = False
    drag_start_pos = None

    cam_x = 0
    cam_y = 0

    selected_unit = 1

    nls.setup_nls()

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        # user input processing

        keys = pg.key.get_pressed()

        is_shift = keys[pg.K_LSHIFT]

        if keys[pg.K_w]:
            cam_y -= conf.cam_speed * ren.delta_time
        
        if keys[pg.K_s]:
            cam_y += conf.cam_speed * ren.delta_time
        
        if keys[pg.K_d]:
            cam_x += conf.cam_speed * ren.delta_time
        
        if keys[pg.K_a]:
            cam_x -= conf.cam_speed * ren.delta_time

        cam.set_camera((int(cam_x), int(cam_y)))

        if keys[pg.K_1]:
            selected_unit = 1
        if keys[pg.K_2]:
            selected_unit = 2
        if keys[pg.K_3]:
            selected_unit = 3
        if keys[pg.K_4]:
            selected_unit = 4

        if keys[pg.K_e]:
            mouse_pos = pg.mouse.get_pos()
            wm_pos = cam.inverse_translate(mouse_pos)
            gm_pos = lvl.world_to_grid_space(wm_pos)

            un.add_move_task(en.get_entity(f"unit_{selected_unit}"), gm_pos, is_shift)

        # drag processing

        # not None if currently dragging
        drag_area = None

        # not None if finished dragging this frame
        final_drag_area = None

        if not is_dragging and pg.mouse.get_pressed()[0]:
            # started dragging

            is_dragging = True

            drag_start_pos = pg.mouse.get_pos()

        elif is_dragging and not pg.mouse.get_pressed()[0]:
            # stopped dragging

            is_dragging = False

            final_drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))
            drag_start_pos = None

        if is_dragging:
            drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))

        # mark area for mining
        if not final_drag_area == None:
            w_drag_area = (cam.inverse_translate(final_drag_area[0]), cam.inverse_translate(final_drag_area[1]))
            g_drag_area = (lvl.world_to_grid_space(w_drag_area[0]), lvl.world_to_grid_space(w_drag_area[1]))

            mining_queue = un.create_mining_queue(g_drag_area)


            if not len(mining_queue) == 0:
                # lvl.set_pixels_for_mining(mining_queue)
                un.add_mining_task(en.get_entity(f"unit_{selected_unit}"), mining_queue, is_shift)

        # main game update

        en.tick()

        # render frame

        sur = ren.get_surface()

        lvl.render_level(sur)
        en.render_entities(sur)
        lvl.render_fow(sur)

        en.render_ui(sur)

        if not drag_area == None:
            pg.draw.rect(sur, (64, 255, 64), (drag_area[0][0], drag_area[0][1], drag_area[1][0] - drag_area[0][0], drag_area[1][1] - drag_area[0][1]))

        ren.submit()

    en.reset()

    return 0 # switch to menu loop

# == main menu ==

game_started = False

def is_click_on_ui(t, click):
    pos = click[0]
    ui_area = cam.translate_ui(t)

    rel_pos = (pos[0] - ui_area[0], pos[1] - ui_area[1])

    return (rel_pos[0] >= 0 and rel_pos[0] <= ui_area[2]) and (rel_pos[1] >= 0 and rel_pos[1] <= ui_area[3])

def start_game(e, click):
    if not is_click_on_ui(e["ui_trans"], click):
        return

    global game_started
    game_started = True

def menu_loop():
    pg.display.set_caption("Far Depths - Chiling at central")

    global game_started
    game_started = False

    title = en.create_entity("menu_title", {
        "ui_trans": [
            (2, 2), # anchor to center
            (-250, -250),
            (250, -170)
        ],

        "on_ui_frame": rlib.title_renderer,
    })

    start_button = en.create_entity("start_button", {
        "ui_trans": [
            (2, 2),
            (-110, -50),
            (110, -5)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": start_game,
        "button_border_size": 5,
        "button_text": "Undock and Start",
    })

    howto_button = en.create_entity("howto_button", {
        "ui_trans": [
            (2, 2),
            (-110, 5),
            (110, 50)
        ],

        "on_ui_frame": rlib.button_renderer,
        "button_border_size": 5,
        "button_text": "How to Play",
    })

    quit_text = en.create_entity("quit_text", {
        "ui_trans": [
            (2, 2),
            (150, 150),
            (-150, 185)
        ],

        "on_ui_frame": rlib.text_renderer,
        "text": "To quit close the window :p",
        "text_size": 12,
        "text_color": conf.ui_foreground_faded_color,
    })

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.MOUSEBUTTONDOWN:
                en.click_event((e.dict["pos"], e.dict["button"]))
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        if game_started:
            break

        sur = ren.get_surface()
        # sur.fill(conf.ui_background_color)

        en.render_ui(sur)
        ren.submit()

    en.reset()

    return 1 # switch to in-game loop