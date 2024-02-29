import src.fd_level as lvl
import src.fd_entity as en

import time

def add_to_base(mats):
    print("add_to_base TODO")

def add_to_sub(sub_index, mats):
    sub = en.get_entity(f"substation_{sub_index}")

    print("add_to_sub TODO")

def set_next_to_mine(e, mining_queue):
    return mining_queue[0]

mine_times = [
    2,
    5
]

move_time = .2

t = time.time()

def unit_tick(e: dict):
    global t

    # TODO: move only after some cooldown

    pos = lvl.grid_to_world_space(e["grid_trans"])

    e["transform"][0] = (pos[0] + lvl.point_size // 2, pos[1] + lvl.point_size // 2)

    delta_t = time.time() - t
    t = time.time()

    # check if unit busy

    task = e.get("busy_with")
    if not task == None:
        task[1] -= delta_t

        if task[1] <= 0:
            e.pop("busy_with")

            # handle on task finished
            if task[0] == 0: # finished mining
                mats = e["stored_materials"]

                mat_type = lvl.get_pixel(task[2])
                mats[mat_type] += 1

                lvl.set_pixel(task[2], 0) # mine out pixel

                to_mine = e["to_mine"]
                if not len(to_mine) == 0:
                    set_next_to_mine(e, to_mine)
            elif task[0] == 1: # moving cooldown
                pass
            
            return # TODO: not sure if should return or not
        else:
            return 

    # path following update

    path = e.get("current_path")

    if not path == None:
        if len(path) == 0:
            e.pop("current_path")

            target = e.get("path_target_dock")
            if not target == None:
                if target == 0: # target is base
                    # transfer materials to base
                    mats = e["stored_materials"]

                    add_to_base(mats.copy())
                    mats.clear()

                else: # target is substation
                    # transfer materials to substation
                    mats = e["stored_materials"]

                    add_to_sub(target - 1, mats.copy())

            target = e.get("path_target_mine")
            if not target == None: # target is a mining location
                # TODO: check_if_being_mined_global

                e["busy_with"] = [0, mine_times[0], target]
                e.pop("path_target_mine")
        else:
            next_pos = path.pop(0)
            e["grid_trans"] = next_pos

            lvl.unfog_area([ next_pos ], 24)

            e["busy_with"] = [1, move_time]
            
