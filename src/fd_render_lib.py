import pygame as pg
import pygame.freetype as freetype
import pygame.gfxdraw as gfx
import OpenGL.GL as gl

import src.fd_render as ren
import src.fd_camera as cam
import src.fd_config as conf

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
    vs = ren.load_shader(gl.GL_VERTEX_SHADER, vert)
    fs = ren.load_shader(gl.GL_FRAGMENT_SHADER, frag)

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

    font.render_to(sur, cam.translate_screenspace((e["transform"][0][0], e["transform"][0][1]), (e["transform"][1][0], e["transform"][1][1])), e["status_text"] + " " + spinboi[spinboi_frame % 4], (255, 255, 255))

# nls renderer

def nls_renderer(e, sur):
    t = e["ui_trans"]

    render_area = cam.translate_ui(t)

    terminal_render_area = (render_area[0] + conf.nls_border_size, render_area[1] + conf.nls_border_size, render_area[2] - conf.nls_border_size * 2, render_area[3] - conf.nls_border_size * 2) 
    
    # border and terminal background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, terminal_render_area)

    # terminal text

    cursor_draw_point = (terminal_render_area[0] + conf.nls_cursor_margin, terminal_render_area[1] + conf.nls_cursor_margin, terminal_render_area[2] - conf.nls_cursor_margin * 2, conf.nls_log_line_size)

    for i, line in enumerate(e["nls_log_console"]):
        line_area = (cursor_draw_point[0], cursor_draw_point[1] + conf.nls_log_line_size * i, *cursor_draw_point[2:3])

        font.render_to(sur, line_area, line[1], conf.nls_log_colors[line[0]], size=10)
    
    # notification ping outline

    notif = e.get("nls_notif_timer")

    if not notif == None:
        notif[1] -= ren.delta_time

        if notif[1] <= 0:
            e.pop("nls_notif_timer")
            return

        if int(notif[1] * 4) % 2 == 1:
            alpha = 200
        else:
            alpha = 127

        for i in range(conf.nls_outline_width):
            outline_render_area = (render_area[0] - conf.nls_outline_margin - i, render_area[1] - conf.nls_outline_margin - i, render_area[2] + conf.nls_outline_margin * 2 + 2 * i, render_area[3] + conf.nls_outline_margin * 2 + 2 * i)

            gfx.rectangle(sur, outline_render_area, (*conf.nls_log_colors[notif[0]], alpha))

# menu title renderer

def title_renderer(e, sur):
    render_area = cam.translate_ui(e["ui_trans"])

    font.render_to(sur, render_area, "Far Depths", conf.ui_foreground_color, size=58)

# menu button renderer

def button_renderer(e, sur):
    render_area = cam.translate_ui(e["ui_trans"])

    button_border_size = e["button_border_size"]
    button_render_area = (render_area[0] + button_border_size, render_area[1] + button_border_size, render_area[2] - button_border_size * 2, render_area[3] - button_border_size * 2)

    # border and button background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, button_render_area)

    button_text = e["button_text"]

    text_area = font.get_rect(button_text, size=12)

    text_dest = (button_render_area[0] + button_render_area[2] // 2 - text_area[2] // 2, button_render_area[1] + button_render_area[3] // 2 - text_area[3] // 2)
    font.render_to(sur, text_dest, button_text, conf.ui_foreground_color, size=12)