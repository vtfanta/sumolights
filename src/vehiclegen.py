import os, sys
import math
import numpy as np

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    from sumolib import checkBinary
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import traci

import numpy as np

class VehicleGen:
    def __init__(self, netdata, sim_len, demand, scale, mode, conn):
        np.random.seed()
        self.conn = conn
        self.v_data = None
        self.vehicles_created = 0
        self.netdata = netdata
        ###for generating vehicles
        self.origins = self.netdata['origin']
        self.destinations = self.netdata['destination'] 
        self.add_origin_routes()
        self.scale = scale
        self.sim_len = sim_len
        self.t = 0
        
        # vehicle state for consensus
        self.veh_states = None
        self.veh_names = None

        ###determine what function we run every step to 
        ###generate vehicles into sim
        if demand == 'single':
            self.gen_vehicles = self.gen_single
        elif demand == 'dynamic':
            self.v_schedule = self.gen_dynamic_demand(mode)
            self.gen_vehicles = self.gen_dynamic
        elif demand == 'custom':
            self.gen_vehicles = self.gen_custom
        else:
            raise ValueError('invalid demand type')
        
    def run_at_start(self):
        # initialize vehicle states for consensus
        self.veh_names = ["bus_0", "bus_1", "bus_2"]
        self.veh_states = {bus_id : np.random.randn() for bus_id in self.veh_names}
        print(self.conn.getVersion())
        # create lines connecting buses to visualize communication
        bus_ids = self.get_bus_ids()
        for i in range(len(bus_ids)):
            for j in range(i+1, len(bus_ids)):
                    self.conn.polygon.add(f"line_{i}_{j}", [(-100., 0.), (100., 0.)], color=(255, 0, 0, 0), lineWidth=0.5, layer=10)

    def run(self):
        # this runs only once
        if self.t == 1:
            self.run_at_start()

        self.gen_vehicles()
        self.t += 1

    def gen_dynamic(self):
        ###get next set of edges from v schedule, use them to add new vehicles
        ###this is batch vehicle generation
        try:
            new_veh_edges = next(self.v_schedule)
            self.gen_veh( new_veh_edges  )
        except StopIteration:
            print('no vehicles left')

    def gen_dynamic_demand(self, mode):
        ###use sine wave as rate parameter for dynamic traffic demand
        t = np.linspace(1*np.pi, 2*np.pi, self.sim_len)                                          
        sine = np.sin(t)+1.55
        ###create schedule for number of vehicles to be generated each second in sim
        v_schedule = []
        second = 1.0
        for t in range(int(self.sim_len)):
            n_veh = 0.0
            while second > 0.0:
                headway = np.random.exponential( sine[t], size=1)
                second -= headway
                if second > 0.0:
                    n_veh += 1
            second += 1.0
            v_schedule.append(int(n_veh))
                                                                                            
        ###randomly shift traffic pattern as a form of data augmentation
        v_schedule = np.array(v_schedule)
        if mode == 'test':
            random_shift = 0
        else:
            random_shift = np.random.randint(0, self.sim_len)
        v_schedule = np.concatenate((v_schedule[random_shift:], v_schedule[:random_shift]))
        ###zero out the last minute for better comparisons because of random shift
        v_schedule[-60:] = 0
        ###randomly select from origins, these are where vehicles are generated
        v_schedule = [ np.random.choice(self.origins, size=int(self.scale*n_veh), replace = True) 
                       if n_veh > 0 else [] for n_veh in v_schedule  ]
        ###fancy iterator, just so we can call next for sequential access
        return v_schedule.__iter__() 

    def add_origin_routes(self):
        for origin in self.origins:
            self.conn.route.add(origin, [origin] )

    def gen_single(self):
        if self.conn.vehicle.getIDCount() == 0:
            ###if no vehicles in sim, spawn 1 on random link
            veh_spawn_edge = np.random.choice(self.origins)
            self.gen_veh( [veh_spawn_edge] )
            
    def gen_custom(self):
        if self.t % 10 == 1:
            pass
            ##every 10 seconds spawn a vehicle
            veh_spawn_edge = np.random.choice(self.origins)
            self.gen_veh( [veh_spawn_edge] )
            
    def get_bus_ids(self):
        return list(filter(lambda t: self.conn.vehicle.getVehicleClass(t) == "bus", self.conn.vehicle.getIDList()))
    
    def get_bus_distance(self, bus_id1, bus_id2):
        return math.sqrt(
            (self.conn.vehicle.getPosition(bus_id1)[0] - self.conn.vehicle.getPosition(bus_id2)[0])**2 +
            (self.conn.vehicle.getPosition(bus_id1)[1] - self.conn.vehicle.getPosition(bus_id2)[1])**2)

    # perform actions of the individual vehicles (get their position, get the distance between them, exchange messages)
    def perform_actions(self):
        bus_IDs = self.get_bus_ids()
        dist_dict = {(v1, v2):  self.get_bus_distance(v1, v2) for v1 in bus_IDs for v2 in bus_IDs if v1 != v2}       
        for i in range(len(bus_IDs)):
            for j in range(i+1, len(bus_IDs)):
                if dist_dict[(bus_IDs[i], bus_IDs[j])] < 100:
                    # print("Bus " + bus_IDs[i] + " is close to Bus " + bus_IDs[j] + " at distance " + str(dist_dict[(bus_IDs[i], bus_IDs[j])]))
                    # print(f"{self.t} {self.veh_states[self.veh_names[0]]=}, {self.veh_states[self.veh_names[1]]=}")
                    # communication and discrete-time consensus
                    self.veh_states[self.veh_names[0]] = 1 / (1 + 1) * (self.veh_states[self.veh_names[0]] + self.veh_states[self.veh_names[1]])
                    self.veh_states[self.veh_names[1]] = 1 / (1 + 1) * (self.veh_states[self.veh_names[1]] + self.veh_states[self.veh_names[0]])
                    # print(f"CLOSE, {self.t} {self.veh_states[self.veh_names[0]]=}, {self.veh_states[self.veh_names[1]]=}")
                    
                    # draw red line between buses
                    bus1_pos = self.conn.vehicle.getPosition(bus_IDs[i])
                    bus2_pos = self.conn.vehicle.getPosition(bus_IDs[j])
                    self.conn.polygon.setShape(f"line_{i}_{j}", [bus1_pos, bus2_pos])
                    self.conn.polygon.setLineWidth(f"line_{i}_{j}", 0.5)
                    self.conn.polygon.setColor(f"line_{i}_{j}", (255, 0, 0, 255))
                    self.conn.polygon.setFilled(f"line_{i}_{j}", False)
                else:
                    self.veh_states[self.veh_names[0]] += 0.4 * (np.random.rand() - 0.5)
                    self.veh_states[self.veh_names[1]] += 0.4 * (np.random.rand() - 0.5)
                    # print(f"{self.t} {self.veh_states[self.veh_names[0]]=}, {self.veh_states[self.veh_names[1]]=}")

                    # make lines between buses invisible
                    bus1_pos = self.conn.vehicle.getPosition(bus_IDs[i])
                    bus2_pos = self.conn.vehicle.getPosition(bus_IDs[j])
                    self.conn.polygon.setShape(f"line_{i}_{j}", [bus1_pos, bus2_pos])
                    self.conn.polygon.setLineWidth(f"line_{i}_{j}", 0.)
                    self.conn.polygon.setColor(f"line_{i}_{j}", (255, 0, 0, 0))
                    self.conn.polygon.setFilled(f"line_{i}_{j}", True)

        
    def gen_veh( self, veh_edges ):
        for e in veh_edges:
            vid = e+str(self.vehicles_created)
            # self.conn.vehicle.addFull( vid, e, departLane="best", typeID="bus")
            self.conn.vehicle.addFull( vid, e, departLane="best")
            self.set_veh_route(vid)
            self.vehicles_created += 1

    def set_veh_route(self, veh):
        current_edge = self.conn.vehicle.getRoute(veh)[0]
        route = [current_edge]
        while current_edge not in self.destinations:
            next_edge = np.random.choice(self.netdata['edge'][current_edge]['outgoing'])
            route.append(next_edge)
            current_edge = next_edge
        self.conn.vehicle.setRoute( veh, route )    