import src.fd_level as lvl
import src.fd_entity as en
import src.fd_astar as astar
import src.fd_notif as nls

import time

# task subroutines

def create_mining_queue(drag_area):
    queue = set()

    for x in range(drag_area[0][0], drag_area[1][0] + 1):
        for y in range(drag_area[0][1], drag_area[1][1] + 1):
            if not lvl.get_pixel((x, y)) == 0:
                queue.add((x, y))
                lvl.offset_by_pixel_mark((x, y), 1)

    return queue

def revert_mining_queue(queue):
    for p in queue:
        lvl.offset_by_pixel_mark(p, -1)
    
    queue.clear()

def clear_unit_tasks(e):
    for task in e["task_queue"]:
        if task[0] == 0: # queued mining task
            for p in task[1]:
                lvl.offset_by_pixel_mark(p, -1)
        elif task[0] == 1: # move task
            pass
        else:
            raise ValueError("invalid task type on clear_unit")

    e["task_queue"].clear()
    
    # clear movement
    e.pop("current_path", None)
    
    mine_task = e.pop("path_target_mine", None)
    if not mine_task == None:
        lvl.offset_by_pixel_mark(mine_task, -1)
    
    e.pop("path_target_dock", None)

    # clear mining
    revert_mining_queue(e["mining_queue"])
    interupt_busy_unit(e)

def interupt_busy_unit(e):
    task = e.pop("busy_with", None)

    if not task == None:
        if task[0] == 0: # stop mining task
            currently_being_mined_global.remove(task[2])
            lvl.offset_by_pixel_mark(task[2], -1)

        elif task[0] == 1: # continue movment cooldown
            pass

        else: 
            raise ValueError("invalid task type on busy_interupt")

def add_mining_task(e, mining_queue, append_task):
    if not append_task:
        clear_unit_tasks(e)

    e["task_queue"].append((0, mining_queue))

def add_move_task(e, target_point, append_task):
    if not append_task:
        clear_unit_tasks(e)

    e["task_queue"].append((1, target_point))

# mining subroutines

# contains a set of all points currenly being mined by a unit
currently_being_mined_global = set()

def set_next_to_mine(e, finished_point, mining_queue: set):
    # first try neighboring points

    for p in [ (1, 0), (0, 1), (-1, 0), (0, -1) ]:
        p = ((finished_point[0] + p[0], finished_point[1] + p[1]))

        # check if not mined by other units in the meantime
        if lvl.get_pixel(p) == 0 or p in currently_being_mined_global:
            continue

        if p in mining_queue:
            e["current_path"] = [ finished_point ]
            e["path_target_mine"] = p

            mining_queue.remove(p)

            return

    # search for any reachable mining points

    current_point = e["grid_trans"]

    for p in mining_queue:
        # check if not mined by other units in the meantime
        if lvl.get_pixel(p) == 0 or p in currently_being_mined_global:
            mining_queue.remove(p)
            continue

        path = astar.pathfind(current_point, p, True)

        if not path == None:
            e["current_path"] = path
            e["path_target_mine"] = p
            
            mining_queue.remove(p)

            return

    # failed to find path to continue mining

    nls.push_error(f"unit {e['unit_index']}", "Failed to find path to continue mining, stopping!")

    revert_mining_queue(e["mining_queue"])

# transfer subroutines

def add_to_base(mats):
    print("add_to_base TODO")

def add_to_sub(sub_index, mats):
    sub = en.get_entity(f"substation_{sub_index}")

    print("add_to_sub TODO")

# mine_times = [
#     2,
#     5
# ]

# move_time = .2
    
mine_times = [
    0, # air (unused)
    .02, # stone
    .15, # oxy
    1, # goal
]

move_time = .005

t = time.time()

def unit_tick(e: dict):
    global t

    # TODO: move only after some cooldown

    pos = lvl.grid_to_world_space(e["grid_trans"])

    e["transform"][0] = (pos[0] + lvl.point_size // 2, pos[1] + lvl.point_size // 2)

    nls_sender = f"unit {e['unit_index']}"

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
                lvl.set_pixel_navgrid(task[2], 1) # expand navgrid
                lvl.set_pixel_mark(task[2], 0) # remove mining overlay

                currently_being_mined_global.remove(task[2])

                mining_queue = e["mining_queue"]
                if not len(mining_queue) == 0:
                    set_next_to_mine(e, task[2], mining_queue)
            elif task[0] == 1: # moving cooldown
                pass
            else:
                raise ValueError("invalid task type on busy_with")

        return

    # setup next task if idle

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
                if not target in currently_being_mined_global: # avoid more units mining the same point at the same time
                    currently_being_mined_global.add(target)

                    e["busy_with"] = [0, mine_times[lvl.get_pixel(target)], target]
                    e.pop("path_target_mine")
                else:
                    mining_queue = e["mining_queue"]
                    if not len(mining_queue) == 0:
                        set_next_to_mine(e, e["grid_trans"], mining_queue)
        else:
            next_pos = path.pop(0)
            e["grid_trans"] = next_pos

            lvl.unfog_area([ next_pos ], 24)

            e["busy_with"] = [1, move_time]
    
    # setup the next task if idle

    task_queue = e["task_queue"]

    if e.get("busy_with") == None and not len(task_queue) == 0:
        task = task_queue.pop(0)

        if task[0] == 0: # mining task
            e["mining_queue"] = task[1]

            nls.push_info(nls_sender, f"Starting a mining operation of {len(task[1])} blocks.")

            set_next_to_mine(e, e["grid_trans"], task[1])
                
        elif task[0] == 1: # move task
            path = astar.pathfind(e["grid_trans"], task[1])

            if not path == None:
                if not len(path) == 0:
                    e["current_path"] = path

                    nls.push_info(nls_sender, f"Moving to position {path[-1]}.")
            else:
                nls.push_error(nls_sender, "Failed to move to the requested position, stopping!")

        else:
            raise ValueError("invalid task type on task_setup")
    elif e.get("busy_with") == None and len(task_queue) == 0:
        # nls.push_warn(nls_sender, "Finished all tasks in my queue, idling...") 
        pass