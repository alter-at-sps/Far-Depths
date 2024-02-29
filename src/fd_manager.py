import pygame as pg

import src.fd_render as ren
import src.fd_render_lib as rlib

import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_entity as en
import src.fd_units as un
import src.fd_astar as astar

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
            "stored_materials": [],
        })

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        keys = pg.key.get_pressed()

        if keys[pg.K_e]:
            mouse_pos = pg.mouse.get_pos()
            wm_pos = cam.inverse_translate(mouse_pos)
            gm_pos = lvl.world_to_grid_space(wm_pos)

            en.get_entity("unit_0")["current_path"] = astar.pathfind(en.get_entity("unit_0")["grid_trans"], gm_pos)

        en.tick()

        cam.set_camera(en.get_entity("unit_0")["transform"][0])

        sur = ren.get_surface()

        lvl.render_level(sur)
        en.render_entities(sur)

        ren.submit()

def menu_loop():
    pass