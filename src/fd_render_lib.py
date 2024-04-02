import pygame as pg
import pygame.freetype as freetype
import pygame.gfxdraw as gfx
import time
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

def struct_renderer(e, sur):
    trans = e["transform"]
    render_area = cam.translate(trans[0], trans[1])

    # pg.draw.polygon(sur, conf.struct_colors[e["struct_type"]], ((render_area[0] + render_area[2] // 2, render_area[1]), (render_area[0], render_area[1] + render_area[3]), (render_area[0] + render_area[2], render_area[1] + render_area[3])))
    pg.draw.rect(sur, conf.struct_colors[e["struct_type"]], render_area)

def struct_early_renderer(e, sur):
    trans = e["transform"]

    if e["struct_type"] == 1:
        p1 = cam.translate_position(trans[0])
        p2 = cam.translate_position(e["linked_trans"])

        pg.draw.line(sur, (64, 64, 64), p1, p2, 10)

def struct_ghost_renderer(e, sur):
    if not ui_mode == 1:
        return

    trans = e["transform"]
    render_area = cam.translate(trans[0], trans[1])

    # pg.draw.polygon(sur, (127, 127, 127), ((render_area[0] + render_area[2] // 2, render_area[1]), (render_area[0], render_area[1] + render_area[3]), (render_area[0] + render_area[2], render_area[1] + render_area[3])))
    col = conf.struct_colors[e["struct_index"]]
    pg.draw.rect(sur, (col[0] // 2, col[1] // 2, col[2] // 2), render_area)

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
    panel_render_area = [render_area[0] + conf.ctl_border_size, render_area[1] + conf.ctl_border_size, render_area[2] - conf.ctl_border_size * 2, render_area[3] - conf.ctl_border_size * 2]

    # border and panel background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, panel_render_area)

    panel_render_area[2] -= conf.ctl_selected_tag_margin

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

    if data["lost_signal"]:
        return

    if data["type"] == 0:
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

        mat_start_y = dock_border_area[1]

        pg.draw.rect(sur, conf.ui_foreground_color, dock_border_area)
        pg.draw.rect(sur, conf.ui_background_color, dock_area)

        dock_text_area = font.get_rect("Dock to base [r]", size=12)
        dock_text_area = (dock_area[0] + dock_area[2] // 2 - dock_text_area[2] // 2, dock_area[1] + dock_area[3] // 2 - dock_text_area[3] // 2)

        font.render_to(sur, dock_text_area, "Dock to base [r]", conf.ui_foreground_color, size=12)

    else:
        # depart button

        depart_border_area = cam.translate_ui(e["depart_ui_trans"])
        depart_area = (depart_border_area[0] + conf.ctl_button_border_size, depart_border_area[1] + conf.ctl_button_border_size, depart_border_area[2] - conf.ctl_button_border_size * 2, depart_border_area[3] - conf.ctl_button_border_size * 2)

        mat_start_y = depart_border_area[1]

        can_depart = e["selected_entity"]["units_undocked"] == 0

        pg.draw.rect(sur, conf.ui_foreground_color if can_depart else conf.ui_foreground_faded_color, depart_border_area)
        pg.draw.rect(sur, conf.ui_background_color, depart_area)

        depart_text_area = font.get_rect("Depart now.", size=12)
        depart_text_area = (depart_area[0] + depart_area[2] // 2 - depart_text_area[2] // 2, depart_area[1] + depart_area[3] // 2 - depart_text_area[3] // 2)

        font.render_to(sur, depart_text_area, "Depart now.", conf.ui_foreground_color if can_depart else conf.ui_foreground_faded_color, size=12)

    # materials

    if data["type"] == 0 or data["type"] == 1:
        mats = data.get("materials")
        if not mats == None:
            # materials tag

            tag_area = [panel_render_area[0] + 40, mat_start_y + 50]

            font.render_to(sur, tag_area, "stored materials:", conf.ui_foreground_faded_color, size=10)

            # materials

            tag_area[1] += 15
            font.render_to(sur, tag_area, f" - stone: {mats[1]}", conf.ui_foreground_faded_color, size=10)

            tag_area[1] += 15
            font.render_to(sur, tag_area, f" - oxy: {mats[2]}", conf.ui_foreground_faded_color, size=10)

            tag_area[1] += 15
            font.render_to(sur, tag_area, f" - goal: {mats[3]}", conf.ui_foreground_faded_color, size=10)
    
    pg.draw.line(sur, conf.ui_foreground_faded_color, (panel_render_area[0] + panel_render_area[2], panel_render_area[1]), (panel_render_area[0] + panel_render_area[2], panel_render_area[1] + panel_render_area[3]), conf.ctl_selected_tag_border_size)

    for i, select_tag in enumerate(('1', '2', '3', '4', '5', '6', 'B')):
        tag_area = font.get_rect(select_tag, size=14)
        tag_area = [panel_render_area[0] + panel_render_area[2] + 8 - tag_area[0] // 2, panel_render_area[1] + 20 + (panel_render_area[3] - 40) // 6 * i - tag_area[1] // 2]

        color_div = 1 if data["selected_index"] == i else 2
        color = (conf.unit_colors[i][0] // color_div, conf.unit_colors[i][1] // color_div, conf.unit_colors[i][2] // color_div)

        font.render_to(sur, tag_area, select_tag, color, size=14)

def ctl_build_renderer(e, sur):
    if not ui_mode == 1:
        return

    render_area = cam.translate_ui(e["ui_trans"])
    panel_render_area = (render_area[0] + conf.ctl_border_size, render_area[1] + conf.ctl_border_size, render_area[2] - conf.ctl_border_size * 2, render_area[3] - conf.ctl_border_size * 2)

    # border and panel background
    pg.draw.rect(sur, conf.ui_foreground_color, render_area)
    pg.draw.rect(sur, conf.ui_background_color, panel_render_area)

    # transceiver

    transceiver_border_area = cam.translate_ui(e["transceiver_ui_trans"])
    transceiver_area = (transceiver_border_area[0] + conf.ctl_button_border_size, transceiver_border_area[1] + conf.ctl_button_border_size, transceiver_border_area[2] - conf.ctl_button_border_size * 2, transceiver_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 0 else conf.ui_foreground_faded_color, transceiver_border_area)
    pg.draw.rect(sur, conf.ui_background_color, transceiver_area)

    transceiver_text_area = font.get_rect("Signal", size=12)
    transceiver_text_area = (transceiver_area[0] + transceiver_area[2] // 2 - transceiver_text_area[2] // 2, transceiver_area[1] + transceiver_area[3] // 2 - 8 - transceiver_text_area[3])

    font.render_to(sur, transceiver_text_area, "Signal", conf.ui_foreground_color, size=12)

    transceiver_text_area = font.get_rect("Transceiver", size=12)
    transceiver_text_area = (transceiver_area[0] + transceiver_area[2] // 2 - transceiver_text_area[2] // 2, transceiver_area[1] + transceiver_area[3] // 2 - 8)

    font.render_to(sur, transceiver_text_area, "Transceiver", conf.ui_foreground_color, size=12)

    transceiver_text_area = font.get_rect(f"oxy cost: {conf.struct_build_costs[0][0]}", size=12)
    transceiver_text_area = (transceiver_area[0] + transceiver_area[2] // 2 - transceiver_text_area[2] // 2, transceiver_area[1] + transceiver_area[3] // 2 + 10)

    font.render_to(sur, transceiver_text_area, f"oxy cost: {conf.struct_build_costs[0][0]}", conf.ui_foreground_faded_color, size=12)

    # substation

    substation_border_area = cam.translate_ui(e["substation_ui_trans"])
    substation_area = (substation_border_area[0] + conf.ctl_button_border_size, substation_border_area[1] + conf.ctl_button_border_size, substation_border_area[2] - conf.ctl_button_border_size * 2, substation_border_area[3] - conf.ctl_button_border_size * 2)

    pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 1 else conf.ui_foreground_faded_color, substation_border_area)
    pg.draw.rect(sur, conf.ui_background_color, substation_area)

    substation_text_area = font.get_rect("Pipeline", size=12)
    substation_text_area = (substation_area[0] + substation_area[2] // 2 - substation_text_area[2] // 2, substation_area[1] + substation_area[3] // 2 - 8 - substation_text_area[3])

    font.render_to(sur, substation_text_area, "Pipeline", conf.ui_foreground_color, size=12)

    substation_text_area = font.get_rect("Substation", size=12)
    substation_text_area = (substation_area[0] + substation_area[2] // 2 - substation_text_area[2] // 2, substation_area[1] + substation_area[3] // 2 - 8)

    font.render_to(sur, substation_text_area, "Substation", conf.ui_foreground_color, size=12)

    substation_text_area = font.get_rect(f"oxy cost: {conf.struct_build_costs[1][0]}", size=12)
    substation_text_area = (substation_area[0] + substation_area[2] // 2 - substation_text_area[2] // 2, substation_area[1] + substation_area[3] // 2 + 10)

    font.render_to(sur, substation_text_area, f"oxy cost: {conf.struct_build_costs[1][0]}", conf.ui_foreground_faded_color, size=12)

    # detector

    # detector_border_area = cam.translate_ui(e["detector_ui_trans"])
    # detector_area = (detector_border_area[0] + conf.ctl_button_border_size, detector_border_area[1] + conf.ctl_button_border_size, detector_border_area[2] - conf.ctl_button_border_size * 2, detector_border_area[3] - conf.ctl_button_border_size * 2)
# 
    # pg.draw.rect(sur, conf.ui_foreground_color if e["selected_index"] == 2 else conf.ui_foreground_faded_color, detector_border_area)
    # pg.draw.rect(sur, conf.ui_background_color, detector_area)
# 
    # detector_text_area = font.get_rect("Long Range", size=12)
    # detector_text_area = (detector_area[0] + detector_area[2] // 2 - detector_text_area[2] // 2, detector_area[1] + detector_area[3] // 2 - detector_text_area[3])
# 
    # font.render_to(sur, detector_text_area, "Long Range", conf.ui_foreground_color, size=12)
# 
    # detector_text_area = font.get_rect("Detector", size=12)
    # detector_text_area = (detector_area[0] + detector_area[2] // 2 - detector_text_area[2] // 2, detector_area[1] + detector_area[3] // 2)
# 
    # font.render_to(sur, detector_text_area, "Detector", conf.ui_foreground_color, size=12)

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
    eta_area = (timer_render_area[0] + timer_render_area[2] // 2 - eta_area[2] // 2, timer_render_area[1] + 30 - eta_area[3] // 2)

    font.render_to(sur, eta_area, eta_text, conf.ui_foreground_color, size=22)

    eta_tag_area = font.get_rect("eta:", size=10)
    eta_tag_area = (timer_render_area[0] + timer_render_area[2] // 2 - eta_tag_area[2] // 2, timer_render_area[1] + 10 - eta_tag_area[3] // 2)

    font.render_to(sur, eta_tag_area, "eta:", conf.ui_foreground_color, size=10)

    # draw goal mat

    count = int(e['goal_mat_count'])
    if count < 1000:
        tag_text = f"{count}"
    elif count < 100 * 1000:
        tag_text = f"{round(count / 1000, 1)}k"
    else:
        tag_text = f"{round(count / (1000 * 1000), 1)}M"
    
    goal_area = font.get_rect(tag_text, size=16)
    goal_area = (timer_render_area[0] + timer_render_area[2] // 2 + 95 - goal_area[2] // 2, timer_render_area[1] + 30 - goal_area[3] // 2)

    font.render_to(sur, goal_area, tag_text, conf.ui_foreground_color, size=16)

    goal_tag_area = font.get_rect("goal:", size=10)
    goal_tag_area = (timer_render_area[0] + timer_render_area[2] // 2 + 95 - goal_tag_area[2] // 2, timer_render_area[1] + 10 - goal_tag_area[3] // 2)

    font.render_to(sur, goal_tag_area, "goal:", conf.ui_foreground_color, size=10)

    # draw power usage

    count = int(e['power_usage'])
    if count < 1000:
        tag_text = f"{count}"
    elif count < 100 * 1000:
        tag_text = f"{round(count / 1000, 1)}k"
    else:
        tag_text = f"{round(count / (1000 * 1000), 1)}M"

    usage_area = font.get_rect(tag_text, size=16)
    usage_area = (timer_render_area[0] + timer_render_area[2] // 2 - 95 - usage_area[2] // 2, timer_render_area[1] + 30 - usage_area[3] // 2)

    font.render_to(sur, usage_area, tag_text, conf.ui_foreground_color, size=16)

    usage_tag_area = font.get_rect("opm:", size=10)
    usage_tag_area = (timer_render_area[0] + timer_render_area[2] // 2 - 95 - usage_tag_area[2] // 2, timer_render_area[1] + 10 - usage_tag_area[3] // 2)

    font.render_to(sur, usage_tag_area, "opm:", conf.ui_foreground_color, size=10)

    # draw warning outline on low time

    if not e["eta"] < conf.timer_warn_at_time:
        return

    if int(time.time() * 4) % 2 == 1:
        alpha = 200
    else:
        alpha = 127

    for i in range(conf.timer_outline_width):
        outline_render_area = (render_area[0] - conf.timer_outline_margin - i, render_area[1] - conf.timer_outline_margin - i, render_area[2] + conf.timer_outline_margin * 2 + 2 * i, render_area[3] + conf.timer_outline_margin * 2 + 2 * i)

        gfx.rectangle(sur, outline_render_area, (255, 0, 0, alpha))

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

def left_aligned_text_renderer(e, sur):
    render_area = cam.translate_ui(e["ui_trans"])

    text_string = e["text"]
    text_size = e["text_size"]

    text_area = font.get_rect(text_string, size=text_size)

    text_area = (render_area[0] + render_area[2] // 2, render_area[1] + render_area[3] // 2 - text_area[3] // 2)
    font.render_to(sur, text_area, text_string, e["text_color"], size=text_size)

# game over renderers

def power_lost_anim_renderer(t, sur):
    center = (sur.get_width() // 2, sur.get_height() // 2)

    if t < 6:
        pass
    elif t > 6 and t < 7:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected.", conf.ui_foreground_color)

    elif t > 7 and t < 10:
        if int(t * 7) % 4 == 0:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... /", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 1:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... -", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 2:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... \\", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 3:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... |", conf.ui_foreground_color)
        
    elif t > 10 and t < 11:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... done", conf.ui_foreground_color)
    elif t > 11 and t < 14:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... done", conf.ui_foreground_color)
        
        if int(t * 7) % 4 == 0:
            font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission failed. Gathering logs... /", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 1:
            font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission failed. Gathering logs... -", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 2:
            font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission failed. Gathering logs... \\", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 3:
            font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission failed. Gathering logs... |", conf.ui_foreground_color)
    elif t > 14 and t < 15:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Power loss detected. Switching to backup batteries... done", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission failed. Gathering logs... done", conf.ui_foreground_color)
    else:
        return True
    
    return False

def departed_anim_renderer(t, sur):
    center = (sur.get_width() // 2, sur.get_height() // 2)

    if t < 1:
        pass
    elif t > 1 and t < 3:
        if int(t * 7) % 4 == 0:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... /", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 1:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... -", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 2:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... \\", conf.ui_foreground_color)
        elif int(t * 7) % 4 == 3:
            font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... |", conf.ui_foreground_color)
    elif t > 3 and t < 4:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... done", conf.ui_foreground_color)
    elif t > 4 and t < 5.5:
        font.render_to(sur, (center[0] - 400, center[1] - 12), "> Departing from location... done", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] + 14), "> Mission success!", conf.ui_foreground_color)
    else:
        return True

    return False

# how-to manual content renderer

def manual_renderer(page, sur):
    center = (sur.get_width() // 2, sur.get_height() // 2)

    if page == 0:
        font.render_to(sur, (center[0] - 400, center[1] - 220), f"Welcome new worker on board your new submersible.", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 20), f"As the pilot of your new vessel, your mission is", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 20), f"to gather as much material codenamed \"goal\"", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 3 + 20), f"as possible in a hostile and remote enviroment.", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 112), f"Also because of the distance from any infrastructure,", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 112), f"to power your vessel you also have to collect enough", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 3 + 112), f"material codenamed \"oxy\" as fuel.", conf.ui_foreground_color)
    elif page == 1:
        font.render_to(sur, (center[0] - 400, center[1] - 340), f"To work in this hostile enviroment you can use your Units.", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 + 20), f"Point and click your right mouse button to", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 * 2 + 20), f"move your unit to the pointed location", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 + 88), f"To mine a piece of a deposit, hold and drag with", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 * 2 + 88), f"your left mouse button over the area for mining", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 340 + 176), f"hold down shift to append tasks into a queue", conf.ui_foreground_color)
    elif page == 2:
        font.render_to(sur, (center[0] - 400, center[1] - 340), f"Now that you have units filled with materials,", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24), f"we need to transfer them to a secure location", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 + 44), f"To dock and transfer units materials press r", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 * 2 + 44), f"your unit will move to the closest dockable structure", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 340 + 24 + 112), f"Again you can append this action when holding shift", conf.ui_foreground_color)
    elif page == 3:
        font.render_to(sur, (center[0] - 400, center[1] - 220), f"== Don't forget about time and your reserves! ==", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 20), f"Keep checking your timer on top to see if", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 20), f"you are running out of time, that when it runs out", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 3 + 20), f"you lose power and fail your mission.", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 112), f"To increase your time, supply your vessel with oxy", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 176), f"opm (oxy per minute) - how much oxy is consumed per minute", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 176), f"eta - estimated time until loss of power with your", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 3 + 176), f"      current oxy usage and oxy reserves in vessel", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 4 + 176), f"goal - amount of goal secured in your vessel", conf.ui_foreground_color)
    elif page == 4:
        font.render_to(sur, (center[0] - 400, center[1] - 220), f"Your units can also build small structures.", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 20), f"This can be helpful for extending your reach to farther", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 20), f"parts of your location as units have only a limited", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 3 + 20), f"signal range which can be extended using structures", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 112), f"To open units build menu press e in-game", conf.ui_foreground_color)
    elif page == 5:
        font.render_to(sur, (center[0] - 400, center[1] - 220), f"To successfully end your mission, you must depart with", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24), f"your vessel", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 44), f"After you transfered all wanted materials from your units,", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 44), f"press b to select your vessel and press the depart button", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 + 112), f"== To depart ALL units have to be docked to your vessel! ==", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 220 + 24 * 2 + 112), f"You can recall your units to your vessel using alt+r", conf.ui_foreground_color)
    elif page == 6:
        font.render_to(sur, (center[0] - 400, center[1] - 300), f"Now that you know the gist of it, here are the full controls", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 + 20), f"w,a,s,d - to move your camera", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 2 + 20), f"1,2,3,4,5,6 - switch between your units", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 3 + 20), f"b - switch to your vessel", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 4 + 20), f"hold shift while switching to prevent focusing your camera", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 + 136), f"the following controls control the selected unit", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 + 176), f"left mouse button - mark area for mining", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 2 + 176), f"right mouse button - move to location", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 3 + 176), f"r - dock to closest dockable structure", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 4 + 176), f"alt+r - dock to vessel (required for departing)", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 5 + 176), f"e - open build menu", conf.ui_foreground_color)
        font.render_to(sur, (center[0] - 400, center[1] - 300 + 24 * 6 + 176), f"hold shift to append tasks on each other", conf.ui_foreground_color)

        font.render_to(sur, (center[0] - 400, center[1] - 300 + 380), f"good luck!", conf.ui_foreground_color)