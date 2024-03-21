import src.fd_entity as en
import src.fd_render_lib as rlib
import src.fd_config as conf

def setup_timer():
    timer = en.create_entity("timer_ui", {
        "ui_trans": [
            (2, 0),
            (-110, 0),
            (110, 60)
        ],

        "on_ui_frame": rlib.timer_renderer,
        "tick": timer_tick,

        # timer components (updated by timer tick)

        "eta": 0,
        "goal_mat_count": 0,
    })

def timer_tick(e: dict):
    base = en.get_entity("player_base")
    base_mats = base["stored_materials"]

    e["eta"] = max(0, (base_mats[2] * conf.oxy_to_power_time // base["power_usage"]) - conf.timer_eta_zero_offset + (base["busy_generating"]))
    e["goal_mat_count"] = base_mats[3]