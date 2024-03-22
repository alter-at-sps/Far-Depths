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

    gl.glActiveTexture(gl.GL_TEXTURE0)
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

# PBR bloom pass (because i was bored)

def downsample_frame(rpass, in_tex):
    gl.glUseProgram(rpass["downsample_program"])

    mip_res = ren.fd_renderer.res
    src_res_loc = rpass["downsample_src_resolution_location"]
    gl.glUniform2i(src_res_loc, mip_res[0], mip_res[1])

    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, in_tex)

    tex_bufs = rpass["mip_tex_bufs"]
    mip_res = rpass["mip_resolutions"]

    for i in range(rpass["mip_count"]):
        gl.glViewport(0, 0, mip_res[i][0], mip_res[i][1])
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, tex_bufs[i], 0)

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)

        # set current mip as input for next iteration
        gl.glUniform2i(src_res_loc, mip_res[i][0], mip_res[i][1])
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_bufs[i])

    gl.glUseProgram(0)

def upsample_frame(rpass):
    gl.glUseProgram(rpass["upsample_program"])

    # enable additive blending
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)
    gl.glBlendEquation(gl.GL_FUNC_ADD)

    res = ren.fd_renderer.res
    tex_bufs = rpass["mip_tex_bufs"]
    mip_res = rpass["mip_resolutions"]

    for i in range(rpass["mip_count"] - 1, 0, -1):
        # set input mip
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_bufs[i])

        # set output mip
        gl.glViewport(0, 0, mip_res[i-1][0], mip_res[i-1][1])
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, tex_bufs[i-1], 0)

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)

    gl.glDisable(gl.GL_BLEND)

    gl.glUseProgram(0)

def bloom_frame(rpass, in_tex, out_fb):
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, rpass["bloom_fb"])

    downsample_frame(rpass, in_tex)

    # gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, out_fb)

    upsample_frame(rpass)

    # res = ren.fd_renderer.res
    # gl.glViewport(0, 0, res[0], res[1])
# 
    # return

    # copy / mix bloom

    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, out_fb)

    gl.glUseProgram(rpass["copy_program"])

    # bind input texture
    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, in_tex)

    # bind bloom texture
    gl.glActiveTexture(gl.GL_TEXTURE1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, rpass["mip_tex_bufs"][0])
    
    res = ren.fd_renderer.res
    gl.glViewport(0, 0, res[0], res[1])

    gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)

    # clean up

    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    gl.glActiveTexture(gl.GL_TEXTURE0)
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    gl.glUseProgram(0)

def bloom_cleanup(rpass, full = True):
    gl.glDeleteTextures(len(rpass["mip_tex_bufs"]), rpass["mip_tex_bufs"])
    gl.glDeleteFramebuffers(1, [rpass["bloom_fb"]])

    if full:
        gl.glDeleteProgram(rpass["downsample_program"])
        gl.glDeleteProgram(rpass["upsample_program"])
        gl.glDeleteProgram(rpass["copy_program"])

def bloom_recreate(rpass, res):
    # delete old resources

    if not rpass.get("bloom_fb") == None:
        bloom_cleanup(rpass, False)

    # create bloom mips

    # fb used for overlaying the individual mips on the upsample pass
    fb = gl.glGenFramebuffers(1)
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fb)

    # mip textures used to hold the individual mips (for the downsample pass)
    tex_bufs = gl.glGenTextures(rpass["mip_count"])
    mip_reses = []
    
    mip_res = res

    for i in range(rpass["mip_count"]):
        mip_res = (mip_res[0] // 2, mip_res[1] // 2)
        mip_reses.append(mip_res)

        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_bufs[i])
        
        # setup mip format and size (using HDR format only for the sake of following the guide, shouldn't be nesessary here)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_R11F_G11F_B10F, mip_res[0], mip_res[1], 0, gl.GL_RGB, gl.GL_FLOAT, None)

        # linear filter instead of nearest filtering (this is what's doing the bloom effect) 
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_BORDER)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_BORDER)
        gl.glTexParameterfv(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BORDER_COLOR, [ 0, 0, 0, 0 ])

    gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, tex_bufs[0], 0)

    if not gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) == gl.GL_FRAMEBUFFER_COMPLETE:
        print("fd renderer: failed to init offscreen bloom framebuffer!")
        quit()

    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    rpass["bloom_fb"] = fb
    rpass["mip_tex_bufs"] = tex_bufs
    rpass["mip_resolutions"] = mip_reses

