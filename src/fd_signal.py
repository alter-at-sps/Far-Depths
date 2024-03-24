from pygame import base
import src.fd_config as conf

# == Far Depths Signal and Pipeline Ranges ==

signal_transmitters = []
pipeline_sinks = []

def setup_ranges(base_pos):
    global signal_transmitters
    global pipeline_sinks

    signal_transmitters = [(base_pos, conf.base_signal_distance ** 2)]
    pipeline_sinks = [(base_pos, conf.base_pipeline_distance ** 2)]

def add_transceiver(p):
    signal_transmitters.insert(0, (p, conf.transceiver_signal_distance ** 2))

def add_substation(p):
    signal_transmitters.insert(0, (p, conf.substation_signal_distance ** 2))
    pipeline_sinks.insert(0, (p, conf.substation_pipeline_distance ** 2))

def find_signal(p):
    for t in signal_transmitters:
        d_sq = (t[0][0] - p[0]) ** 2 + (t[0][1] - p[1]) ** 2

        if t[1] >= d_sq:
            return t
    
    return None

def check_signal(t, p):
    return (t[0][0] - p[0]) ** 2 + (t[0][1] - p[1]) ** 2 <= t[1]

def find_pipeline_sink(p):
    for s in pipeline_sinks:
        d_sq = (s[0][0] - p[0]) ** 2 + (s[0][1] - p[1]) ** 2

        if s[1] >= d_sq:
            return s
    
    return None

def find_closest_substation(p, base_pos):
    min_d = (base_pos[0] - p[0]) ** 2 + (base_pos[1] - p[1]) ** 2
    pos = base_pos
    
    for s in pipeline_sinks[:-1]: # ignore base pos in sinks
        d_sq = (s[0][0] - p[0]) ** 2 + (s[0][1] - p[1]) ** 2

        if d_sq < min_d:
            min_d = d_sq
            pos = s[0]
    
    return pos