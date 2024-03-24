import pygame as pg

import src.fd_entity as en
import src.fd_render_lib as rlib
import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_signal as sig

# == Far Depths Structure Controllers ==

next_struct_index = 1

def spawn_struct(p, t):
    global next_struct_index

    pos = lvl.grid_to_world_space(p)

    s = en.create_entity(f"struct_{next_struct_index}", {
        "transform": [
            (pos[0] + lvl.point_size // 2, pos[1] + lvl.point_size // 2),
            (18, 18)
        ],

        "grid_trans": p,

        "on_frame": rlib.struct_renderer,
        "on_early_frame": rlib.struct_early_renderer,
        "tick": struct_tick,
        "struct_type": t,

        "pretty_name": (2, f"Structure #{next_struct_index}"),
    })

    next_struct_index += 1

    if t == 0:
        sig.add_transceiver(p)
    elif t == 1:
        rp = lvl.grid_to_world_space(sig.find_pipeline_sink(p)[0])
        s["linked_trans"] = (rp[0] + lvl.point_size // 2, rp[1] + lvl.point_size // 2)

        sig.add_substation(p)

    return s

def setup_struct_build_ghost():
    en.create_entity("struct_ghost", {
        "transform": [
            None, # set on ticks
            (18, 18)
        ],

        "on_frame": rlib.struct_ghost_renderer,
        "tick": struct_ghost_tick,
    })

def struct_tick(e: dict):
    pass

def struct_ghost_tick(e: dict):
    pos = lvl.grid_to_world_space(lvl.world_to_grid_space(cam.inverse_translate(pg.mouse.get_pos())))
    e["transform"][0] = (pos[0] + lvl.point_size // 2, pos[1] + lvl.point_size // 2)
    e["struct_index"] = en.get_entity("build_select")["selected_index"]