                                                                           

                                                                        
                                                                      
                                                                       
                                                                  
            

                                                                    
                                                                 
                                        
   

import numpy as np
from typing import Callable

                                                                  
                                                                       
                          
_DEFAULT_TIMES = [round(0.5 * i, 2) for i in range(1, 11)]


def _round_list(arr, decimals=4):
    return [round(float(x), decimals) for x in np.asarray(arr).ravel()]


def _round_pairs(arr, decimals=4):
    return [[round(float(x), decimals), round(float(y), decimals)] for x, y in arr]


def sample_two_particle(rng: np.random.Generator) -> dict:
    pass                                               

                                                                        
                                                                     
       
    for _ in range(50):
        pos2 = rng.uniform(-10.0, 10.0, 2)
        if np.linalg.norm(pos2) >= 0.5:
            break
    return {
        "p1": round(float(rng.uniform(0.1, 10.0)), 4),
        "p2": round(float(rng.uniform(0.1, 10.0)), 4),
        "pos2": _round_list(pos2),
        "velocity2": _round_list(rng.uniform(-5.0, 5.0, 2)),
        "measurement_times": list(_DEFAULT_TIMES),
    }


def _sample_probes(rng: np.random.Generator, n: int = 5) -> dict:
    return {
        "probe_positions": _round_pairs(rng.uniform(-10.0, 10.0, (n, 2))),
        "probe_velocities": _round_pairs(rng.uniform(-5.0, 5.0, (n, 2))),
        "measurement_times": list(_DEFAULT_TIMES),
    }


def _sample_probes_with_masses(rng: np.random.Generator, n: int = 5) -> dict:
                                                                           
                                                                               
                                                                   
    mass_choices = np.array([1.0, 2.0, 4.0])
    return {
        "probe_positions": _round_pairs(rng.uniform(-10.0, 10.0, (n, 2))),
        "probe_velocities": _round_pairs(rng.uniform(-5.0, 5.0, (n, 2))),
        "probe_masses": _round_list(rng.choice(mass_choices, size=n)),
        "measurement_times": list(_DEFAULT_TIMES),
    }


def sample_dark_matter(rng: np.random.Generator) -> dict:
    return _sample_probes(rng, n=5)


def sample_three_species(rng: np.random.Generator) -> dict:
    return _sample_probes(rng, n=5)


def sample_ether(rng: np.random.Generator) -> dict:
    return _sample_probes_with_masses(rng, n=5)


def sample_hubble(rng: np.random.Generator) -> dict:
    return _sample_probes_with_masses(rng, n=5)


def sample_coulomb_hard(rng: np.random.Generator, n: int = 10) -> dict:
    pass                                                               
    return {
        "positions": _round_pairs(rng.uniform(-10.0, 10.0, (n, 2))),
        "velocities": _round_pairs(rng.uniform(-3.0, 3.0, (n, 2))),
        "charges": _round_list(rng.uniform(-3.0, 3.0, n)),
        "measurement_times": list(_DEFAULT_TIMES),
    }


def sample_species(rng: np.random.Generator) -> dict:
    pass                                                                    
    return {
        "positions": _round_pairs(rng.uniform(-10.0, 10.0, (6, 2))),
        "velocities": _round_pairs(rng.uniform(-5.0, 5.0, (6, 2))),
        "measurement_times": list(_DEFAULT_TIMES),
    }


def sample_circle(rng: np.random.Generator) -> dict:
    pass                                                                          
    return {
        "ring_radius": round(float(rng.uniform(2.0, 10.0)), 4),
        "initial_tangential_velocity": round(float(rng.uniform(-3.0, 3.0)), 4),
        "measurement_times": list(_DEFAULT_TIMES),
    }


_SAMPLERS: dict[str, Callable[[np.random.Generator], dict]] = {
    "gravity": sample_two_particle,
    "yukawa": sample_two_particle,
    "fractional": sample_two_particle,
    "diffusion": sample_two_particle,
    "wave": sample_two_particle,
    "oscillator": sample_two_particle,
    "extra_dimensions": sample_two_particle,
    "coulomb_easy": sample_two_particle,
    "coulomb_hard": sample_coulomb_hard,
    "dark_matter": sample_dark_matter,
    "three_species": sample_three_species,
    "ether": sample_ether,
    "hubble": sample_hubble,
    "species": sample_species,
    "circle": sample_circle,
}


def make_random_generator(world: str, seed=None) -> Callable[[], dict]:
    pass                                                                 

         
                                                                          
                                                                         
                                                                         
                                                                 
       
    if world not in _SAMPLERS:
        raise ValueError(
            f"No random sampler registered for world '{world}'. "
            f"Available: {sorted(_SAMPLERS)}"
        )
    rng = np.random.default_rng(seed)
    sampler = _SAMPLERS[world]

    def generator() -> dict:
        return sampler(rng)

    return generator
