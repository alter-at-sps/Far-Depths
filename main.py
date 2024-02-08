import pygame as pg
import src.fd_render as renderer
import src.pass_lib as rp

import src.fd_entity as entity
import src.fd_camera as cam

renderer.reset_passes()

renderer.add_pass(rp.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
renderer.add_pass(rp.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/curve_effect.frag"))

x = 0
y = 0

e = entity.create_entity("test e", {
    "trans": [
        (100, 100),
        (50, 50)
    ],

    "renderer": 0,
    "rect_color": (255, 255, 0)
})


e2 = entity.create_entity("test e2", {
    "trans": [
        (50, 50),
        (50, 50)
    ],

    "renderer": 0,
    "rect_color": (128, 128, 128)
})

while True:
    # events
    for e in pg.event.get():
        if e.type == pg.QUIT:
            quit()
        if e.type == pg.WINDOWRESIZED:
            renderer.recreate_renderer((e.dict["x"], e.dict["y"]))
    
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

    entity.render_entities(sur)

    renderer.submit()