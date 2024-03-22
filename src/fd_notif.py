import src.fd_render_lib as rlib
import src.fd_entity as en
import src.fd_camera as cam

# == Far Depths Notifications and (in-game) Logs ==

max_log_length = 16
log_console = []

def append_log(log):
    log_console.append(log)

    if len(log_console) > max_log_length:
        log_console.pop(0)

def push_info(sender, message):
    append_log((0, f"> {sender}: {message}"))
    print(f"> {sender} INFO: {message}")

def push_warn(sender, message):
    append_log((1, f"> {sender}: {message}"))

    en.get_entity("nls_terminal")["nls_notif_timer"][1] = 2
    print(f"> {sender} WARN: {message}")

def push_error(sender, message):
    append_log((2, f"> {sender}: {message}"))

    en.get_entity("nls_terminal")["nls_notif_timer"][0] = 2
    print(f"> {sender} ERROR: {message}")

def setup_nls():
    nls = en.create_entity("nls_terminal", {
        "ui_trans": [
            (0, 1), # anchor inverts
            (0, 0),
            (475, 250)
        ],

        "on_ui_frame": rlib.nls_renderer,
        "on_click": nls_on_click,
        "nls_log_console": log_console,
        "nls_notif_timer": [ None, None ]
    })

    log_console.clear()

def nls_on_click(e: dict, click):
    return cam.is_click_on_ui(e["ui_trans"], click)