def setup_bloom_pass(fs_vert, down_frag, up_frag, copy_frag, mip_count):
    # create shader programs

    vs = ren.load_shader(gl.GL_VERTEX_SHADER, fs_vert)
    fs = ren.load_shader(gl.GL_FRAGMENT_SHADER, down_frag)

    dp = gl.glCreateProgram()

    gl.glAttachShader(dp, vs)
    gl.glAttachShader(dp, fs)
    
    gl.glLinkProgram(dp)
    result = gl.glGetProgramiv(dp, gl.GL_LINK_STATUS)

    if not result:
        log = gl.glGetProgramInfoLog(dp)

        print("error while linking a bloom downsample Gl shader program: ", log)
        quit()

    gl.glDeleteShader(vs)
    gl.glDeleteShader(fs)

    d_res_loc = gl.glGetUniformLocation(dp, "in_res")

    vs = ren.load_shader(gl.GL_VERTEX_SHADER, fs_vert)
    fs = ren.load_shader(gl.GL_FRAGMENT_SHADER, up_frag)

    up = gl.glCreateProgram()

    gl.glAttachShader(up, vs)
    gl.glAttachShader(up, fs)
    
    gl.glLinkProgram(up)
    result = gl.glGetProgramiv(up, gl.GL_LINK_STATUS)

    if not result:
        log = gl.glGetProgramInfoLog(up)

        print("error while linking a bloom upsample Gl shader program: ", log)
        quit()

    gl.glDeleteShader(vs)
    gl.glDeleteShader(fs)

    vs = ren.load_shader(gl.GL_VERTEX_SHADER, fs_vert)
    fs = ren.load_shader(gl.GL_FRAGMENT_SHADER, copy_frag)

    copy = gl.glCreateProgram()

    gl.glAttachShader(copy, vs)
    gl.glAttachShader(copy, fs)
    
    gl.glLinkProgram(copy)
    result = gl.glGetProgramiv(copy, gl.GL_LINK_STATUS)

    if not result:
        log = gl.glGetProgramInfoLog(copy)

        print("error while linking a bloom copy Gl shader program: ", log)
        quit()

    gl.glDeleteShader(vs)
    gl.glDeleteShader(fs)

    # sets the in_bloom_texture the texture unit GL_TEXTURE1
    bloom_tex_log = gl.glGetUniformLocation(copy, "in_bloom_texture")
    
    gl.glUseProgram(copy)
    gl.glUniform1i(bloom_tex_log, 1)
    gl.glUseProgram(0)

    rpass = {
        "frame": bloom_frame,
        "cleanup": bloom_cleanup,
        "recreate": bloom_recreate,
        "downsample_program": dp,
        "downsample_src_resolution_location": d_res_loc,
        "upsample_program": up,
        "copy_program": copy,
        "mip_count": mip_count,
        # more to be added by bloom_recreate
    }

    bloom_recreate(rpass, ren.fd_renderer.res)

    return rpass

# rect renderer system

def rect_renderer(e, sur):
    trans = e["transform"]
    
    render_area = cam.translate(trans[0], trans[1])

    pg.draw.rect(sur, e["rect_color"], render_area)

# struct renderer

def struct_ghost_renderer(e, sur):
    if not ui_mode == 1:
        return

    trans = e["transform"]
    render_area = cam.translate(trans[0], trans[1])

    pg.draw.rect(sur, (127, 127, 127), render_area)

# ui globals

font = freetype.Font("./assets/font/amiga4ever pro2.ttf", 16)
ui_mode = 0

