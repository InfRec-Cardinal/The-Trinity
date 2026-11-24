import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

from spatial.build import Blocks
from .sim_common import (
    parse_simulation_paths,
    parse_task_metadata,
    load_block_data,
    calculate_total_mass,
    clean_simulation_data,
    analyze_motion_metrics,
    analyze_target_trajectory_quality,
    extract_round_suffix,
    save_analysis_result
)

                                  
DISTANCE_THRESHOLD = 10.0                                               
START_POSITION = np.array([0.0, 0.0, 0.0])
TARGET_POSITION = np.array([10.0, 10.0, 0.0])
START_TIME_SPEED = 2.0
START_TIME_TRAJECTORY = 2.0
WHEEL_DISTANCE_THRESHOLD = 1.0                                            
INITIAL_HEIGHT_THRESHOLD = 20.0                                                      

def analyze_simulation_transport(machine_dir: str, sim_round: Optional[int] = None, verbose: bool = False) -> Dict[str, Any]:
    pass                                                                         
    
         
                                                             
                                                                                              
                                                      
        
            
                                                                          
                                                                              
        
           
                                                        
                                         
       
    try:
        all_blocks = Blocks()
        
                                     
        paths = parse_simulation_paths(machine_dir, sim_round)
        metadata = parse_task_metadata(machine_dir)
        
        if verbose:
            print(f"Task: {metadata['task_name']}")
            print(f"Category: {metadata['category']}, Level: {metadata['level']}")
            print(f"Model: {metadata['model_name']}")
            print(f"Machine ID: {metadata['machine_id']}")
        
                                     
        block_data = load_block_data(paths['block_json_path'])
        total_mass = calculate_total_mass(block_data, all_blocks)
        
        if verbose:
            print(f"Block data: {block_data}")
            print(f"Total mass: {total_mass}")
        
                                                                  
        position_df = clean_simulation_data(paths['simulation_csv_path'])
        
                                                                       
        target_id, target_stats = _determine_tracking_target(position_df, verbose)
        
                                                             
        wheel_stats = _analyze_wheel_consistency(
            position_df, block_data, verbose
        )
        
                                
        motion_stats = analyze_motion_metrics(
            paths['simulation_csv_path'], START_TIME_SPEED, verbose
        )
        
                                                            
        trajectory_stats = analyze_target_trajectory_quality(
            paths['simulation_csv_path'], target_id, START_POSITION, TARGET_POSITION, 
            START_TIME_TRAJECTORY, verbose
        )
        
                                                                             
        max_transport_distance = target_stats['max_distance_from_start']
        
                                                                   
        passed = max_transport_distance > DISTANCE_THRESHOLD
        if metadata['level'] == "soft":
            passed = passed and wheel_stats['wheel_count'] >= 4
        
        initial_max_height = target_stats['initial_max_height']
        passed = passed and initial_max_height < INITIAL_HEIGHT_THRESHOLD
                    
        if passed and wheel_stats['wheel_count'] == 0:
            hacked = True
        else:
            hacked = False
            
        if initial_max_height > INITIAL_HEIGHT_THRESHOLD:
            hacked = True
        
                                              
        round_suffix = extract_round_suffix(paths)
        
                         
        result = {
            "pass": passed,
            "hacked": hacked,
            "category": metadata['category'],
            "level": metadata['level'],
            "model_name": metadata['model_name'],
            "machine_id": metadata['machine_id'],
            "round_suffix": round_suffix,
            "machine_bsg_path": paths['machine_bsg_path'],
            "machine_json_path": paths['machine_json_path'],
            "num_blocks": len(block_data),
            "total_mass": total_mass,
            "tracking_target": target_id,
            "max_transport_distance": max_transport_distance,
            "final_position": target_stats['final_position'],
            "initial_max_height": target_stats['initial_max_height'],
            "one_piece": wheel_stats['one_piece'],
            "wheel_count": wheel_stats['wheel_count'],
            "max_wheel_distance_variation": wheel_stats['max_distance_variation'],
            "max_height": motion_stats['max_height'],
            "max_speed": motion_stats['max_speed'],
            "max_progress_ratio": trajectory_stats['max_progress_ratio'],
            "direction_consistency": trajectory_stats['direction_consistency'],
            "backtrack_penalty": trajectory_stats['backtrack_penalty'],
            "lateral_deviation": trajectory_stats['lateral_deviation'],
            "path_efficiency": trajectory_stats['path_efficiency'],
            "final_distance_ratio": trajectory_stats['final_distance_ratio'],
            "hyperparameters": {
                "DISTANCE_THRESHOLD": DISTANCE_THRESHOLD,
                "START_TIME_SPEED": START_TIME_SPEED,
                "START_TIME_TRAJECTORY": START_TIME_TRAJECTORY,
                "START_POSITION": START_POSITION.tolist(),
                "TARGET_POSITION": TARGET_POSITION.tolist(),
                "WHEEL_DISTANCE_THRESHOLD": WHEEL_DISTANCE_THRESHOLD,
                "INITIAL_HEIGHT_THRESHOLD": INITIAL_HEIGHT_THRESHOLD
            }
        }
        
        if verbose:
            print(f"Analysis result: {result}")
            
        return result
        
    except Exception as e:
        raise ValueError(f"Failed to analyze simulation: {str(e)}") from e


