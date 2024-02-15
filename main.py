import pygame as pg
import src.fd_render as renderer
import src.fd_render_lib as rlib

import src.fd_entity as en
import src.fd_camera as cam
import src.fd_level as lvl

# == Far Depths Main Loop ==

renderer.reset_passes()

renderer.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
renderer.add_pass(rlib.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/curve_effect.frag"))

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


e2 = en.create_entity("test e2", {
    "transform": [
        (50, 50),
        (50, 50)
    ],

    "on_frame": rlib.rect_renderer,
    "rect_color": (128, 128, 128)
})

lvl.gen_level(None, 25)

i = 0

while True:
    # events
    for e in pg.event.get():
        if e.type == pg.QUIT:
            quit()
        if e.type == pg.WINDOWRESIZED:
            renderer.recreate_renderer((e.dict["x"], e.dict["y"]), 1)
    
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

    sur = renderer.get_surface()
    sur.fill((0, 28, 0))

    pos = cam.get_camera()
    lvl.unfog_area([ (pos[0] // 20 + 127, pos[1] // 20 + 127) ], 36)
    lvl.set_pixel((0, 0), 0)

    en.tick()

    en.render_entities(sur)
    lvl.render_level(sur)

    renderer.submit()