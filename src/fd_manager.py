import pygame as pg
import random
import time

import src.fd_render as ren
import src.fd_render_lib as rlib

import src.fd_camera as cam
import src.fd_level as lvl
import src.fd_entity as en
import src.fd_units as un
import src.fd_astar as astar
import src.fd_notif as nls
import src.fd_config as conf
import src.fd_control_panel as ctl
import src.fd_timer as ti
import src.fd_struct as st
import src.fd_signal as sig

# == Far Depths Main Event Loop ==

def in_game_loop():
    # reset globals

    un.game_over_trigged = 0
    rlib.ui_mode = 0
    st.next_struct_index = 1
    un.total_mined = [None, 0, 0, 0]

    cam.set_camera((0, 0))

    # generate level

    pg.display.set_caption("Far Depths - Traveling to a forbidden location")

    lvl.gen_level(None, 25)

    pg.display.set_caption("Far Depths - Scanning and Mining" if random.randint(0, 100) > 40 else random.choice(conf.secret_titles)) 

    # dev options

    if conf.dev_frametimes:
        frametime_display = en.create_entity("frametime_display", {
            "ui_trans": [
                (0, 0),
                (0, 0),
                (100, 20)
            ],

            "on_ui_frame": rlib.frametime_renderer,
        })

    # generate base

    base_pos = (conf.level_size[0] // 2, conf.level_size[1] // 2)
    base_world_pos = lvl.grid_to_world_space(base_pos)

    base = en.create_entity("player_base", {
        "transform": [ # base at world root
            (base_world_pos[0] + 30, base_world_pos[1] + 20),
            (60, 40)
        ],

        "on_frame": rlib.rect_renderer,
        "rect_color": (254, 254, 254),

        "tick": un.base_tick,

        # base components

        "stored_materials": [
            None, # air (unused)
            0, # rock
            conf.initial_base_oxy_count, # oxy
            0, # goal
        ],

        "power_usage": 1, # initial power usage
        "busy_generating": 0,

        "units_undocked": 0,

        "pretty_name": (4, "Base (You)")
    })

    lvl.set_circle(base_pos, 100, 0) # clear spawn location
    lvl.set_pixel_navgrid(base_pos, 1) # initial navgrid origin
    lvl.unfog_area([ base_pos ], 64) # initial unfoged area

    sig.setup_ranges(base_pos)

    for i, unit in enumerate([ (0, -1), (1, -1), (2, -1), (0, 2), (1, 2), (2, 2) ], 1):
        en.create_entity(f"unit_{i}", {
            "transform": [
                None, # set on ticks
                (15, 15) 
            ],

            "grid_trans": (base_pos[0] + unit[0], base_pos[1] + unit[1]),
            "base_dock_pos": (base_pos[0] + unit[0], base_pos[1] + unit[1]),

            "on_frame": rlib.rect_renderer,
            "rect_color": conf.unit_colors[i - 1],

            "tick": un.unit_tick,

            # unit components

            "unit_index": i,
            "pretty_name": f"Unit {i}",

            "stored_materials": [
                None, # air (unused)
                0, # rock
                0, # oxy
                0, # goal
            ],
            "transfer_size": 0,

            "task_queue": [],
            "mining_queue": set(),

            "already_idle": True,

            "active_transmitter": sig.find_signal((base_pos[0] + unit[0], base_pos[1] + unit[1])),
            "auto_return": False,

            "is_docked": True,
        })

        base["power_usage"] += 2

    # setup game loop locals

    is_dragging = False
    is_pressed = False
    drag_start_pos = None

    is_right_pressed = False
    dock_base_pressed = False

    cam_x = 0
    cam_y = 0

    selected_unit = 1
    selected_entity = en.get_entity(f"unit_{selected_unit}")
    is_selected_unit = True

    nls.setup_nls()
    ctl.setup_ctl_panel()
    ti.setup_timer()
    st.setup_struct_build_ghost()

    start_game_time = time.time()

    while True:
        click_consumed = False

        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.MOUSEBUTTONDOWN:
                click_consumed = en.click_event((e.dict["pos"], e.dict["button"]))
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)
                lvl.resize_level_preren((e.dict["x"], e.dict["y"]))

        # user input processing

        keys = pg.key.get_pressed()

        is_shift = keys[pg.K_LSHIFT]

        old_cam = (cam_x, cam_y)

        if keys[pg.K_w]:
            cam_y -= conf.cam_speed * ren.delta_time
            cam.set_camera((int(cam_x), int(cam_y)))
        
        if keys[pg.K_s]:
            cam_y += conf.cam_speed * ren.delta_time
            cam.set_camera((int(cam_x), int(cam_y)))
        
        if keys[pg.K_d]:
            cam_x += conf.cam_speed * ren.delta_time
            cam.set_camera((int(cam_x), int(cam_y)))
        
        if keys[pg.K_a]:
            cam_x -= conf.cam_speed * ren.delta_time
            cam.set_camera((int(cam_x), int(cam_y)))

        if click_consumed:
            is_pressed = True

        if rlib.ui_mode == 0: # normal mode
            if keys[pg.K_1]:
                selected_unit = 1
                is_selected_unit = True
            if keys[pg.K_2]:
                selected_unit = 2
                is_selected_unit = True
            if keys[pg.K_3]:
                selected_unit = 3
                is_selected_unit = True
            if keys[pg.K_4]:
                selected_unit = 4
                is_selected_unit = True
            if keys[pg.K_5]:
                selected_unit = 5
                is_selected_unit = True
            if keys[pg.K_6]:
                selected_unit = 6
                is_selected_unit = True

            if keys[pg.K_b]:
                selected_unit = 0
                is_selected_unit = False

            if is_selected_unit:
                selected_entity = en.get_entity(f"unit_{selected_unit}")
                ctl.set_selected(selected_entity)
            else:
                selected_entity = en.get_entity(f"player_base")
                ctl.set_selected(selected_entity)

            if (keys[pg.K_1] or keys[pg.K_2] or keys[pg.K_3] or keys[pg.K_4] or keys[pg.K_5] or keys[pg.K_6] or keys[pg.K_b]) and not is_shift:
                cam_x, cam_y = selected_entity["transform"][0]
                cam.set_camera((int(cam_x), int(cam_y)))

            if pg.mouse.get_pressed()[2] and not is_right_pressed and is_selected_unit and un.has_signal(selected_entity):
                is_right_pressed = True

                mouse_pos = pg.mouse.get_pos()
                wm_pos = cam.inverse_translate(mouse_pos)
                gm_pos = lvl.world_to_grid_space(wm_pos)

                un.add_move_task(selected_entity, lvl.inbounds(gm_pos), is_shift)
            elif not pg.mouse.get_pressed()[2]:
                is_right_pressed = False

            if keys[pg.K_e] and is_selected_unit:
                rlib.ui_mode = 1

            if keys[pg.K_r] and not dock_base_pressed and is_selected_unit and un.has_signal(selected_entity):
                dock_base_pressed = True
                un.add_dock_task(selected_entity, is_shift, keys[pg.K_LALT])
            elif not keys[pg.K_r]:
                dock_base_pressed = False

            # drag processing

            # not None if currently dragging
            drag_area = None

            # not None if finished dragging this frame
            final_drag_area = None

            if not is_dragging and pg.mouse.get_pressed()[0] and not is_pressed and is_selected_unit:
                # started dragging

                is_dragging = True
                is_pressed = True

                drag_start_pos = pg.mouse.get_pos()

            elif is_dragging and not pg.mouse.get_pressed()[0]:
                # stopped dragging

                is_dragging = False

                final_drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))
                drag_start_pos = None

            if is_dragging:
                drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))

            # mark area for mining
            if not final_drag_area == None and un.has_signal(selected_entity):
                w_drag_area = (cam.inverse_translate(final_drag_area[0]), cam.inverse_translate(final_drag_area[1]))
                g_drag_area = (lvl.inbounds(lvl.world_to_grid_space(w_drag_area[0])), lvl.inbounds(lvl.world_to_grid_space(w_drag_area[1])))

                mining_queue = un.create_mining_queue(g_drag_area)

                if not len(mining_queue) == 0:
                    # lvl.set_pixels_for_mining(mining_queue)
                    un.add_mining_task(selected_entity, mining_queue, is_shift)
        
        elif rlib.ui_mode == 1: # unit build mode
            if keys[pg.K_ESCAPE]:
                rlib.ui_mode = 0

            if not click_consumed and not is_pressed and pg.mouse.get_pressed()[0] and un.has_signal(selected_entity):
                w_struct_loc = cam.inverse_translate(pg.mouse.get_pos())
                g_struct_loc = lvl.world_to_grid_space(w_struct_loc)

                is_pressed = True

                un.add_build_task(selected_entity, g_struct_loc, en.get_entity("build_select")["selected_index"], is_shift)

                rlib.ui_mode = 0

        if is_pressed and not pg.mouse.get_pressed()[0]:
            is_pressed = False

        cam_offset = (cam_x - old_cam[0], cam_y - old_cam[1])

        if not cam_offset[0] == 0 or not cam_offset[1] == 0:
            lvl.invalidate_level(cam_offset)

        # main game update

        en.tick()

        # check for game over

        if not un.game_over_trigged == 0:
            un.game_over_stats.clear()

            un.game_over_stats.append(en.get_entity("timer_ui")["eta"])
            un.game_over_stats.append(time.time() - start_game_time)
            un.game_over_stats.append(base["stored_materials"])
            un.game_over_stats.append(un.total_mined)

            en.reset()
            return 2

        # render frame

        sur = ren.get_surface()

        lvl.render_level(sur)
        en.render_entities(sur)
        lvl.render_fow(sur)

        if not drag_area == None:
            pg.draw.rect(sur, (64, 255, 64), (drag_area[0][0], drag_area[0][1], drag_area[1][0] - drag_area[0][0], drag_area[1][1] - drag_area[0][1]))

        en.render_ui(sur)

        ren.submit()

