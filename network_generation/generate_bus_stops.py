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

parser = argparse.ArgumentParser(description='Generate bus stops along the network.')

parser.add_argument('--net_file', type=str, help='Path to the SUMO network file (.net.xml)')
parser.add_argument('--bus_stop_file', type=str, help='Path to save the bus stops file (.add.xml)')
parser.add_argument('--every_nth', type=int, default=2, help='Place bus stops on every nth edge')
parser.add_argument('--stop_length', type=float, default=7, help='Length of each bus stop')
parser.add_argument('--stop_position', type=float, default=50, help='Location of bus stop on edge')

args = parser.parse_args()

# Define input and output file paths
net_file = args.net_file
bus_stop_file = args.bus_stop_file

# Load the SUMO network
net = sumolib.net.readNet(net_file)

# Open file to write the bus stops
with open(bus_stop_file, "w") as f:
    f.write('<additional>\n')

    stop_interval = args.stop_position  # Place a stop every 50 meters
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
                lane_id = lanes[0].getID()
                edge_length = edge.getLength()

                pos = stop_interval
                while pos < edge_length:
                    f.write(f'    <busStop id="busStop_{stop_id}" lane="{lane_id}" startPos="{pos}" endPos="{pos + stop_length}" friendlyPos="true"/>\n')
                    pos += stop_interval
                    stop_id += 1

    f.write('</additional>\n')

print(f"Bus stops successfully saved to {bus_stop_file}")

