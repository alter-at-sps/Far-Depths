import pygame as pg
import src.fd_render as render

while True:
    # events
    for e in pg.event.get():
        if e.type == pg.QUIT:
            quit()

    pg.draw.rect(render.get_surface(), (128, 128, 128), (100, 100, 200, 200))

    render.submit()