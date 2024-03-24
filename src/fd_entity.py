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
    for name, e in dict(entity_registry).items():
        s = e.get(s_name)

        if not s == None:
            try:
                s(e, *args)
            except:
                print(f"An Exception occured while system \"{s_name}\" was working with entity \"{name}\"!")
                raise

# calls a system (component) on every entity if it has that system and stop if system returns true
def call_system_consuming(s_name, *args):
    for name, e in dict(entity_registry).items():
        s = e.get(s_name)

        if not s == None:
            try:
                c = s(e, *args)

                if c:
                    return True
            except:
                print(f"An Exception occured while system \"{s_name}\" was working with entity \"{name}\"!")
                raise
    
    return False

def reset():
    entity_registry.clear()

# common system

def render_entities(surface):
    call_system("on_early_frame", surface)
    call_system("on_frame", surface)
    # call_system("on_late_frame", surface)

def render_ui(surface):
    call_system("on_ui_frame", surface)

def click_event(click):
    return call_system_consuming("on_click", click)

def tick():
    call_system("tick")