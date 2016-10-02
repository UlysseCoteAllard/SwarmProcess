import numpy as np
from Swarm import Swarm
import FitnessFunction
from sklearn.cluster import KMeans
import math
from FunctionEstimator import FunctionEstimator

class SwarmProcess(object):
    '''
    lower_bound and upper_bound refer to the min and max of the function to optimize respectively.
    number_of_genes correspond to the number of dimensions of the function to optimize.
    population_size Number of creature in a population
    number_of_generation correspond to the number of the main loop the algorithm will do
    '''
    def __init__(self, lower_bound, upper_bound, number_of_dimensions, number_of_real_evaluation, swarm_size,
                 number_of_generation_swarm, fitness_function, inertia_factor=0.5, self_confidence=1.5,
                 swarm_confidence=1.5, sense_of_adventure=1.5):
        self._number_of_real_evaluation = number_of_real_evaluation
        self._random = np.random.RandomState()
        self._number_of_dimensions = number_of_dimensions
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound
        self._number_of_generation_swarm = number_of_generation_swarm

        #Swarm hyper-parameters
        self._inertia_factor = inertia_factor
        self._self_confidence = self_confidence
        self._swarm_confidence = swarm_confidence
        self._sense_of_adventure = sense_of_adventure

        # We remove two for the swarm size.
        # Because the first step of the algorithm is to add two creatures which cover the space
        # in the most efficient manner.
        self._swarm_size = swarm_size-2

        self._fitness_function = fitness_function

        self._regressor = FunctionEstimator(get_EI=True)

        # Create the main swarm responsible to explore the function
        self._swarm = Swarm(swarm_size=self._swarm_size, number_of_dimensions=self._number_of_dimensions,
                            lower_bound=self._lower_bound, upper_bound=self._upper_bound, random=self._random)

        self._list_real_evaluation_position = []
        self._list_real_evaluation_fitness = []


    def run_swarm_process(self):
        # First we find the combination of creature that cover the space the more thoroughly.
        # To achieve that, we use KMEANS with k=2 on the list of creature position.
        kmeans = KMeans(n_clusters=2)

        swarm_positions = self._swarm.get_list_position()  # Get the list of point in the space for KMeans
        kmeans.fit(swarm_positions)  # Train KMeans
        centers = kmeans.cluster_centers_  # Get the centers
        print "Centers: ", centers

        # Add two new creatures with their position corresponding to the centers of kmeans.
        creature0_position = centers[0]
        creature0_fitness = FitnessFunction.calculate_fitness(self._fitness_function, creature0_position,
                                                              self._number_of_dimensions)
        self._number_of_real_evaluation -= 1  # Did a real evaluation

        creature1_position = centers[1]
        creature1_fitness = FitnessFunction.calculate_fitness(self._fitness_function, creature1_position,
                                                              self._number_of_dimensions)
        self._number_of_real_evaluation -= 1  # Did a real evaluation

        self._swarm.add_creature_to_swarm(position=creature0_position)
        self._swarm.add_creature_to_swarm(position=creature1_position)

        # Add the creatures position and fitness to the list of position and fitness evaluated
        self._list_real_evaluation_position.append(creature0_position)
        self._list_real_evaluation_fitness.append(creature0_fitness)
        self._list_real_evaluation_position.append(creature1_position)
        self._list_real_evaluation_fitness.append(creature1_fitness)

        # Train the regressor
        self._regressor.train(self._list_real_evaluation_position, self._list_real_evaluation_fitness)

        # From here, we alternate between exploration and exploitation randomly based on an heuristic except for the
        # Very first pass where we for the algorithm to be in exploration mode for one more evaluation
        # (3 evaluations total)
        self.exploration()
        self._number_of_real_evaluation -= 1  # Did a real evaluation

        # Now that we have three points evaluated, we are ready to start the algorithm for the requested amount of real
        # evaluations. Or until the user stop the program
        for generation in range(self._number_of_real_evaluation):
            # Decide if we explore or exploite.
            exploitation_threshold = max(0.2, 1/math.sqrt((generation+2)/2))
            exploitation_threshold = 5.0
            if self._random.rand() < exploitation_threshold:
                best_creature_ever = self.exploration()

                # TODO once the exploitation algorithm is finish. Remove the if/else and move this block after
                # We are almost done with this generation, get the real value of the point of interest found
                new_point_to_add_fitness = FitnessFunction.calculate_fitness(self._fitness_function,
                                                                             best_creature_ever.get_position(),
                                                                             self._number_of_dimensions)
                # Finish the generation by adding the new creature to the list and updating the regressor
                self._list_real_evaluation_position.append(best_creature_ever.get_position())
                self._list_real_evaluation_fitness.append(new_point_to_add_fitness)
                self._regressor.update_regressor(self._list_real_evaluation_position,
                                                 self._list_real_evaluation_fitness)
                print "Smallest point found: ", new_point_to_add_fitness, "Fitness found by the PSO:", \
                    best_creature_ever.get_fitness()," At position: ", best_creature_ever.get_position()
                # Reset swarm fitness
                self._swarm.reset_swarm()
            else:
                best_creature_ever = self.exploitation()

        index = self._list_real_evaluation_fitness.index(min(self._list_real_evaluation_fitness))
        print "Smallest point found: ", self._list_real_evaluation_fitness[index], " At position: ", \
            self._list_real_evaluation_position[index]

    def exploration(self):
        print "EXPLORATION"
        # We want to get EI
        self._regressor.set_EI_bool(True)
        # We want to get the curiosity
        self._swarm.set_curiosity(True)
        # Make sure that every creature has been evaluated
        best_fitness = min(self._list_real_evaluation_fitness)
        print "BEST CURRENT FITNESS", best_fitness
        self._swarm.evaluate_fitness_swarm(fitness_function=self._regressor, best_real_function_value=best_fitness)

        # run swarm optimization with number of iterations.
        best_creature_ever = self._swarm.run_swarm_optimization(max_iterations=self._number_of_generation_swarm,
                                                                function_to_optimize=self._regressor,
                                                                inertia_factor=self._inertia_factor,
                                                                self_confidence=self._self_confidence,
                                                                swarm_confidence=self._swarm_confidence,
                                                                sense_of_adventure=self._sense_of_adventure,
                                                                best_real_function_value=best_fitness)
        return best_creature_ever

    def exploitation(self):
        print "EXPLOITATION"
        # Finish exploration by updating the regressor
        # We don't want to get EI
        self._regressor.set_EI_bool(False)
        #We don't want to allow curiosity
        self._swarm.set_curiosity(False)

        self._regressor.update_regressor(self._list_real_evaluation_position, self._list_real_evaluation_fitness)
        return 0.0

lower_bound = np.array([-5.0, 10.0])
upper_bound = np.array([0.0, 15.0])
number_of_dimensions = 2
number_of_real_evaluation = 100
swarm_size = 100
number_of_generation_swarm = 100
swarmProcess = SwarmProcess(lower_bound=lower_bound, upper_bound=upper_bound, number_of_dimensions=number_of_dimensions,
                            number_of_real_evaluation=number_of_real_evaluation, swarm_size=swarm_size,
                            number_of_generation_swarm=number_of_generation_swarm,
                            fitness_function=FitnessFunction.branin, inertia_factor=0.5, self_confidence=1.5,
                            swarm_confidence=1.5, sense_of_adventure=1.5)
swarmProcess.run_swarm_process()