# == main menu ==

menu_state = 0

def start_game(e, click):
    if not cam.is_click_on_ui(e["ui_trans"], click):
        return

    global menu_state
    menu_state = 1

def show_how_to(e, click):
    if not cam.is_click_on_ui(e["ui_trans"], click):
        return

    global menu_state
    menu_state = 3

def menu_loop():
    pg.display.set_caption("Far Depths - Chiling at central")

    global menu_state
    menu_state = 0

    title = en.create_entity("menu_title", {
        "ui_trans": [
            (2, 2), # anchor to center
            (-250, -250),
            (250, -170)
        ],

        "on_ui_frame": rlib.title_renderer,
    })

    start_button = en.create_entity("start_button", {
        "ui_trans": [
            (2, 2),
            (-110, -50),
            (110, -5)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": start_game,
        "button_border_size": 5,
        "button_text": "Undock and Start",
    })

    howto_button = en.create_entity("howto_button", {
        "ui_trans": [
            (2, 2),
            (-110, 5),
            (110, 50)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": show_how_to,
        "button_border_size": 5,
        "button_text": "How to Play",
    })

    quit_text = en.create_entity("quit_text", {
        "ui_trans": [
            (2, 2),
            (150, 150),
            (-150, 185)
        ],

        "on_ui_frame": rlib.text_renderer,
        "text": "To quit close the window :p",
        "text_size": 12,
        "text_color": conf.ui_foreground_faded_color,
    })

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.MOUSEBUTTONDOWN:
                en.click_event((e.dict["pos"], e.dict["button"]))
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        if not menu_state == 0:
            break

        sur = ren.get_surface()
        sur.fill(conf.ui_background_color)

        en.render_ui(sur)
        ren.submit()

    en.reset()

    return menu_state # switch to in-game loop

# == game stats loop ==

return_to_menu = True

def stats_return_to_menu(e, click):
    global return_to_menu
    return_to_menu = cam.is_click_on_ui(e['ui_trans'], click)

def suffix_count(count):
    if count < 1000:
        return f"{count}"
    elif count < 1000 * 1000:
        return f"{round(count / 1000, 2)}k"
    else:
        return f"{round(count / (1000 * 1000), 2)}M"

def format_time(t):
    if t < 3600:
        return f"{int(t // 60):0=2}:{int(t % 60):0=2}"
    else:
        return f"{int(t // (60 * 60))}:{int((t // 60) % 60):0=2}:{int(t % 60):0=2}"

def game_over_loop():
    # play game over animation

    start_time = time.time()

    if un.game_over_trigged == 1:
        while not time.time() - start_time > 5:
            # events
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    return None
                if e.type == pg.WINDOWRESIZED:
                    ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

            sur = ren.get_surface()
            sur.fill((0, 0, 0))

            ren.submit()
        
        while True:
            # events
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    return None
                if e.type == pg.WINDOWRESIZED:
                    ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

            t = time.time() - start_time

            sur = ren.get_surface()

            power_up_mult = min((t - 5) * 2, 1)
            sur.fill((int(conf.ui_background_color[0] * power_up_mult), int(conf.ui_background_color[1] * power_up_mult), int(conf.ui_background_color[2] * power_up_mult)))

            if rlib.power_lost_anim_renderer(t, sur):
                break

            ren.submit()

    elif un.game_over_trigged == 2:
        while True:
            # events
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    return None
                if e.type == pg.WINDOWRESIZED:
                    ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

            t = time.time() - start_time

            sur = ren.get_surface()
            sur.fill(conf.ui_background_color)

            if rlib.departed_anim_renderer(t, sur):
                break

            ren.submit()

    # display game stats

    status_text = en.create_entity("status_text", {
        "ui_trans": [
            (2, 2),
            (-250, -230),
            (250, -150)
        ],

        "on_ui_frame": rlib.text_renderer,
        "text": "Mission success." if un.game_over_trigged == 2 else "Mission failed.",
        "text_size": 22,
        "text_color": conf.ui_foreground_color,
    })

    time_remaining = en.create_entity("time_remaining", {
        "ui_trans": [
            (2, 2),
            (-280, -120),
            (0, -100)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Time remaining: {format_time(un.game_over_stats[0])}",
        "text_size": 16,
        "text_color": conf.ui_foreground_faded_color,
    })

    time_played = en.create_entity("time_played", {
        "ui_trans": [
            (2, 2),
            (-280, -90),
            (0, -70)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Time in-game: {format_time(un.game_over_stats[1])}",
        "text_size": 16,
        "text_color": conf.ui_foreground_faded_color,
    })

    goal_collected = en.create_entity("goal_collected", {
        "ui_trans": [
            (2, 2),
            (-280, -50),
            (0, -30)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Goal collected: {suffix_count(un.game_over_stats[2][3]) if un.game_over_trigged == 2 else 'Failed to depart'}",
        "text_size": 16,
        "text_color": conf.ui_foreground_color,
    })

    stone_mined = en.create_entity("stone_mined", {
        "ui_trans": [
            (2, 2),
            (-280, -10),
            (0, 10)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Total stone mined: {suffix_count(un.game_over_stats[3][1])}",
        "text_size": 16,
        "text_color": conf.ui_foreground_faded_color,
    })

    oxy_mined = en.create_entity("oxy_mined", {
        "ui_trans": [
            (2, 2),
            (-280, 20),
            (0, 40)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Total oxy mined: {suffix_count(un.game_over_stats[3][2])}",
        "text_size": 16,
        "text_color": conf.ui_foreground_faded_color,
    })

    goal_mined = en.create_entity("goal_mined", {
        "ui_trans": [
            (2, 2),
            (-280, 50),
            (0, 70)
        ],

        "on_ui_frame": rlib.left_aligned_text_renderer,
        "text": f"Total goal mined: {suffix_count(un.game_over_stats[3][3])}",
        "text_size": 16,
        "text_color": conf.ui_foreground_faded_color,
    })

    return_button = en.create_entity("return_button", {
        "ui_trans": [
            (2, 2),
            (-100, 120),
            (100, 160)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": stats_return_to_menu,

        "button_border_size": 5,
        "button_text": "Return to menu",
    })

    global return_to_menu
    return_to_menu = False

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.MOUSEBUTTONDOWN:
                en.click_event((e.dict["pos"], e.dict["button"]))
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)

        if return_to_menu:
            break

        sur = ren.get_surface()
        sur.fill(conf.ui_background_color)

        en.render_ui(sur)

        ren.submit()

    en.reset()
    return 0

# == how-to loop ==

def page_change(p):
    en.reset()

    # setup controls

    return_button = en.create_entity("return_button", {
        "ui_trans": [
            (2, 2),
            (-100, 220),
            (100, 260)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": exit_to_menu,

        "button_border_size": 5,
        "button_text": "Return to menu",
    })

    prev_button = en.create_entity("prev_button", {
        "ui_trans": [
            (2, 2),
            (-200, 160),
            (-20, 200)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": prev_page,

        "button_border_size": 5,
        "button_text": "Previous",
    })

    next_button = en.create_entity("next_button", {
        "ui_trans": [
            (2, 2),
            (20, 160),
            (200, 200)
        ],

        "on_ui_frame": rlib.button_renderer,
        "on_click": next_page,

        "button_border_size": 5,
        "button_text": "Next",
    })

    # setup mock game state for units and level

    cam.set_camera((0, 0))

    if p == 1 or p == 2 or p == 3:
        lvl.init_level(True)
        lvl.resize_level_preren(ren.get_surface().get_size())

        if p == 1:
            lvl.set_circle(lvl.world_to_grid_space((-300, 0)), 16, 2)
            lvl.set_circle(lvl.world_to_grid_space((300, 0)), 16, 3)

            lvl.set_circle_nav(lvl.world_to_grid_space((-300, 0)), 16, 0)
            lvl.set_circle_nav(lvl.world_to_grid_space((300, 0)), 16, 0)

            oxy_text = en.create_entity("oxy_title", {
                "ui_trans": [
                    (2, 2),
                    (-290, 100),
                    (-290, 100),
                ],

                "on_ui_frame": rlib.text_renderer,
                "text": "oxy",
                "text_size": 18,
                "text_color": conf.ui_foreground_color,
            })

            goal_text = en.create_entity("goal_title", {
                "ui_trans": [
                    (2, 2),
                    (310, 100),
                    (310, 100),
                ],

                "on_ui_frame": rlib.text_renderer,
                "text": "goal",
                "text_size": 18,
                "text_color": conf.ui_foreground_color,
            })

        base = en.create_entity("player_base", {
            "transform": None,

            # "on_frame": rlib.rect_renderer,
            # "rect_color": (254, 254, 254),

            # "tick": un.base_tick,

            # base components

            "stored_materials": [
                None, # air (unused)
                0, # rock
                conf.initial_base_oxy_count, # oxy
                158, # goal
            ],

            "power_usage": 16, # initial power usage
            "busy_generating": 0,

            "units_undocked": 0,

            "pretty_name": (4, "Base (You)")
        })

        if p == 2:
            base["transform"] = [ # base at world root
                (200 + 30, 0 + 20),
                (60, 40)
            ]

            base["on_frame"] = rlib.rect_renderer
            base["rect_color"] = (254, 254, 254)

            base_text = en.create_entity("base_title", {
                "ui_trans": [
                    (2, 2),
                    (230, 60),
                    (230, 60),
                ],

                "on_ui_frame": rlib.text_renderer,
                "text": "vessel",
                "text_size": 16,
                "text_color": conf.ui_foreground_color,
            })

        if p == 1 or p == 2:
            sig.add_transceiver(lvl.world_to_grid_space((0, 0)))

            u = en.create_entity(f"unit_mock", {
                "transform": [
                    None, # set on ticks
                    (15, 15) 
                ],

                "grid_trans": lvl.world_to_grid_space((0, 0)),
                "base_dock_pos": lvl.world_to_grid_space((0, 0)),

                "on_frame": rlib.rect_renderer,
                "rect_color": conf.unit_colors[0],

                "tick": un.unit_tick,

                # unit components

                "unit_index": 0,
                "pretty_name": f"Totorial Unit",

                "stored_materials": [
                    None, # air (unused)
                    0, # rock
                    0, # oxy
                    0, # goal
                ],
                "transfer_size": 0,

                "task_queue": [],
                "mining_queue": set(),

                "already_idle": True,

                "active_transmitter": sig.find_signal(lvl.world_to_grid_space((0, 0))),
                "auto_return": False,

                "is_docked": True,
            })

            if p == 2:
                pos = lvl.world_to_grid_space((200, 0))

                u["grid_trans"] = lvl.world_to_grid_space((-200, 0))
                u["base_dock_pos"] = (pos[0] - 1, pos[1])
        
        if p == 3:
            base["tick"] = un.base_tick

            ti.setup_timer()

        nls.setup_nls(True)

how_to_page = 0

def next_page(e, click):
    if not cam.is_click_on_ui(e["ui_trans"], click):
        return

    global how_to_page
    if how_to_page < 6:
        how_to_page += 1

    page_change(how_to_page)

def prev_page(e, click):
    if not cam.is_click_on_ui(e["ui_trans"], click):
        return

    global how_to_page
    if how_to_page > 0:
        how_to_page -= 1

    page_change(how_to_page)

def exit_to_menu(e, click):
    if not cam.is_click_on_ui(e["ui_trans"], click):
        return

    global how_to_page
    how_to_page = None

def how_to_loop():
    pg.display.set_caption("Far Depths - Took a trip to the academia")

    global how_to_page
    how_to_page = 0

    page_change(0)

    is_dragging = False
    drag_start_pos = None

    is_right_pressed = False
    dock_base_pressed = False

    while True:
        # events
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return None
            if e.type == pg.MOUSEBUTTONDOWN:
                en.click_event((e.dict["pos"], e.dict["button"]))
            if e.type == pg.WINDOWRESIZED:
                ren.recreate_renderer((e.dict["x"], e.dict["y"]), 1)
                lvl.resize_level_preren((e.dict["x"], e.dict["y"]))

        if how_to_page == None:
            break

        if how_to_page == 1 or how_to_page == 2:
            if pg.mouse.get_pressed()[2] and not is_right_pressed:
                is_right_pressed = True

                mouse_pos = pg.mouse.get_pos()
                wm_pos = cam.inverse_translate(mouse_pos)
                gm_pos = lvl.world_to_grid_space(wm_pos)

                un.add_move_task(en.get_entity("unit_mock"), lvl.inbounds(gm_pos), pg.key.get_pressed()[pg.K_LSHIFT])
            elif not pg.mouse.get_pressed()[2]:
                is_right_pressed = False

        if how_to_page == 1:
            # not None if currently dragging
            drag_area = None

            # not None if finished dragging this frame
            final_drag_area = None

            if not is_dragging and pg.mouse.get_pressed()[0]:
                # started dragging

                is_dragging = True

                drag_start_pos = pg.mouse.get_pos()

            elif is_dragging and not pg.mouse.get_pressed()[0]:
                # stopped dragging

                is_dragging = False

                final_drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))
                drag_start_pos = None

            if is_dragging:
                drag_area = ((min(drag_start_pos[0], pg.mouse.get_pos()[0]), min(drag_start_pos[1], pg.mouse.get_pos()[1])), (max(drag_start_pos[0], pg.mouse.get_pos()[0]), max(drag_start_pos[1], pg.mouse.get_pos()[1])))

            # mark area for mining
            if not final_drag_area == None:
                w_drag_area = (cam.inverse_translate(final_drag_area[0]), cam.inverse_translate(final_drag_area[1]))
                g_drag_area = (lvl.inbounds(lvl.world_to_grid_space(w_drag_area[0])), lvl.inbounds(lvl.world_to_grid_space(w_drag_area[1])))

                mining_queue = un.create_mining_queue(g_drag_area)

                if not len(mining_queue) == 0:
                    # lvl.set_pixels_for_mining(mining_queue)
                    un.add_mining_task(en.get_entity("unit_mock"), mining_queue, pg.key.get_pressed()[pg.K_LSHIFT])
        elif how_to_page == 2:
            if pg.key.get_pressed()[pg.K_r] and not dock_base_pressed:
                dock_base_pressed = True
                un.add_dock_task(en.get_entity("unit_mock"), pg.key.get_pressed()[pg.K_LSHIFT], pg.key.get_pressed()[pg.K_LALT])
            elif not pg.key.get_pressed()[pg.K_r]:
                dock_base_pressed = False

        en.tick()

        sur = ren.get_surface()
        sur.fill(conf.ui_background_color)

        if how_to_page == 1 or how_to_page == 2:
            lvl.render_level(sur)

        en.render_entities(sur)

        if how_to_page == 1:
            if not drag_area == None:
                pg.draw.rect(sur, (64, 255, 64), (drag_area[0][0], drag_area[0][1], drag_area[1][0] - drag_area[0][0], drag_area[1][1] - drag_area[0][1]))

        rlib.manual_renderer(how_to_page, sur)
        en.render_ui(sur)

        ren.submit()

    en.reset()
    return 0