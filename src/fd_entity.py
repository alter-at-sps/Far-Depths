import pygame as pg

import src.fd_camera as cam

# == A Far Depths Entity used for rendering ==
# kind of a ecs system replacement

entity_registry = {}

def create_entity(name, e):
    entity_registry[name] = e

    return e

def get_entity(name):
    return entity_registry[name]

# iteration done directly with entity_registry

# == entity systems ==

def render_entities(surface):
    for name, e in entity_registry.items():
        rt = e.get("renderer")

        if rt == None:
            continue

        trans = e.get("trans")

        # rect renderer
        if rt == 0:
            draw_area = cam.translate(trans[0], trans[1])
            pg.draw.rect(surface, e["rect_color"], draw_area)

        # ui renderer
        elif rt == 1:
            ui_trans = e.get("ui_trans")
            # TODO

        # unknown renderer type
        else:
            print(f"warning: entity \"{name}\" has an unknown renderer!")