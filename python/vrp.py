#!/usr/bin/python
# ozeasx@gmail.com

from tsp import TSPLIB
from shell import Shell


class VRP(TSPLIB):
    def __init__(self, instance_path):
        # Call super init
        TSPLIB.__init__(self, instance_path)

        # Set capacity
        self._capacity = int(Shell.run("grep CAPACITY " + instance_path
                                       + " | cut -d':' -f2").strip())
        # Mim number of vehicles
        self._trucks = int(Shell.run("grep TRUCKS " + instance_path
                                     + " | cut -d':' -f2").strip())

        # Load demand
        with open(instance_path) as instance:
            read = False
            self._demand = list()
            for word in instance:
                # End loop if EOF
                if word.strip() == "DEPOT_SECTION":
                    break
                # If do, store tour
                if read:
                    s = word.split()
                    self._demand.append(int(s[1]))
                # If DEMAND_SECTION, set 'read'
                if word.strip() == "DEMAND_SECTION":
                    read = True

    # Get vehicles capacity
    @property
    def capacity(self):
        return self._capacity

    # Get min number of vehicles
    @property
    def trucks(self):
        return self._trucks

    # Get tour demand
    def tour_demand(self, tour):
        demand = 0
        for i in tour:
            demand += self._demand[i - 1]
        return demand


# Test section
if __name__ == '__main__':
    vrp = VRP("../cvrp/F-n45-k4.vrp")
    print vrp._capacity
    print vrp._trucks
    print vrp.tour_demand([1, 2, 3])