import numpy as np
import random
import math

class HypothesisSpaceTracker:
    def __init__(self, possible_rules):
        self.possible_rules = possible_rules                                                       
        self.remaining_hypotheses = set(possible_rules.values())
        self.total_hypotheses = len(possible_rules)
        self.total_explored = 0

    def update(self, x, y, z, result):
        pass                                                                   
        newly_explored = 0
        for rule in list(self.remaining_hypotheses):
            try:
                if rule(x, y, z) != result:
                    self.remaining_hypotheses.remove(rule)
                    newly_explored += 1
            except Exception as e:
                print(f"Caught exception: {e}, applying {x, y, z, result} ignoring")

        self.total_explored = (self.total_hypotheses - len(self.remaining_hypotheses)) / self.total_hypotheses
        newly_explored_percentage = newly_explored / self.total_hypotheses
        return newly_explored_percentage, self.total_explored
    
    def update_single_arg(self, x, result):
        pass                                                                                       
        newly_explored = 0
        for rule in list(self.remaining_hypotheses):
            if rule(x) != result:
                self.remaining_hypotheses.remove(rule)
                newly_explored += 1

        self.total_explored = (self.total_hypotheses - len(self.remaining_hypotheses)) / self.total_hypotheses
        newly_explored_percentage = newly_explored / self.total_hypotheses
        return newly_explored_percentage, self.total_explored


    def visualize_space(self):
        pass                                                                                       
        grid_size = int(np.ceil(np.sqrt(self.total_hypotheses)))
        grid = np.zeros((grid_size, grid_size))
        remaining = list(self.remaining_hypotheses)

        for i in range(len(remaining)):
            grid[i // grid_size, i % grid_size] = 1

        viz = "\n".join(" ".join("■" if cell else "□" for cell in row) for row in grid)
        return viz
    
    def compute_threshold(self):
        base_threshold = max(0.01, min(0.1, 1 / math.log(self.total_hypotheses)))
        return base_threshold * (1 - 0.5 * self.total_explored)

def combine_hypotheses(base_hypotheses, generated_hypotheses):
    combined = base_hypotheses.copy()
    
    for key, rule in generated_hypotheses.items():
        if rule not in combined.values():
            combined[key] = rule
    
    return combined

def generate_hypothesis_space(num_hypotheses=50):
    generated_rules = {}
    
    rule_types = [
        'order',
        'equality',
        'inequality',
        'sign',
        'parity',
        'arithmetic',
        'max_min',
        'modulo',
        'rounding',
        'simple_function'
    ]

    for i in range(num_hypotheses):
        rule_type = random.choice(rule_types)

        if rule_type == 'order':
            ops = random.choice(['>', '<', '>=', '<='])
            rule = f"lambda x, y, z: x {ops} y {ops} z"

        elif rule_type == 'equality':
            equal_vars = random.sample(['x', 'y', 'z'], 2)
            rule = f"lambda x, y, z: {equal_vars[0]} == {equal_vars[1]}"

        elif rule_type == 'inequality':
            rule = "lambda x, y, z: x != y and y != z and x != z"

        elif rule_type == 'sign':
            sign = random.choice(['>', '<'])
            rule = f"lambda x, y, z: x {sign} 0 and y {sign} 0 and z {sign} 0"

        elif rule_type == 'parity':
            parity = random.choice([0, 1])
            rule = f"lambda x, y, z: (int(x) % 2 == {parity}) and (int(y) % 2 == {parity}) and (int(z) % 2 == {parity})"

        elif rule_type == 'arithmetic':
            op = random.choice(['+', '-', '*'])
            vars = random.sample(['x', 'y', 'z'], 3)
            rule = f"lambda x, y, z: {vars[0]} {op} {vars[1]} == {vars[2]}"

        elif rule_type == 'max_min':
            func = random.choice(['max', 'min'])
            var = random.choice(['x', 'y', 'z'])
            rule = f"lambda x, y, z: {func}(x, y, z) == {var}"

        elif rule_type == 'modulo':
            mod = random.randint(2, 5)
            remainder = random.randint(0, mod-1)
            rule = f"lambda x, y, z: (int(x) % {mod} == {remainder}) and (int(y) % {mod} == {remainder}) and (int(z) % {mod} == {remainder})"

        elif rule_type == 'rounding':
            round_func = random.choice(['math.floor', 'math.ceil', 'round'])
            rule = f"lambda x, y, z: {round_func}(x) == {round_func}(y) == {round_func}(z)"

        elif rule_type == 'simple_function':
            func = random.choice(['abs', 'math.sin', 'math.cos', 'math.exp'])
            op = random.choice(['>', '<', '=='])
            rule = f"lambda x, y, z: {func}(x) {op} {func}(y) {op} {func}(z)"

        generated_rules[f'generated_{i}'] = eval(rule)

    return generated_rules
