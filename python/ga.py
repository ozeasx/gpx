#!/usr/bin/python
# ozeasx@gmail.com

import time
import random
import logging as log
from collections import defaultdict
from operator import attrgetter
from itertools import combinations
import numpy
from vrp_chromosome import VRP_Chromosome as Chromosome
import functions


# Class to abstract a Genetic algorithm
class GA(object):
    # GA initialization
    def __init__(self, data, xop, fit_func, elitism=0):
        # Parametrization
        self._data = data
        # Crossover operator
        self._xop = xop
        self._elitism = elitism

        # Generation count
        self._generation = -1
        # Average fitness of the current generation
        self._avg_fitness = 0
        # To indicate if pop should be restarted
        self._restart_pop = False
        # Fitness function
        self._fit_func = fit_func
        # Counters amd timers
        self._counters = defaultdict(list)
        self._timers = defaultdict(list)

        # Current population
        self._population = list()
        # Elite population
        self._elite = list()
        # Best solution found
        self._best_solution = None

        # Initialize counters
        self._counters['cross'].append(0)
        self._counters['mut'].append(0)
        self._counters['constructions'].append(0)
        self._counters['destructions'].append(0)
        self._counters['repairs'].append(0)

    # Get current generation number
    @property
    def generation(self):
        return self._generation

    # Average fitness of current generation
    @property
    def avg_fitness(self):
        return self._avg_fitness

    # return best individuals
    @property
    def best_solution(self):
        return self._best_solution

    # Return counters
    @property
    def counters(self):
        return self._counters

    # Return timers
    @property
    def timers(self):
        return self._timers

    # Insert unique solutions into population
    def _insert_pop(self, number, method='random', eval=False):

        # Sub method to generate one unique random chromosome
        def random():
            c = Chromosome(self._data.dimension, self._data.trucks)
            # Avoid duplicates
            while c in self._population:
                c = Chromosome(self._data.dimension, self._data.trucks)
            return c

        # Individuals to be inserted
        for i in xrange(int(number)):
            # Random
            if method == 'random':
                c = random()
                c.dist = self._data.tour_dist(c.tour)
            # 2opt
            elif method == '2opt':
                c = random()
                c = functions.vrp_2opt(c, self._data)
                while c in self._population:
                    c = random()
                    c = functions.vrp_2opt(c, self._data)
            # NN and NN with 2opt
            elif method == 'nn' or 'nn2opt':
                c = functions.nn(self._data, method)
                # Avoid duplicates
                while c in self._population or c is None:
                    c = functions.nn(self._data, method)
            # Insert c in population
            assert c.dist is not None, "ga, _insert_pop, 'dist is none'"
            c.load = self._data.routes_load(c.routes)
            if eval:
                c.fitness = self._evaluate(c)
            self._population.append(c)

    # Generate inicial population
    def gen_pop(self, size, method='random', ratio=1):
        # Regiter local and global start time
        self._start_time = start_time = time.time()
        # Need even population
        assert not (size % 2), "Invalid population size. " \
                               "Must be even and greater than 0"
        # Print step
        print "Generating initial population..."
        # Population generation
        if method == 'random':
            self._insert_pop(size, method)
        else:
            self._insert_pop(size - ratio * size, 'random')
            self._insert_pop(ratio * size, method)
        # Done
        print "Done..."
        # Store execution time
        self._timers['population'].append(time.time() - start_time)
        # Assert population size
        assert size == len(self._population), "ga, gen_pop"
        self._pop_size = size

    # Evaluate the entire population
    def evaluate(self):
        # Register star time
        start_time = time.time()

        # Update fitness of all population
        total_fitness = 0
        for c in self._population:
            c.fitness = self._evaluate(c)
            total_fitness += c.fitness

        # Calc average fitness
        self._counters['avg_fit'].append(total_fitness/float(self._pop_size))

        # Elitism
        if self._elitism:
            # Insert previous elite population
            self._population += self._elite
            # Sort
            self._population.sort(key=attrgetter('fitness'), reverse=True)
            # Save new elite
            self._elite = self._population[:self._elitism]
            # Adjust population size
            self._population = self._population[:self._pop_size]

        # Store best solution found
        if not self._best_solution:
            self._best_solution = max(self._population,
                                      key=attrgetter('fitness'))
        else:
            current_best = max(self._population, key=attrgetter('fitness'))
            if current_best.fitness > self._best_solution.fitness:
                self._best_solution = current_best

        self._counters['best_fit'].append(self._best_solution.fitness)

        # Increment generaion
        self._generation += 1

        # Register execution Timers
        self._timers['evaluation'].append(time.time() - start_time)

    # Calculate the individual fitness
    def _evaluate(self, c):
        # Eliminate infeasible solutions
        if self._fit_func == 'a':
            if any(load > self._data.capacity for load in c.load.values()):
                return -float("inf")
            else:
                return -c.dist
        # Standard deviation
        elif self._fit_func == 'b':
            return -c.dist * numpy.std(c.load.values())
        # Standard deviation squared
        elif self._fit_func == 'c':
            return -c.dist * (numpy.std(c.load.values()) ** 2)
        # Standard deviation if infeasible
        elif self._fit_func == 'd':
            if any(load > self._data.capacity for load in c.load.values()):
                return -c.dist * (numpy.std(c.load.values()))
            else:
                return -c.dist
        # Square of standard deviation if infeasible
        elif self._fit_func == 'e':
            if any(load > self._data.capacity for load in c.load.values()):
                return -c.dist * (numpy.std(c.load.values()) ** 2)
            else:
                return -c.dist

    # Tournament selection
    def tournament_selection(self, k):
        # Register start time
        start_time = time.time()
        # Tournament winners
        selected = list()

        # Tournament
        for i in xrange(self._pop_size):
            # Retrieve k-sized sample
            tournament = random.sample(self._population, k)
            # Get best solution
            selected.append(max(tournament, key=attrgetter('fitness')))

        # Update population
        self._population = selected
        # Regiter execution time
        self._timers['tournament'].append(time.time() - start_time)

        # Assure population size remains the same
        assert len(self._population) == self._pop_size, "Tournament, pop size"

    # Ranking selection
    def rank_selection(self, weight):
        selected = list()
        self._population.sort(key=attrgetter('fitness'))
        weight_list = range(0, self._pop_size, weight)
        for i in xrange(self._pop_size):
            pass

    # Recombination
    def recombine(self, p_cross, pairwise=None):
        # Register start time
        start_time = time.time()

        # Pairwise recombination
        if pairwise == 'True':
            selected = list()
            for pair in combinations(set(self._population), 2):
                selected.extend([pair[0], pair[1]])
            self._population = selected

        # New generation
        children = set()

        # Counters
        cross = 0
        constructions = 0
        destructions = 0

        # Recombination
        for p1, p2 in zip(self._population[0::2], self._population[1::2]):
            # print p1.dist
            if random.random() < p_cross:
                c1, c2 = self._xop.recombine(p1.to_tsp(), p2.to_tsp())
                c1 = c1.to_vrp(self._data.dimension)
                c2 = c2.to_vrp(self._data.dimension)
                c1.load = self._data.routes_load(c1.routes)
                c2.load = self._data.routes_load(c2.routes)
                children.add(c1)
                children.add(c2)
                # Count cross only if there is at least one different child
                if c1 not in [p1, p2] or c2 not in [p1, p2]:
                    cross += 1
                    # Conditions
                    p1f = not any(l > self._data.capacity
                                  for l in p1.load.values())
                    p2f = not any(l > self._data.capacity
                                  for l in p2.load.values())
                    c1f = not any(l > self._data.capacity
                                  for l in c1.load.values())
                    c2f = not any(l > self._data.capacity
                                  for l in c2.load.values())
                    # Count constructions
                    if (not (p1f or p2f)) and (c1f or c2f):
                        constructions += 1
                    # Count destructions
                    if (p1f or p2f) and not (c1f or c2f):
                        destructions += 1

        # Reduce population in case of pairwise recombination
        children = list(children)
        if pairwise == 'True':
            # Reevaluate population
            for c in children:
                c.fitness = self._evaluate(c)
            children.sort(key=attrgetter('fitness'), reverse=True)
            self._population = children[:self._pop_size]
        else:
            self._population = children

        # Update counters
        self._counters['cross'].append(cross)
        self._counters['constructions'].append(constructions)
        self._counters['destructions'].append(destructions)

        # Set restart based on crossover number or best_fit or avg_fit
        if self._generation > 0:
            if ((cross == 0) or (self._counters['avg_fit'][-2]
                                 == self._counters['avg_fit'][-1])
                or (self._counters['best_fit'][-2]
                    == self._counters['best_fit'][-1])):
                self._restart_pop = True

        # Register execution time
        self._timers['recombination'].append(time.time() - start_time)

    # Repopulate with unique solutions
    def repopulate(self, method):
        self._insert_pop(self._pop_size - len(self._population), method)
        # Assure population size remains the same
        assert len(self._population) == self._pop_size, len(self._population)

    # Repair infeasible solutions
    def repair(self):
        fixed = 0
        for i in xrange(self._pop_size):
            if any(l > self._data.capacity for l in
                   self._population[i].load.values()):
                c = functions.fix(self._population[i], self._data)
                c.load = self._data.routes_load(c.routes)
                if not any(l > self._data.capacity for l in c.load.values()):
                    self._population[i] = c
                    fixed += 1
        self._counters['repairs'].append(fixed)

    # Mutate individuals according to p_mut probability
    def mutate(self, p_mut, method):
        # Register start time
        start_time = time.time()
        # Mutations counter
        mut = 0
        # Is map fast?
        for i, c in enumerate(self._population):
            if random.random() < p_mut:
                if method == '2opt':
                    c = functions.vrp_2opt(self._population[i], self._data)
                elif method == 'nn' or method == 'nn2opt':
                    c = functions.nn(self._data, method)
                    # Avoid duplicates
                    while c in self._population or c is None:
                        c = functions.nn(self._data, method)
                if c != self._population[i]:
                    c.load = self._data.routes_load(c.routes)
                    self._population[i] = c
                    mut += 1

        # Update counter
        self._counters['mut'].append(mut)

        # Register execution time
        self._timers['mutation'].append(time.time() - start_time)

    # Reset population
    def restart_pop(self, ratio, method='random'):
        # Register start time
        start_time = time.time()

        if self._restart_pop:
            # Population restarted flag
            self._restart_pop = False
            # Sort pop
            self._population.sort(key=attrgetter('fitness'), reverse=True)
            # Reduce pop to acomodate restart
            self._population = self._population[:int(self._pop_size
                                                     - self._pop_size * ratio)]
            # Insert new population
            self._insert_pop(self._pop_size * ratio, method, eval=True)

        # Register execution time
        self._timers['restart_pop'].append(time.time() - start_time)

        # Assure population size remains the same
        assert len(self._population) == self._pop_size, "ga, restart_pop"

    # Generation info
    def print_info(self):

        log.info("T: %i\tC: %i\tCDF: %i/%i/%i\tM: %i\tAvg: %f\tB: %f\tR: %s",
                 self._generation, self._counters['cross'][-1],
                 self._counters['constructions'][-1],
                 self._counters['destructions'][-1],
                 self._counters['repairs'][-1],
                 self._counters['mut'][-1], self._counters['avg_fit'][-1],
                 self._counters['best_fit'][-1], self._restart_pop)

    # Final report
    def report(self):
        self._timers['total'].append(time.time() - self._start_time)
        log.info("----------------------- Statitics -------------------------")
        log.info("Total Crossover: %i", sum(self._counters['cross']))
        log.info("Constructions: %i", sum(self._counters['constructions']))
        log.info("Destructions: %i", sum(self._counters['destructions']))
        log.info("Repairs: %i", sum(self._counters['repairs']))
        log.info("Failed: %i", self._xop.counters['failed'])
        parents_sum = self._xop.counters['parents_sum']
        children_sum = self._xop.counters['children_sum']
        if parents_sum != 0:
            log.info("Overall improvement: %f", (parents_sum - children_sum)
                     / float(parents_sum) * 100)
        log.info("Partitions")
        log.info(" Feasible type 1: %i", self._xop.counters['feasible_1'])
        log.info(" Feasible type 2: %i", self._xop.counters['feasible_2'])
        log.info(" Feasible type 3: %i", self._xop.counters['feasible_3'])
        log.info(" Infeasible: %i", self._xop.counters['infeasible'])
        log.info(" Fusions: %i", self._xop.counters['fusions'])
        log.info(" Unsolved: %i", self._xop.counters['unsolved'])
        log.info("Infeasible tours: %i", self._xop.counters['inf_tours'])
        log.info("Total mutations: %i", sum(self._counters['mut']))
        log.info("--------------------- Time statistics----------------------")
        log.info("Total execution time: %f", sum(self._timers['total']))
        log.info("Inicial population: %f", sum(self._timers['population']))
        log.info("Evaluation: %f", sum(self._timers['evaluation']))
        log.info("Selection: %f", sum(self._timers['tournament']))
        log.info("Recombination: %f", sum(self._timers['recombination']))
        log.info(" Partitioning: %f",
                 sum(self._xop.timers['partitioning']))
        log.info(" Simplified graph: %f",
                 sum(self._xop.timers['simple_graph']))
        log.info(" Classification: %f",
                 sum(self._xop.timers['classification']))
        log.info(" Fusion: %f", sum(self._xop.timers['fusion']))
        log.info(" Build: %f", sum(self._xop.timers['build']))
        log.info("Mutation: %f", sum(self._timers['mutation']))
        log.info("Population restart: %f", sum(self._timers['restart_pop']))
        log.info("Capcity: %f", self._data.capacity)
        if self._data.best_solution:
            log.info("---------------- Best known solution ------------------")
            log.info("Tour: %s", (self._data.best_solution.tour,))
            log.info("Distance: %f", self._data.best_solution.dist)
            log.info("Load: %s", (self._data.best_solution.load.values()))
        log.info("------------------- Best individual found -----------------")
        log.info("Tour: %s", (self._best_solution.tour,))
        log.info("Distance: %f", self._best_solution.dist)
        log.info("Load: %s", (self._best_solution.load.values()))
        log.info("-----------------------------------------------------------")
