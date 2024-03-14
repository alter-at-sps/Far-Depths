import src.fd_render_lib as rlib
import src.fd_entity as en

def set_selected(e):
    en.get_entity("control_panel")["selected_entity"] = e

def setup_ctl_panel():
    ctl = en.create_entity("control_panel",{
        "ui_trans": [
            (True, False),
            (0, 0),
            (300, 500)
        ],

        "on_ui_frame": rlib.ctl_renderer,
        "tick": ctl_tick,
        "selected_entity": None,

        "panel_data": {
            "selected_title": (0, "unit name"),
        }
    })

def ctl_tick(e):
    sel = e["selected_entity"]
    data = e["panel_data"]

    data["materials"] = sel.get("stored_materials")

    unit = sel.get("unit_index")
    if not unit == None:
        data["selected_title"] = (sel["unit_index"] - 1, sel["pretty_name"])

        busy_task = sel.get("busy_with")
        if not busy_task == None:
            if busy_task[0] == 0:
                data["status"] = "Mining..."
            elif busy_task[0] == 1:
                if not sel.get("path_target_mine") == None:
                    data["status"] = "Mining..."
                elif not sel.get("path_target_dock", -1) == -1:
                    data["status"] = "Travelling To Dock..."
                else:
                    data["status"] = "Travelling..."
                
            elif busy_task[0] == 2:
                data["status"] = "Transfering..."
            else:
                raise ValueError("unknown busy task type in ctl_tick")
        elif sel["already_idle"]:
            data["status"] = "Idle"
    else:
        data["selected_title"] = (sel["name_color"], sel["pretty_name"])

        data["status"] = "Online"