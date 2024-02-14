import pygame as pg

import src.fd_camera as cam

# == Far Depths Entities ==
# kind of a ecs system "replacement"

entity_registry = {}

def create_entity(name, e):
    entity_registry[name] = e

    return e

def get_entity(name):
    return entity_registry[name]

# calls a system (component) on every entity if it has that system
def call_system(s_name, *args):
    for name, e in entity_registry.items():
        s = e.get(s_name)

        if not s == None:
            try:
                s(e, *args)
            except:
                print(f"An Exception occured while system \"{s_name}\" was working with entity \"{name}\"!")
                raise

# common system

def render_entities(surface):
    call_system("on_frame", surface)

def tick():
    call_system("tick")