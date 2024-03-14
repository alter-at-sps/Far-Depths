# == WARNING: These settings are not ment to be changed randomly and can cause crashes if set incorectly ==

# graphics

empty_color = (8, 8, 8)
fog_color = (2, 2, 2)

stone_color = (127, 127, 127)
oxy_color = (200, 200, 200)
goal_color = (64, 245, 64)

loading_status_texts = [
    "> Undocking...",
    "> Searching for a suitable location...",
    "> Traveling to location...",
    "> Searching for a landing location...",
    "> Landing at location...",
    "> Get ready for deployment!"
]

ui_foreground_color = (255, 255, 255)
ui_background_color = (4, 4, 4)
ui_foreground_faded_color = (127, 127, 127)

nls_log_colors = [
    (225, 225, 225),
    (200, 200, 64),
    (255, 16, 16)
]

nls_border_size = 5
nls_cursor_margin = 5
nls_log_line_size = 14
nls_outline_margin = 10
nls_outline_width = 10

ctl_border_size = 10

# level gen

level_size = (500, 500)

fill_percent = 25
level_seed = None # random

num_of_oxy_deposits_min_max = (125, 175)
oxy_deposit_size_min_max = (4, 10)

num_of_goal_deposits_min_max = (85, 125)
goal_deposit_size_min_max = (6, 12)

# unit behaviour

mine_times = [
    0, # air (unused)
    .02, # stone
    .15, # oxy
    1, # goal
]

move_time = .005
transfer_time = .05

cam_speed = 500

unit_colors = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
]

# menu

secret_titles = [
    "Far Depths - Mining and stayin' alive, stayin' alive",
    "Far Depths - Never gonna mine you up",
    "Far Depths - Failing to reach centrals weekly quota",
    "Far Depths - Being a great asset for central",
    "Far Depths - Mining for Democracy",
    "Far Depths - There are no enemies in this game, right?",
    "Far Depths - Mining in an OSHA approved definitely non-lethal submersible",
    "Far Depths - Mining with only 24 new warnings per second",
    "Far Depths - Mining and ignoring all the bugs that don't exists.",
]

# dev options

dev_fastmap = False
dev_frametimes = False