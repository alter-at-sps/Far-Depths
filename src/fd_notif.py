import src.fd_render_lib as rlib
import src.fd_entity as en

# == Far Depths Notifications and (in-game) Logs ==

max_log_length = 15
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
    print(f"> {sender} WARN: {message}")

def push_error(sender, message):
    append_log((2, f"> {sender}: {message}"))
    print(f"> {sender} ERROR: {message}")

def setup_nls():
    # TODO: proper UI

    nls = en.create_entity("nls_console", {
        "ui_trans": [
            (False, True), # anchor inverts
            (0, 0),
            (475, 250)
        ],

        "on_frame": rlib.nls_renderer,
        "nls_log_console": log_console
    })

    log_console.clear()