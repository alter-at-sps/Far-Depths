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

e = en.create_entity("test e", {
    "transform": [
        (100, 100),
        (50, 50)
    ],

    "on_frame": rlib.rect_renderer,
    "rect_color": (255, 255, 0)
})

def update_pos(e):
    trans = e["transform"]

    mouse_pos = pg.mouse.get_pos()
    wm_pos = cam.inverse_translate(mouse_pos)

    trans[0] = wm_pos

e2 = en.create_entity("test e2", {
    "transform": [
        (50, 50),
        (50, 50)
    ],

    "on_frame": rlib.rect_renderer,
    "rect_color": (128, 128, 128),

    "tick": update_pos
})

# lvl.gen_level(None, 25)
# lvl.init_level()

i = 0

mgr.in_game_loop()

exit()

while True:
    # events
    for e in pg.event.get():
        if e.type == pg.QUIT:
            quit()
        if e.type == pg.WINDOWRESIZED:
            ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)
    
    keys = pg.key.get_pressed()

    if keys[pg.K_w]:
        pos = cam.get_camera()
        pos[1] -= 10
        cam.set_camera(pos)

    if keys[pg.K_s]:
        pos = cam.get_camera()
        pos[1] += 10
        cam.set_camera(pos)

    if keys[pg.K_a]:
        pos = cam.get_camera()
        pos[0] -= 10
        cam.set_camera(pos)

    if keys[pg.K_d]:
        pos = cam.get_camera()
        pos[0] += 10
        cam.set_camera(pos)

    if keys[pg.K_e]:
        print(astar.pathfind((pos[0] // 20 + 127, pos[1] // 20 + 127), (pos[0] // 20 + 127, pos[1] // 20 + 129)))

    mouse_pos = pg.mouse.get_pos()
    wm_pos = cam.inverse_translate(mouse_pos)
    gm_pos = lvl.world_to_grid_space(wm_pos)

    print(wm_pos, gm_pos)

    sur = ren.get_surface()
    sur.fill((0, 28, 0))

    pos = cam.get_camera()
    
    lvl.set_pixel_navgrid(gm_pos, 1)
    lvl.unfog_area([ gm_pos ], 36)

    en.tick()

    lvl.render_level(sur)
    en.render_entities(sur)

    ren.submit()