# loading screen status renderer

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
    if not ui_mode == 0:
        return

    t = e["ui_trans"]

    render_area = cam.translate_ui(t)

    terminal_render_area = (render_area[0] + conf.nls_border_size, render_area[1] + conf.nls_border_size, render_area[2] - conf.nls_border_size * 2, render_area[3] - conf.nls_border_size * 2) 
    
    # border and terminal background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, terminal_render_area)

    # panel decor tag

    font.render_to(sur, (terminal_render_area[0] + 5, terminal_render_area[1] + 5), "> nls v1.36", conf.ui_foreground_faded_color, size=8)

    # terminal text

    cursor_draw_point = (terminal_render_area[0] + conf.nls_cursor_margin, terminal_render_area[1] + conf.nls_cursor_margin + 10, terminal_render_area[2] - conf.nls_cursor_margin * 2, conf.nls_log_line_size)

    for i, line in enumerate(e["nls_log_console"]):
        line_area = (cursor_draw_point[0], cursor_draw_point[1] + conf.nls_log_line_size * i, *cursor_draw_point[2:3])

        font.render_to(sur, line_area, line[1], conf.nls_log_colors[line[0]], size=10)
    
    # notification ping outline

    notif = e["nls_notif_timer"]

    if not notif[0] == None:
        notif[0] -= ren.delta_time

        if notif[0] <= 0:
            notif[0] = None
        else:
            if int(notif[0] * 4) % 2 == 1:
                alpha = 200
            else:
                alpha = 127

            for i in range(conf.nls_outline_width):
                outline_render_area = (render_area[0] - conf.nls_outline_margin - i, render_area[1] - conf.nls_outline_margin - i, render_area[2] + conf.nls_outline_margin * 2 + 2 * i, render_area[3] + conf.nls_outline_margin * 2 + 2 * i)

                gfx.rectangle(sur, outline_render_area, (*conf.nls_log_colors[2], alpha))
    
    elif not notif[1] == None:
        notif[1] -= ren.delta_time

        if notif[1] <= 0:
            notif[1] = None
        else:
            if int(notif[1] * 4) % 2 == 1:
                alpha = 200
            else:
                alpha = 127

            for i in range(conf.nls_outline_width):
                outline_render_area = (render_area[0] - conf.nls_outline_margin - i, render_area[1] - conf.nls_outline_margin - i, render_area[2] + conf.nls_outline_margin * 2 + 2 * i, render_area[3] + conf.nls_outline_margin * 2 + 2 * i)

                gfx.rectangle(sur, outline_render_area, (*conf.nls_log_colors[1], alpha))

# ctl renderer

