import pygame as pg
import src.fd_render as renderer
import src.pass_lib as rp

renderer.reset_passes()

renderer.add_pass(rp.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
# renderer.add_pass(rp.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/crt_effect.frag"))
renderer.add_pass(rp.setup_basic_pass("src/shaders/fs_trig.vert", "src/shaders/curve_effect.frag"))

x = 0
y = 0

while True:
    # events
    for e in pg.event.get():
        if e.type == pg.QUIT:
            quit()
        if e.type == pg.WINDOWRESIZED:
            renderer.recreate_renderer((e.dict["x"], e.dict["y"]))
    
    keys = pg.key.get_pressed()

    if keys[pg.K_w]:
        y -= 10

    if keys[pg.K_s]:
        y += 10

    if keys[pg.K_a]:
        x -= 10

    if keys[pg.K_d]:
        x += 10

    sur = renderer.get_surface()

    sur.fill((0, 28, 0))
    pg.draw.rect(sur, (128, 128, 128), (100 + x, 100 + y, 50, 50))

    renderer.submit()