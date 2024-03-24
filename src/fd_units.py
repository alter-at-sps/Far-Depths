import src.fd_entity as en
import src.fd_level as lvl

import src.fd_astar as astar
import src.fd_notif as nls
import src.fd_render as ren
import src.fd_config as conf
import src.fd_struct as st
import src.fd_signal as sig

# == Far Depths Unit AI and Base Controller ==

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
        elif task[0] == 2: # dock task
            pass
        elif task[0] == 3: # build task
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
    e.pop("path_target_build", None)

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
        elif task[0] == 2: # material transfer
            pass
        elif task[0] == 3: # building a struct
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

def add_dock_task(e, append_task):
    if not append_task:
        clear_unit_tasks(e)

    e["task_queue"].append((2, ))

def add_build_task(e, pos, struct, append_task):
    if not lvl.get_pixel_navgrid(pos) == 1:
        nls.push_error(f"unit {e['unit_index']}", "Can't build at reqested position!")
        return
    
    if not append_task:
        clear_unit_tasks(e)

    e["task_queue"].append((3, pos, struct))

# mining subroutines

# contains a set of all points currenly being mined by a unit
currently_being_mined_global = set()

def set_next_to_mine(e, finished_point, mining_queue: set):
    if len(mining_queue) == 0:
        return
    
    # first try neighboring points

    for p in [ (1, 0), (0, 1), (-1, 0), (0, -1) ]:
        p = ((finished_point[0] + p[0], finished_point[1] + p[1]))

        # check if already mined out and skip and if already being mined by a different unit (can't remove here yet)
        if lvl.get_pixel(lvl.inbounds(p)) == 0 or p in currently_being_mined_global:
            continue

        if p in mining_queue:
            e["current_path"] = [ finished_point ]
            e["path_target_mine"] = p

            mining_queue.remove(p)

            return

    # search for any reachable mining points

    current_point = e["grid_trans"]

    # workaround for sets not being able to change size durind iteration
    remove_queue = []

    for p in mining_queue:
        # check if not mined by other units in the meantime
        if lvl.get_pixel(p) == 0 or p in currently_being_mined_global:
            remove_queue.append(p)
            continue

        path = astar.pathfind(current_point, p, True)

        if not path == None:
            e["current_path"] = path
            e["path_target_mine"] = p

            for _p in remove_queue:
                mining_queue.remove(_p)

            revert_mining_queue(remove_queue)
            
            mining_queue.remove(p)

            return
    
    just_removed = not len(remove_queue) == 0

    for _p in remove_queue:
        mining_queue.remove(_p)

    # failed to find path to continue mining

    revert_mining_queue(remove_queue)
    if len(mining_queue) == 0 and just_removed:
        # "finished" mining operation without errors
        return

    nls.push_error(f"unit {e['unit_index']}", "Can't find path to continue mining!")

    revert_mining_queue(e["mining_queue"])

# mine_times = [
#     2,
#     5
# ]

# move_time = .2

total_mined = [
    None, # air (unused)
    0, # stone
    0, # oxy
    0, # goal
]

