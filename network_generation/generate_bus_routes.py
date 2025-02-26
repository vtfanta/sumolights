# Created with the help of ChatGPT, Gemini (fantavit)
import argparse
import os, sys
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    from sumolib import checkBinary
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib
import random

parser = argparse.ArgumentParser(description='Generate bus stops along the network.')

parser.add_argument('--net_file', type=str, help='Path to the SUMO network file (.net.xml)')
parser.add_argument('--bus_stop_file', type=str, help='Path to save the bus stops file (.add.xml)')
parser.add_argument('--route_file', type=str, help='Path to save the bus routes file (.rou.xml)')
parser.add_argument('--stop_position', type=float, default=50.0, help='Distance between bus stops (meters)')
parser.add_argument('--stop_length', type=float, default=7.0, help='Length of each bus stop (meters)')
parser.add_argument('--every_nth', type=int, default=1, help='Process every nth edge pair')
parser.add_argument('--route_repeats', type=int, default=10, help='Number of times to repeat each route')
parser.add_argument('--stop_duration', type=int, default=10, help='Time spent at each bus stop (seconds)')
parser.add_argument('--num_buses', type=int, default=5, help='Number of buses to create')
parser.add_argument('--sumocfg_file', type=str, help='Path to save the sumocfg file (.sumocfg)')

args = parser.parse_args()

# Define input and output file paths
net_file = args.net_file
bus_stop_file = args.bus_stop_file
route_file = args.route_file
sumocfg_file = args.sumocfg_file

# Load the SUMO network
net = sumolib.net.readNet(net_file)

# Open file to write the bus stops
with open(bus_stop_file, "w") as f:
    f.write('<additional>\n')

    stop_position = args.stop_position  # Place a stop every 50 meters
    stop_length = args.stop_length    # Length of each bus stop
    stop_id = 0         # Counter for unique stop IDs

    # Get network boundaries to identify terminal edges
    min_x, min_y, max_x, max_y = net.getBoundary()

    def is_boundary_edge(edge):
        """ Check if an edge is on the network boundary. """
        from_x, from_y = edge.getFromNode().getCoord()
        to_x, to_y = edge.getToNode().getCoord()
        return (from_x <= min_x or from_x >= max_x or to_x <= min_x or to_x >= max_x or
                from_y <= min_y or from_y >= max_y or to_y <= min_y or to_y >= max_y)

    # Select every second edge, excluding boundary edges
    edges = [edge for i, edge in enumerate(net.getEdges()) if not is_boundary_edge(edge)]
    
    # Dict to store edge and lane IDs for each stop
    stop_edge_lane = {}

     # Iterate through edges in pairs to ensure opposite stops
    for i in range(0, len(edges) - 1, args.every_nth): # Iterate in steps of every_nth
        edge1 = edges[i]
        # Find the opposite edge (if it exists)
        for j in range(i+1, len(edges)):
            edge2 = edges[j]
            if edge1.getFromNode() == edge2.getToNode() and edge1.getToNode() == edge2.getFromNode():
                break # Found the opposite edge
        else: # If we did not find an opposite edge, we skip this edge
            continue

        for edge in [edge1, edge2]: # Create stops on both edges
            lanes = edge.getLanes()
            if len(lanes) > 0:
                # choose road and not pavement
                lane_id = [l.getID() for l in lanes if "bus" in l.getPermissions()][0]
                # lane_id = lanes[0].getID()
                edge_length = edge.getLength()

                pos = stop_position
                while pos < edge_length:
                    f.write(f'    <busStop id="busStop_{stop_id}" lane="{lane_id}" startPos="{pos}" endPos="{pos + stop_length}" friendlyPos="true"/>\n')
                    stop_edge_lane[f"busStop_{stop_id}"] = (edge.getID(), lane_id)
                    pos += stop_position
                    stop_id += 1

    f.write('</additional>\n')

print(f"Bus stops successfully saved to {bus_stop_file}")

# --- Route Generation ---
with open(route_file, "w") as f:
    f.write('<routes>\n')

    bus_stop_ids = [f"busStop_{i}" for i in range(stop_id)]

    # Define a single bus type
    f.write(f'    <vType id="bus" vClass="bus"/>\n')
    
    route_length = len(bus_stop_ids) // args.num_buses
    for k in range(args.num_buses):
        # Define a bus route
        f.write(f'    <route id="bus_route_{k}" edges="')

        route_stop_edges = [stop_edge_lane[bus_stop_ids[k * route_length + i % len(bus_stop_ids)]][0] for i in range(route_length)]
        print(route_stop_edges)
        route_all_edges = []
        for i in range(len(route_stop_edges) - 1):
            route_all_edges.append(route_stop_edges[i])
            between_stops_path = [e.getID() for e in net.getFastestPath(net.getEdge(route_stop_edges[i]), net.getEdge(route_stop_edges[i+1]))[0][1:-1]]
            if len(between_stops_path) > 0:
                # print(f"{k}, {i} Between stops path: {between_stops_path}")
                route_all_edges += between_stops_path
        route_all_edges.append(route_stop_edges[-1])
        # ensure last stop is connected to first stop
        between_stops_path = [e.getID() for e in net.getFastestPath(net.getEdge(route_stop_edges[-1]), net.getEdge(route_stop_edges[0]))[0][1:-1]]
        if len(between_stops_path) > 0:
            route_all_edges += between_stops_path
        # f.write(f'{stop_edge_lane[bus_stop_ids[k * route_length + i % len(bus_stop_ids)]][0]} ')
        f.write(f'{" ".join(route_all_edges)}')
        f.write(f'" repeat="{args.route_repeats}">\n')
        
        for i in range(route_length):
            f.write(f'\t\t<stop busStop="{bus_stop_ids[k * route_length + i % len(bus_stop_ids)]}"')
            f.write(f' duration="{args.stop_duration}"/>\n')

        f.write(f'\t</route>\n')
        
    for k in range(args.num_buses):
        f.write(f'\t<vehicle id="bus_{k}" type="bus" route="bus_route_{k}" depart="0."/>\n')

    f.write('</routes>\n')

print(f"Bus routes successfully saved to {route_file}")
# print(net.getFastestPath(net.getEdge('A1B1'),
#     net.getEdge('A1A0'))[0])

# --- sumocfg Generation ---
with open(sumocfg_file, "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n\n')

    f.write('<sumoConfiguration>\n')

    f.write(f'\t<input>\n')
    f.write(f'\t\t<net-file value="{net_file}"/>\n')
    f.write(f'\t\t<route-files value="{route_file}"/>\n')
    f.write(f'\t\t<additional-files value="{bus_stop_file}"/>\n')
    f.write(f'\t</input>\n')

    f.write(f'</sumoConfiguration>\n')
print(f"Sumo config successfully saved to {sumocfg_file}")