def _determine_tracking_target(position_df: pd.DataFrame, verbose: bool = False) -> Tuple[str, Dict[str, Any]]:
    pass                                                                                                        
    
         
                                                    
                                                      
        
            
                                          
       
                                            
    unique_ids = position_df['id'].unique()
    has_ballast = 'ID_Ballast' in unique_ids
    
    target_id = 'ID_Ballast' if has_ballast else 'ID_1'
    
    if verbose:
        print(f"Available IDs: {sorted(unique_ids)}")
        print(f"Tracking target: {target_id}")
    
                                
    target_df = position_df[position_df['id'] == target_id].copy()
    
    if target_df.empty:
        if verbose:
            print(f"Warning: No data found for target {target_id}")
        return target_id, {
            'max_distance_from_start': 0.0,
            'final_position': [0.0, 0.0, 0.0],
            'initial_max_height': 0.0
        }
    
                  
    target_df = target_df.sort_values('time').reset_index(drop=True)
    
                                             
    positions = target_df[['x', 'y']].values
    distances_from_start = np.linalg.norm(positions - START_POSITION[:2], axis=1)
    
    max_distance_from_start = float(np.max(distances_from_start))
    final_position = positions[-1].tolist()
    
                                                                      
    initial_max_height = float(target_df['z'][:int(START_TIME_SPEED)].max())
    
    if verbose:
        print(f"Target {target_id} max transport distance: {max_distance_from_start:.3f}")
        print(f"Target {target_id} final position: {final_position}")
    
    return target_id, {
        'max_distance_from_start': max_distance_from_start,
        'final_position': final_position,
        'initial_max_height': initial_max_height
    }


def _analyze_wheel_consistency(position_df: pd.DataFrame, block_data: Dict[str, str], 
                              verbose: bool = False) -> Dict[str, Any]:
    pass                                                                                      
    
         
                                                    
                                            
                                                      
        
            
                                                       
       
                    
    wheel_ids = [f"ID_{block_id}" for block_id, block_name in block_data.items() 
                 if "Wheel" in block_name]
    
    if verbose:
        print(f"Wheel IDs found: {wheel_ids}")
    
    if len(wheel_ids) < 2:
                                                                    
        return {
            'one_piece': True,
            'wheel_count': len(wheel_ids),
            'max_distance_variation': 0.0
        }
    
                                          
    wheel_df = position_df[position_df['id'].isin(wheel_ids)].copy()
    
    if wheel_df.empty or len(wheel_df['id'].unique()) < 2:
        return {
            'one_piece': True,
            'wheel_count': len(wheel_ids),
            'max_distance_variation': 0.0
        }
    
                                                                   
    max_distance_variation = 0.0
    
                                                               
    for time_val, time_group in wheel_df.groupby('time'):
        if len(time_group) < 2:
            continue
            
                                                      
        wheel_positions = {}
        for _, row in time_group.iterrows():
            wheel_positions[row['id']] = np.array([row['x'], row['y'], row['z']])
        
                                          
        wheel_list = list(wheel_positions.keys())
        distances = []
        for i in range(len(wheel_list)):
            for j in range(i + 1, len(wheel_list)):
                dist = np.linalg.norm(wheel_positions[wheel_list[i]] - wheel_positions[wheel_list[j]])
                distances.append(dist)
        
        if distances:
                                                              
            distance_variation = float(np.std(distances))
            max_distance_variation = max(max_distance_variation, distance_variation)
    
                                                                             
    one_piece = max_distance_variation <= WHEEL_DISTANCE_THRESHOLD
    
    if verbose:
        print(f"Wheel consistency analysis:")
        print(f"  Wheel count: {len(wheel_ids)}")
        print(f"  Max distance variation: {max_distance_variation:.3f}")
        print(f"  One piece: {one_piece}")
    
    return {
        'one_piece': one_piece,
        'wheel_count': len(wheel_ids),
        'max_distance_variation': max_distance_variation
    }


def main(machine_dir: str, sim_round: int, verbose: bool):
    pass                                         
    result = analyze_simulation_transport(machine_dir, sim_round=sim_round, verbose=verbose)
    
                                             
    save_path = save_analysis_result(result)
    print(f"Result saved to {save_path}")

    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine_dir", type=str, required=True)
    parser.add_argument("--sim_round", type=int, default=1, required=False)
    parser.add_argument("--verbose", action="store_true", required=False, default=False)
    args = parser.parse_args()
    main(args.machine_dir, args.sim_round, args.verbose)
