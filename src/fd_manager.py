import pygame as pg

import src.fd_render as ren
import src.fd_render_lib as rlib

import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_entity as en
import src.fd_units as un
import src.fd_astar as astar
import src.fd_notif as nls

# == Far Depths Main Event Loop ==

def in_game_loop():
    lvl.gen_level(None, 25)

    # generate base

    base = en.create_entity("player_base", {
        "transform": [ # base at world root
            (0, 0),
            (40, 40)
        ],

        "on_frame": rlib.rect_renderer,
        "rect_color": (254, 254, 254)

        # "tick": None,
    })

    base_grid_pos = lvl.world_to_grid_space(base["transform"][0])

    lvl.set_circle(base_grid_pos, 100, 0) # clear spawn location
    lvl.set_pixel_navgrid(base_grid_pos, 1) # initial navgrid origin
    lvl.unfog_area([ base_grid_pos ], 64) # initial unfoged area

    for i, unit in enumerate([ (247, 250) ]):#[ (0, -1), (1, -1), (-1, 0), (-1, 1) ]):
        en.create_entity(f"unit_{i}", {
            "transform": [
                None, # set on ticks
                (15, 15) 
            ],

            "grid_trans": unit,

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

    nls.setup_nls()

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        # user input processing

        keys = pg.key.get_pressed()

        is_shift = keys[pg.K_LSHIFT]

        if keys[pg.K_e]:
            mouse_pos = pg.mouse.get_pos()
            wm_pos = cam.inverse_translate(mouse_pos)
            gm_pos = lvl.world_to_grid_space(wm_pos)

            un.add_move_task(en.get_entity("unit_0"), gm_pos, is_shift)

        if pg.mouse.get_pressed()[1]:
            mouse_pos = pg.mouse.get_pos()
            wm_pos = cam.inverse_translate(mouse_pos)
            gm_pos = lvl.world_to_grid_space(wm_pos)

            lvl.set_pixel(gm_pos, 1)
            lvl.set_pixel_navgrid(gm_pos, 0)

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

            # lvl.set_pixels_for_mining(mining_queue)
            un.add_mining_task(en.get_entity("unit_0"), mining_queue, is_shift)

        # main game update

        en.tick()

        cam.set_camera(en.get_entity("unit_0")["transform"][0])

        # render frame

        sur = ren.get_surface()

        lvl.render_level(sur)
        en.render_entities(sur)

        if not drag_area == None:
            pg.draw.rect(sur, (64, 255, 64), (drag_area[0][0], drag_area[0][1], drag_area[1][0] - drag_area[0][0], drag_area[1][1] - drag_area[0][1]))

        ren.submit()

def menu_loop():
    pass