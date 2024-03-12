# graphics

empty_color = (8, 8, 8)
fog_color = (16, 16, 16)

stone_color = (200, 200, 200)
oxy_color = (245, 245, 245)
goal_color = (64, 245, 64)

ui_foreground_color = (255, 255, 255)
ui_background_color = (8, 8, 8)

nls_log_colors = [
    (225, 225, 225),
    (200, 200, 64),
    (255, 16, 16)
]

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