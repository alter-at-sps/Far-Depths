import pygame as pg
import pygame.freetype as freetype
import OpenGL.GL as gl

from src.fd_render import *
import src.fd_camera as cam

# == fd renderer library ==
# a few presets for common (or special) post-processing passes and renderer systems

# basic pass (blit)

def basic_frame(rpass, in_tex, out_fb):
    gl.glUseProgram(rpass["shader_program"])

    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, out_fb)

    gl.glBindTexture(gl.GL_TEXTURE_2D, in_tex)
    # gl.glUniform1f(time_loc, time_)
    
    gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)


def basic_cleanup(rpass):
    gl.glDeleteProgram(rpass["shader_program"])

def setup_basic_pass(vert, frag):
    vs = load_shader(gl.GL_VERTEX_SHADER, vert)
    fs = load_shader(gl.GL_FRAGMENT_SHADER, frag)

    p = gl.glCreateProgram()

    gl.glAttachShader(p, vs)
    gl.glAttachShader(p, fs)
    
    gl.glLinkProgram(p)

    result = gl.glGetProgramiv(p, gl.GL_LINK_STATUS)

    if not result:
        log = gl.glGetProgramInfoLog(p)

        print("error while linking a Gl shader program: ", log)
        quit()

    gl.glDeleteShader(vs)
    gl.glDeleteShader(fs)

    return {
        "frame": basic_frame,
        "cleanup": basic_cleanup,
        "shader_program": p
    }

# PBR bloom pass

def bloom_frame(rpass, in_tex, out_fb):
    pass    

# rect renderer system

def rect_renderer(e, sur):
    trans = e["transform"]
    
    render_area = cam.translate(trans[0], trans[1])

    pg.draw.rect(sur, e["rect_color"], render_area)

# loading screen status renderer

font = freetype.Font("./assets/font/amiga4ever pro2.ttf", 16)

loading_color = (255, 255, 255)

spinboi = "-\\|/"
spinboi_frame = 0

def loading_status_renderer(e, sur):
    # pg.draw.rect(sur, loading_color, (cam.translate_screenspace(e["ui_trans"][0], e["ui_trans"][1])))
    # pg.draw.rect(sur, empty_color, (cam.translate_screenspace(e["ui_trans"][0], (e["ui_trans"][1][0] - loading_box_width * 2, e["ui_trans"][1][1] - loading_box_width * 2))))

    # rect = font.get_rect(e["status_text"])
    # e["ui_trans"][1] = (rect[2], rect[3])

    global spinboi_frame
    spinboi_frame += 1

    font.render_to(sur, cam.translate_screenspace((e["ui_trans"][0][0], e["ui_trans"][0][1]), (e["ui_trans"][1][0], e["ui_trans"][1][1])), e["status_text"] + " " + spinboi[spinboi_frame % 4], (255, 255, 255))

# nls renderer

def nls_renderer(e, sur):
    t = e["ui_trans"]

    render_area = cam.translate_ui(t)

    pg.draw.rect(sur, (54, 85, 2), render_area)