def unit_tick(e: dict):
    global t

    pos = lvl.grid_to_world_space(e["grid_trans"])

    e["transform"][0] = (pos[0] + lvl.point_size // 2, pos[1] + lvl.point_size // 2)

    nls_sender = f"unit {e['unit_index']}"

    # check if unit busy

    task = e.get("busy_with")
    if not task == None:
        task[1] -= ren.delta_time

        if task[1] <= 0:
            e.pop("busy_with")

            # handle on task finished
            if task[0] == 0: # finished mining
                mats = e["stored_materials"]

                mat_type = lvl.get_pixel(task[2])
                mats[mat_type] += 1
                total_mined[mat_type] += 1

                lvl.set_pixel(task[2], 0) # mine out pixel
                lvl.set_pixel_navgrid(task[2], 1) # expand navgrid
                lvl.set_pixel_mark(task[2], 0) # remove mining overlay

                lvl.unfog_area([ task[2] ], 18) # trigger incremental flood fill
                # lvl.set_pixel_fow(task[2], 18) # make sure points is fully visible

                currently_being_mined_global.remove(task[2])

                mining_queue = e["mining_queue"]
                if not len(mining_queue) == 0:
                    set_next_to_mine(e, task[2], mining_queue)
            elif task[0] == 1: # moving cooldown
                pass
            elif task[0] == 2: # material transfer
                base_mats = en.get_entity("player_base")["stored_materials"]

                base_mats[task[2]] += 1
                e["stored_materials"][task[2]] -= 1
                e["transfer_size"] += 1

                for i, mat in enumerate(e["stored_materials"]):
                    if not mat == None and not mat == 0:
                        e["busy_with"] = [2, conf.transfer_time, i]
                        break
                
                if e.get("busy_with") == None:
                    nls.push_info(nls_sender, f"Finished transfering {e['transfer_size']} blocks!")
                    e["transfer_size"] = 0
            elif task[0] == 3: # struct building
                mats = e["stored_materials"]

                # consume materials
                mats[2] -= conf.struct_build_costs[task[2][1]][0]
                mats[3] -= conf.struct_build_costs[task[2][1]][1]

                s = st.spawn_struct(task[2][0], task[2][1])

                nls.push_info(nls_sender, f"Finished building {s['pretty_name'][1]}")
            else:
                raise ValueError("invalid task type on busy_with")

        return

    # setup next task if idle

    # check path target lock *before* updating path

    target = e.get("path_target_mine")

    if not target == None and (target in currently_being_mined_global or lvl.get_pixel(target) == 0):    
        mining_queue = e["mining_queue"]
        set_next_to_mine(e, e["grid_trans"], mining_queue)
        
        if len(mining_queue) == 0:
            e.pop("path_target_mine")

    # path following update

    path = e.get("current_path")

    if not path == None:
        if len(path) == 0:
            e.pop("current_path")

            target = e.pop("path_target_mine", None)
            if not target == None: # target is a mining location
                if not target in currently_being_mined_global and not lvl.get_pixel(target) == 0: # avoid more units mining the same point at the same time
                    currently_being_mined_global.add(target)

                    e["busy_with"] = [0, conf.mine_times[lvl.get_pixel(target)], target]
                else:
                    raise SyntaxError("mining global lock caugth too late.")
            
            target = e.pop("path_target_dock", False)
            if target:
                if e["auto_return"]:
                    nls.push_error(nls_sender, "Auto-docked because of a signal loss!")
                    e["auto_return"] = False

                nls.push_info(nls_sender, "Docked and transfering blocks...")
                
                if not e["is_docked"]:
                    e["is_docked"] = True
                    en.get_entity("player_base")["units_undocked"] -= 1

                for i, mat in enumerate(e["stored_materials"]):
                    if not mat == None and not mat == 0:
                        e["busy_with"] = [2, conf.transfer_time, i]
                        break
            
            target = e.pop("path_target_build", None)
            if not target == None:
                mats = e["stored_materials"]
                
                if mats[2] - conf.struct_build_costs[target[1]][0] >= 0 and mats[3] - conf.struct_build_costs[target[1]][1] >= 0:
                    if (not target[1] == 0 or not sig.find_signal(target[0]) == None) and (not target[1] == 1 or not sig.find_pipeline_sink(target[0]) == None):
                        nls.push_info(nls_sender, "Building a new structure...")

                        # resources are consumed after the structure is done
                        e["busy_with"] = [3, conf.struct_build_times[target[1]], target]
                    else:
                        if target[1] == 0:
                            nls.push_error(nls_sender, "Can't build a Transceiver out of range!")
                        else:
                            nls.push_error(nls_sender, "Can't build a Substation out of range!")
                else:
                    nls.push_error(nls_sender, "Not enough materials to build structure!")
                    
        else:
            next_pos = path.pop(0)
            e["grid_trans"] = next_pos

            if e["is_docked"]:
                e["is_docked"] = False
                en.get_entity("player_base")["units_undocked"] += 1

            lvl.unfog_area([ next_pos ], 24)

            e["busy_with"] = [1, conf.move_time]

    # update signal range

    gp = e["grid_trans"]
    if e["active_transmitter"] == None or not sig.check_signal(e["active_transmitter"], gp):
        e["active_transmitter"] = sig.find_signal(gp)

    # setup the next task if idle

    task_queue = e["task_queue"]

    if e.get("busy_with") == None and len(task_queue) == 0 and not e["already_idle"]:
        if not e["active_transmitter"] == True:
            nls.push_warn(nls_sender, "Finished all tasks in my queue, idling...") 
        else:
            add_dock_task(e, False)
            e["auto_return"] = True
        
        e["already_idle"] = True
    elif not e.get("busy_with") == None or not len(task_queue) == 0:
        e["already_idle"] = False 

    if e.get("busy_with") == None and not len(task_queue) == 0:
        task = task_queue.pop(0)

        if task[0] == 0: # mining task
            e["mining_queue"] = task[1]

            nls.push_info(nls_sender, f"Starting a mining operation of {len(task[1])} blocks.")

            set_next_to_mine(e, gp, task[1])
                
        elif task[0] == 1: # move task
            path = astar.pathfind(gp, task[1])

            if not path == None:
                if not len(path) == 0:
                    e["current_path"] = path

                    nls.push_info(nls_sender, f"Moving to position {path[-1]}.")
            else:
                nls.push_error(nls_sender, "Can't find a path to the next location!")

        elif task[0] == 2: # dock task
            path = astar.pathfind(gp, sig.find_closest_substation(gp, e["base_dock_pos"]))

            if not path == None:
                e["current_path"] = path
                e["path_target_dock"] = True
            else:
                # should *never* happen
                nls.push_error(nls_sender, "Can't find a path to docking port!")

        elif task[0] == 3: # build task
            path = astar.pathfind(gp, task[1], True)

            if not path == None:
                e["current_path"] = path
                e["path_target_build"] = (task[1], task[2])
            
            else:
                nls.push_error(nls_sender, "Can't find a path to build a structure!")

        else:
            raise ValueError("invalid task type on task_setup")

# base tick

game_over_trigged = 0
game_over_stats = []

def base_tick(e: dict):
    # update power generation

    global game_over_trigged

    e["busy_generating"] -= ren.delta_time

    if e["busy_generating"] <= 0:
        base_mats = e["stored_materials"]
        base_mats[2] -= 1

        if base_mats[2] <= 0:
            game_over_trigged = 1

        e["busy_generating"] = conf.oxy_to_power_time / e["power_usage"]