# == 2D Global Camera ==

camera_translation = [ 0, 0 ]

def set_camera(pos):
    global camera_translation
    camera_translation = pos

def get_camera():
    return camera_translation

def translate(pos, size):
    return (pos[0] - size[0] // 2 - camera_translation[0], pos[1] - size[1] // 2 - camera_translation[1], size[0], size[1])