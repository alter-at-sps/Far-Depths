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

# setup post-processing stack
ren.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
ren.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/curve_effect.frag"))
ren.add_pass(rlib.setup_bloom_pass("src/shaders/fs_trig.vert", "src/shaders/bloom_downsample.frag", "src/shaders/bloom_upsample.frag", "src/shaders/bloom_copy.frag", 6))

x = 0
y = 0

# lvl.gen_level(None, 25)
# lvl.init_level()

i = 0

loop_list = [
    mgr.menu_loop,
    mgr.in_game_loop,
]

while True:
    if i == None:
        quit()

    i = loop_list[i]() # call the next requested loop