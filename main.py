import pygame as pg
import src.fd_render as ren
import src.fd_render_lib as rlib

import src.fd_entity as en
import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_astar as astar
import src.fd_manager as mgr

# == Far Depths Bootstraper ==

ren.reset_passes()

ren.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
ren.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/curve_effect.frag"))

x = 0
y = 0

# lvl.gen_level(None, 25)
# lvl.init_level()

i = 0

mgr.in_game_loop()