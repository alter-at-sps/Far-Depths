import src.fd_level as lvl
import src.fd_render as r

# == Far Depths A* Pathfinder ==

def h(point, end_point):
    return (point[0] - end_point[0]) ** 2 + (point[1] - end_point[1]) ** 2

def reconstruct_path(closed_list, end_pos):
    path = []
    
    current_pos = end_pos

    while True:
        node = closed_list[current_pos]

        if not node[2] == None:
            path.append(current_pos)
            current_pos = node[2]
        else:
            break

    path.reverse()
    return path

# end_exclusive = won't include the end position, will just to end up next to the end position (at most distance = 1)
def pathfind(start_point, end_point, end_exclusive = False):
    open_list = {}
    closed_list = {}

    open_list[start_point] = (
        0, # g
        h(start_point, end_point), # h
        None # parent node pos
    )

    # check if outside of navgrid (to prevent a loong astar search with no path found)
    if not end_exclusive and (lvl.get_pixel_navgrid(start_point) == 0 or lvl.get_pixel_navgrid(end_point) == 0):
        return None
    
    # check if at least one neighboring point is accessible
    elif end_exclusive:
        found_point = False

        for offset in [ (1, 0), (0, 1), (-1, 0), (0, -1) ]:
            if lvl.get_pixel_navgrid(lvl.inbounds((end_point[0] + offset[0], end_point[1] + offset[1]))) == 1:
                found_point = True
                break
        
        if not found_point:
            return None

    while not len(open_list) == 0:
        # find best next point

        current_node = None
        current_pos = None

        current_node_f = None

        for pos, node in open_list.items():
            f = node[0] + node[1]

            if current_node_f == None or f < current_node_f:
                current_node_f = f
                current_node = node
                current_pos = pos
        
        if current_node == None:
            return None # failed to find a path
        
        # debug astar visualizer
        # lvl.set_pixel(current_pos, 1)
        # lvl.render_level(r.get_surface())
        # r.submit()
        
        # switch current to closed

        open_list.pop(current_pos)
        closed_list[current_pos] = current_node

        if not end_exclusive and current_pos == end_point:
            return reconstruct_path(closed_list, current_pos)

        elif end_exclusive and abs(current_pos[0] - end_point[0]) + abs(current_pos[1] - end_point[1]) == 1:
             return reconstruct_path(closed_list, current_pos)

        # check adjacent points

        for x_offset in range(-1, 2):
            for y_offset in range(-1, 2):
                if x_offset == 0 and y_offset == 0:
                    continue

                adj_pos = lvl.inbounds((current_pos[0] + x_offset, current_pos[1] + y_offset))

                node_in_closed = closed_list.get(adj_pos)
                if node_in_closed == None and lvl.get_pixel_navgrid(adj_pos) == 1:
                    adj_node = open_list.get(adj_pos)

                    if adj_node == None:
                        # add new node

                        open_list[adj_pos] = (
                            current_node[0] + 1,
                            h(adj_pos, end_point),
                            current_pos
                        )

                    else:
                        # override existing node if found a better path to it

                        if adj_node[0] > current_node[0] + 1:
                            open_list[adj_pos] = (
                                current_node[0] + 1,
                                current_node[1],
                                current_pos
                            )