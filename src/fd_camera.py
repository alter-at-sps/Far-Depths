# == 2D Global Camera ==

import src.fd_render as ren

camera_translation = [ 0, 0 ]

def set_camera(pos):
    global camera_translation
    camera_translation = pos

def get_camera():
    return camera_translation 

def translate(pos, size):
    # screen_pos = world_pos - size // 2 (offsets the position from the center of the object to the top left corner for pygame) - camera_translation (correct for the camera position) + get_surface().get_size() // 2 (correct for pygame window size so (0, 0) is in the middle of the screen)
    return (pos[0] - size[0] // 2 - camera_translation[0] + ren.get_surface().get_width() // 2, pos[1] - size[1] // 2 - camera_translation[1] + ren.get_surface().get_height() // 2, size[0], size[1])

def translate_screenspace(pos, size):
    # same as translate but without camera_translation (for ui and screen space objects)
    return (pos[0] - size[0] // 2 + ren.get_surface().get_width() // 2, pos[1] - size[1] // 2 - camera_translation[1] + ren.get_surface().get_height() // 2, size[0], size[1])

def translate_ui(trans):
    # translates ui_trans in screenspace with respect to their anchors

    screensize = ren.get_surface().get_size()
    anchored_points = (trans[1][0] if not trans[0][0] else screensize[0] - trans[1][0], trans[1][1] if not trans[0][1] else screensize[1] - trans[1][1], trans[2][0] if not trans[0][0] else screensize[0] - trans[2][0], trans[2][1] if not trans[0][1] else screensize[1] - trans[2][1])

    return (min(anchored_points[0], anchored_points[2]), min(anchored_points[1], anchored_points[3]), max(anchored_points[0], anchored_points[2]) - min(anchored_points[0], anchored_points[2]), max(anchored_points[1], anchored_points[3]) - min(anchored_points[1], anchored_points[3]))

def inverse_translate(pos):
    # translates a screen space position to world space
    return (pos[0] + camera_translation[0] - ren.get_surface().get_width() // 2, pos[1] + camera_translation[1] - ren.get_surface().get_height() // 2)