def ctl_renderer(e, sur):
    if not ui_mode == 0:
        return

    t = e["ui_trans"]
    data = e["panel_data"]

    render_area = cam.translate_ui(t)
    panel_render_area = (render_area[0] + conf.ctl_border_size, render_area[1] + conf.ctl_border_size, render_area[2] - conf.ctl_border_size * 2, render_area[3] - conf.ctl_border_size * 2)

    # border and panel background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, panel_render_area)

    # panel decor tag

    font.render_to(sur, (panel_render_area[0] + 5, panel_render_area[1] + 5), "> ctl_panel v2.16", conf.ui_foreground_faded_color, size=8)

    # title

    title_text = data["selected_title"][1]
    title_area = font.get_rect(title_text, size=24)

    title_area = (panel_render_area[0] + panel_render_area[2] // 2 - title_area[2] // 2, panel_render_area[1] + 60 - title_area[3] // 2)
    font.render_to(sur, title_area, title_text, conf.unit_colors[data["selected_title"][0]], size=24)

    # status

    status_text = data["status"]
    status_area = font.get_rect(status_text, size=14)

    status_area = (panel_render_area[0] + panel_render_area[2] // 2 - status_area[2] // 2, panel_render_area[1] + 90 - status_area[3] // 2)
    font.render_to(sur, status_area, status_text, conf.ui_foreground_faded_color, size=14)

    # build button

    #build_border_area = (panel_render_area[0] + 20, status_area[1] + 30, panel_render_area[2] - 40, 40)
    build_border_area = cam.translate_ui(e["build_ui_trans"])
    build_area = (build_border_area[0] + conf.ctl_button_border_size, build_border_area[1] + conf.ctl_button_border_size, build_border_area[2] - conf.ctl_button_border_size * 2, build_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color, build_border_area)
    pg.draw.rect(sur, conf.ui_background_color, build_area)

    build_text_area = font.get_rect("Build structure [e]", size=12)
    build_text_area = (build_area[0] + build_area[2] // 2 - build_text_area[2] // 2, build_area[1] + build_area[3] // 2 - build_text_area[3] // 2)

    font.render_to(sur, build_text_area, "Build structure [e]", conf.ui_foreground_color, size=12)

    # dock button

    dock_border_area = cam.translate_ui(e["dock_ui_trans"])
    dock_area = (dock_border_area[0] + conf.ctl_button_border_size, dock_border_area[1] + conf.ctl_button_border_size, dock_border_area[2] - conf.ctl_button_border_size * 2, dock_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color, dock_border_area)
    pg.draw.rect(sur, conf.ui_background_color, dock_area)

    dock_text_area = font.get_rect("Dock to base [r]", size=12)
    dock_text_area = (dock_area[0] + dock_area[2] // 2 - dock_text_area[2] // 2, dock_area[1] + dock_area[3] // 2 - dock_text_area[3] // 2)

    font.render_to(sur, dock_text_area, "Dock to base [r]", conf.ui_foreground_color, size=12)

    # materials

    mats = data.get("materials")
    if not mats == None:
        # materials tag

        tag_area = [panel_render_area[0] + 40, dock_border_area[1] + 50]

        font.render_to(sur, tag_area, "stored materials:", conf.ui_foreground_faded_color, size=10)

        # materials

        tag_area[1] += 15
        font.render_to(sur, tag_area, f" - stone: {mats[1]}", conf.ui_foreground_faded_color, size=10)

        tag_area[1] += 15
        font.render_to(sur, tag_area, f" - oxy: {mats[2]}", conf.ui_foreground_faded_color, size=10)

        tag_area[1] += 15
        font.render_to(sur, tag_area, f" - goal: {mats[3]}", conf.ui_foreground_faded_color, size=10)

def ctl_build_renderer(e, sur):
    if not ui_mode == 1:
        return

    render_area = cam.translate_ui(e["ui_trans"])
    panel_render_area = (render_area[0] + conf.ctl_border_size, render_area[1] + conf.ctl_border_size, render_area[2] - conf.ctl_border_size * 2, render_area[3] - conf.ctl_border_size * 2)

    # border and panel background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, panel_render_area)

    # extender

    extender_border_area = cam.translate_ui(e["extender_ui_trans"])
    extender_area = (extender_border_area[0] + conf.ctl_button_border_size, extender_border_area[1] + conf.ctl_button_border_size, extender_border_area[2] - conf.ctl_button_border_size * 2, extender_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 0 else conf.ui_foreground_faded_color, extender_border_area)
    pg.draw.rect(sur, conf.ui_background_color, extender_area)

    extender_text_area = font.get_rect("Signal", size=12)
    extender_text_area = (extender_area[0] + extender_area[2] // 2 - extender_text_area[2] // 2, extender_area[1] + extender_area[3] // 2 - extender_text_area[3])

    font.render_to(sur, extender_text_area, "Signal", conf.ui_foreground_color, size=12)

    extender_text_area = font.get_rect("Extender", size=12)
    extender_text_area = (extender_area[0] + extender_area[2] // 2 - extender_text_area[2] // 2, extender_area[1] + extender_area[3] // 2)

    font.render_to(sur, extender_text_area, "Extender", conf.ui_foreground_color, size=12)

    # scanner

    scanner_border_area = cam.translate_ui(e["scanner_ui_trans"])
    scanner_area = (scanner_border_area[0] + conf.ctl_button_border_size, scanner_border_area[1] + conf.ctl_button_border_size, scanner_border_area[2] - conf.ctl_button_border_size * 2, scanner_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 1 else conf.ui_foreground_faded_color, scanner_border_area)
    pg.draw.rect(sur, conf.ui_background_color, scanner_area)

    scanner_text_area = font.get_rect("Proximity", size=12)
    scanner_text_area = (scanner_area[0] + scanner_area[2] // 2 - scanner_text_area[2] // 2, scanner_area[1] + scanner_area[3] // 2 - scanner_text_area[3])

    font.render_to(sur, scanner_text_area, "Proximity", conf.ui_foreground_color, size=12)

    scanner_text_area = font.get_rect("Scanner", size=12)
    scanner_text_area = (scanner_area[0] + scanner_area[2] // 2 - scanner_text_area[2] // 2, scanner_area[1] + scanner_area[3] // 2)

    font.render_to(sur, scanner_text_area, "Scanner", conf.ui_foreground_color, size=12)

    # detector

    detector_border_area = cam.translate_ui(e["detector_ui_trans"])
    detector_area = (detector_border_area[0] + conf.ctl_button_border_size, detector_border_area[1] + conf.ctl_button_border_size, detector_border_area[2] - conf.ctl_button_border_size * 2, detector_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 2 else conf.ui_foreground_faded_color, detector_border_area)
    pg.draw.rect(sur, conf.ui_background_color, detector_area)

    detector_text_area = font.get_rect("Long Range", size=12)
    detector_text_area = (detector_area[0] + detector_area[2] // 2 - detector_text_area[2] // 2, detector_area[1] + detector_area[3] // 2 - detector_text_area[3])

    font.render_to(sur, detector_text_area, "Long Range", conf.ui_foreground_color, size=12)

    detector_text_area = font.get_rect("Detector", size=12)
    detector_text_area = (detector_area[0] + detector_area[2] // 2 - detector_text_area[2] // 2, detector_area[1] + detector_area[3] // 2)

    font.render_to(sur, detector_text_area, "Detector", conf.ui_foreground_color, size=12)

# game timer renderer

def timer_renderer(e, sur):
    if not ui_mode == 0:
        return

    render_area = cam.translate_ui(e["ui_trans"])

    timer_render_area = (render_area[0] + conf.timer_border_size, render_area[1] + conf.timer_border_size, render_area[2] - conf.timer_border_size * 2, render_area[3] - conf.timer_border_size * 2)

    # border and timer background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, timer_render_area)

    # draw eta

    eta_text = f"{int(e['eta'] // 60):0=2}:{int(e['eta'] % 60):0=2}"
    
    eta_area = font.get_rect(eta_text, size=22)
    eta_area = (timer_render_area[0] + 25, timer_render_area[1] + 30 - eta_area[3] // 2)

    font.render_to(sur, eta_area, eta_text, conf.ui_foreground_color, size=22)

    eta_tag_area = font.get_rect("power eta:", size=10)
    eta_tag_area = (timer_render_area[0] + 65 - eta_tag_area[2] // 2, timer_render_area[1] + 10 - eta_tag_area[3] // 2)

    font.render_to(sur, eta_tag_area, "power eta:", conf.ui_foreground_color, size=10)

    # draw goal mat

    tag_text = f"{int(e['goal_mat_count'])}"
    
    tag_area = font.get_rect(tag_text, size=20)
    tag_area = (timer_render_area[0] + 158 - tag_area[2] // 2, timer_render_area[1] + 30 - tag_area[3] // 2)

    font.render_to(sur, tag_area, tag_text, conf.ui_foreground_color, size=20)

    tag_tag_area = font.get_rect("goal:", size=10)
    tag_tag_area = (timer_render_area[0] + 158 - tag_tag_area[2] // 2, timer_render_area[1] + 10 - tag_tag_area[3] // 2)

    font.render_to(sur, tag_tag_area, "goal:", conf.ui_foreground_color, size=10)

# dev frametime display

def frametime_renderer(e, sur):
    render_area = cam.translate_ui(e["ui_trans"])

    font.render_to(sur, render_area, f"Frame Time: {round(ren.delta_time * 1000, 1)}ms CPU Time: {round(ren.cpu_time * 1000, 1)}ms ({round(ren.cpu_time / ren.delta_time * 100, 1)}% Util)", conf.ui_foreground_faded_color, size=12)

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

# generic text renderer

def text_renderer(e, sur):
    render_area = cam.translate_ui(e["ui_trans"])

    text_string = e["text"]
    text_size = e["text_size"]

    text_area = font.get_rect(text_string, size=text_size)

    text_area = (render_area[0] + render_area[2] // 2 - text_area[2] // 2, render_area[1] + render_area[3] // 2 - text_area[3] // 2)
    font.render_to(sur, text_area, text_string, e["text_color"], size=text_size)