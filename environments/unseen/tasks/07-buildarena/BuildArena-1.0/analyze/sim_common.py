                                                                
   

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import re
import shutil

from spatial.build import Blocks


def parse_simulation_paths(machine_dir: str, sim_round: Optional[int] = None) -> Dict[str, str]:
    pass                                                                           
    
         
                                                             
                                                                                          
        
            
                                                       
        
                                        
                                                                 
                                                                    
       
    machine_id = os.path.basename(machine_dir)
    
    def _build_paths(suffix: str) -> Dict[str, str]:
        pass                                
        return {
            'machine_bsg_path': os.path.join(machine_dir, f"{machine_id}_sim{suffix}.bsg"),
            'machine_json_path': os.path.join(machine_dir, f"{machine_id}_sim{suffix}.json"),
            'block_json_path': os.path.join(machine_dir, f"block_id_{machine_id}_sim{suffix}.json"),
            'simulation_csv_path': os.path.join(machine_dir, f"simulation_log_{machine_id}_sim{suffix}.csv"),
        }
    
                                                     
    if sim_round is not None:
        return _build_paths(f"_{sim_round}")
    
                                                  
    standard_paths = _build_paths("")
    if all(os.path.exists(path) for path in standard_paths.values()):
        return standard_paths
    
                                                               
    for round_num in range(1, 10):                    
        numbered_paths = _build_paths(f"_{round_num}")
        if all(os.path.exists(path) for path in numbered_paths.values()):
            return numbered_paths
    
                                                                                           
    return standard_paths


def parse_task_metadata(machine_dir: str) -> Dict[str, str]:
    pass                                               
    task_name = os.path.basename(os.path.dirname(os.path.dirname(machine_dir)))
    task_parts = task_name.split("_")
    
    return {
        'task_name': task_name,
        'category': task_parts[0],
        'level': task_parts[1],
        'model_name': "_".join(task_parts[2:-3]),
        'machine_id': os.path.basename(machine_dir),
    }


def load_block_data(block_json_path: str) -> Dict[str, str]:
    pass                                 
    try:
        with open(block_json_path, "r", encoding='utf-8') as f:
            block_id_json = json.load(f)
        return {k: v for d in block_id_json for k, v in d.items() if v != "Ballast"}
    except FileNotFoundError:
        raise FileNotFoundError(f"Block data file not found: {block_json_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in block data file: {e}")


def calculate_total_mass(block_data: Dict[str, str], all_blocks: Blocks) -> float:
    pass                                     
    try:
        return sum(all_blocks.blocks[block_name]["weight"] 
                  for block_name in block_data.values() if block_name != "Ballast")
    except KeyError as e:
        raise ValueError(f"Unknown block type in mass calculation: {e}")


def robust_read_csv(simulation_csv_path: str, 
                   min_columns: int = 5, 
                   validate_numeric_columns: Optional[list] = None,
                   skip_to_first_valid: bool = True) -> pd.DataFrame:
    pass                                                                   
    
                                                                                    
                                                        
                                                             
                                                  
    
         
                                                 
                                                               
                                                                                         
                                                                   
                                                                               
                                                                                       
        
            
                                 
       
    try:
                                                               
        df = pd.read_csv(simulation_csv_path, header=None)
        
                                                                  
                                                     
        if min_columns > 0:
            df = df.dropna(subset=df.columns[:min_columns])
            
        if validate_numeric_columns:
            for col_idx in validate_numeric_columns:
                if col_idx < len(df.columns):
                                                                                  
                    df = df[pd.to_numeric(df.iloc[:, col_idx], errors='coerce').notna()]
                    
        return df
        
    except pd.errors.ParserError:
                                                                   
        rows = []
        found_valid_start = False
        
        with open(simulation_csv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:                    
                    continue
                    
                parts = line.split(',')
                
                                                  
                if len(parts) < min_columns:
                    continue
                
                                                       
                if validate_numeric_columns:
                    valid_row = True
                    for col_idx in validate_numeric_columns:
                        if col_idx < len(parts):
                            try:
                                float(parts[col_idx])
                            except (ValueError, IndexError):
                                valid_row = False
                                break
                    if not valid_row:
                        continue
                
                                                  
                if skip_to_first_valid and not found_valid_start:
                    found_valid_start = True
                    rows.append(parts)
                elif not skip_to_first_valid or found_valid_start:
                    rows.append(parts)
        
        if not rows:
            raise ValueError(f"No valid rows found in {simulation_csv_path} with min_columns={min_columns}")
        
                                          
        df = pd.DataFrame(rows)
                                                    
        return df

def clean_simulation_data(simulation_csv_path: str) -> pd.DataFrame:
    pass                                                                                           
    
         
                                                            
        
            
                                                          
       
    try:
                                                            
        cleaned_df = robust_read_csv(simulation_csv_path)
        cleaned_df.columns = ['time', 'id', 'x', 'z', 'y']
        
                                 
        cleaned_df['time'] = pd.to_numeric(cleaned_df['time'], errors='coerce')
        cleaned_df['x'] = pd.to_numeric(cleaned_df['x'], errors='coerce')
        cleaned_df['z'] = pd.to_numeric(cleaned_df['z'], errors='coerce')
        cleaned_df['y'] = pd.to_numeric(cleaned_df['y'], errors='coerce')
        
                                                      
        cleaned_df = cleaned_df.dropna()
        
                                                       
        cleaned_df = cleaned_df.sort_values(['time', 'id']).reset_index(drop=True)
        
        metadata = parse_task_metadata(os.path.dirname(simulation_csv_path))
        machine_id = metadata['machine_id']
        task_name = metadata['task_name']
        clean_file_name = f"{task_name}_{machine_id}_clean.csv"
        clean_dir = "datacache/analysis_simulation"
        os.makedirs(clean_dir, exist_ok=True)
        clean_file_path = os.path.join(clean_dir, clean_file_name)
        cleaned_df.to_csv(clean_file_path, index=False)
        
        return cleaned_df
        
    except Exception as e:
        raise ValueError(f"Failed to clean simulation data: {e}")


def calculate_max_height(position_df: pd.DataFrame) -> float:
    pass                                                                     
    
         
                                                 
        
            
                                  
       
    if position_df.empty:
        return 0.0
    
    return float(position_df['z'].max())


def calculate_max_speed(position_df: pd.DataFrame, start_time_speed: float = 5.0) -> float:
    pass                                                                        
                                                                                          
    
         
                                                 
                                                                   
        
            
                                                                      
       
    if position_df.empty or len(position_df) < 2:
        return 0.0
    
                                                           
    filtered_df = position_df[position_df['time'] > start_time_speed]
    
    if filtered_df.empty or len(filtered_df) < 2:
        return 0.0
    
    max_speed = 0.0
    
                                                                      
    for block_id, block_data in filtered_df.groupby('id'):
        if len(block_data) < 2:
            continue
            
                                                
        block_data = block_data.sort_values('time').reset_index(drop=True)
        
                                        
        dt = block_data['time'].diff().iloc[1:]                    
        dx = block_data['x'].diff().iloc[1:]                             
        dy = block_data['y'].diff().iloc[1:]                               
        dz = block_data['z'].diff().iloc[1:]                             
        
                                                                    
        valid_mask = dt > 0
        if not valid_mask.any():
            continue
            
        dt_valid = dt[valid_mask]
        dx_valid = dx[valid_mask]
        dy_valid = dy[valid_mask]
        dz_valid = dz[valid_mask]
        
                                                        
        distance_3d = np.sqrt(dx_valid**2 + dy_valid**2 + dz_valid**2)
        speeds = distance_3d / dt_valid
        
                                                               
        block_max_speed = speeds.max()
        if not np.isnan(block_max_speed) and block_max_speed > max_speed:
            max_speed = block_max_speed
    
    return float(max_speed)


def analyze_motion_metrics(simulation_csv_path: str, start_time_speed: float = 5.0, verbose: bool = False) -> Dict[str, float]:
    pass                                                                      
    
         
                                                            
                                                                   
                                                      
        
            
                                                      
       
    try:
                                   
        position_df = clean_simulation_data(simulation_csv_path)
        
        if verbose:
            print(f"Cleaned position data: {len(position_df)} rows")
            print(f"Unique blocks: {position_df['id'].nunique()}")
            print(f"Time range: {position_df['time'].min():.2f} - {position_df['time'].max():.2f}")
            
                                                       
            after_threshold = position_df[position_df['time'] > start_time_speed]
            print(f"Data after {start_time_speed}s for speed calculation: {len(after_threshold)} rows")
        
                                  
        max_height = calculate_max_height(position_df)
        
                                      
        initial_max_height = float(position_df['z'][:int(start_time_speed)].max())
        
                                                                        
        elevation_change_end_time = start_time_speed + 5.0
        elevation_data_slice_1 = position_df[(position_df['time'] > start_time_speed) & (position_df['time'] <= elevation_change_end_time)]
        elevation_data_slice_2 = position_df[(position_df['time'] > elevation_change_end_time) & (position_df['time'] <= elevation_change_end_time + 5.0)]
        if len(elevation_data_slice_1) > 0 and len(elevation_data_slice_2) > 0:
            elevation_change = float(elevation_data_slice_2['z'].max() - elevation_data_slice_1['z'].max())
        else:
            elevation_change = 0.0
        
                                                               
        max_speed = calculate_max_speed(position_df, start_time_speed)
        
                                    
                                                            
        
        if verbose:
            print(f"Maximum height (z): {max_height:.3f}")
            print(f"Initial maximum height: {initial_max_height:.3f}")
            print(f"Maximum speed: {max_speed:.3f}")
            print(f"Elevation change: {elevation_change:.3f}")
        return {
            'max_height': max_height,
            'initial_max_height': initial_max_height,
            'max_speed': max_speed,
            'elevation_change': elevation_change
        }
        
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to analyze motion metrics: {e}")
        return {
            'max_height': 0.0,
            'initial_max_height': 0.0,
            'max_speed': 0.0,
            'elevation_change': 0.0
        }


def analyze_trajectory_quality(simulation_csv_path: str, start_pos: np.ndarray, target_pos: np.ndarray, 
                              start_time_trajectory: float = 0.0, verbose: bool = False) -> Dict[str, float]:
    pass                                                                                     
    
         
                                                            
                                                             
                                                            
                                                                          
                                                      
        
            
                                                        
       
    try:
                                                                  
        position_df = clean_simulation_data(simulation_csv_path)
        filtered_df = position_df[position_df['time'] > start_time_trajectory]
        
        if filtered_df.empty or len(filtered_df) < 2:
            if verbose:
                print("Warning: Insufficient trajectory data for quality analysis")
            return _get_default_trajectory_stats()
        
                                             
        com_trajectory = _calculate_center_of_mass_trajectory(filtered_df)
        
        if len(com_trajectory) < 2:
            return _get_default_trajectory_stats()
        
                                      
        metrics = _calculate_trajectory_metrics(
            com_trajectory, start_pos, target_pos, verbose
        )
        
        if verbose:
            print(f"Trajectory Quality Metrics:")
            print(f"  Max Progress Ratio: {metrics['max_progress_ratio']:.3f}")
            print(f"  Direction Consistency: {metrics['direction_consistency']:.3f}")
            print(f"  Backtrack Penalty: {metrics['backtrack_penalty']:.3f}")
            print(f"  Lateral Deviation: {metrics['lateral_deviation']:.3f}")
            print(f"  Path Efficiency: {metrics['path_efficiency']:.3f}")
            print(f"  Final Distance Ratio: {metrics['final_distance_ratio']:.3f}")
        
        return metrics
        
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to analyze trajectory quality: {e}")
        return _get_default_trajectory_stats()


def analyze_target_trajectory_quality(simulation_csv_path: str, target_id: str, start_pos: np.ndarray, 
                                     target_pos: np.ndarray, start_time_trajectory: float = 0.0, 
                                     verbose: bool = False) -> Dict[str, float]:
    pass                                                                   
    
         
                                                            
                                                                               
                                                             
                                                            
                                                                          
                                                      
        
            
                                                                             
       
    try:
                                                                  
        position_df = clean_simulation_data(simulation_csv_path)
        filtered_df = position_df[position_df['time'] > start_time_trajectory]
        
        if filtered_df.empty or len(filtered_df) < 2:
            if verbose:
                print("Warning: Insufficient trajectory data for quality analysis")
            return _get_default_trajectory_stats()
        
                                     
        target_df = filtered_df[filtered_df['id'] == target_id]
        
        if target_df.empty or len(target_df) < 2:
            if verbose:
                print(f"Warning: No trajectory data found for target {target_id}")
            return _get_default_trajectory_stats()
        
                                      
        target_trajectory = target_df.sort_values('time').reset_index(drop=True)
        
                                      
        metrics = _calculate_trajectory_metrics(
            target_trajectory, start_pos, target_pos, verbose
        )
        
        if verbose:
            print(f"Target {target_id} Trajectory Quality Metrics:")
            print(f"  Max Progress Ratio: {metrics['max_progress_ratio']:.3f}")
            print(f"  Direction Consistency: {metrics['direction_consistency']:.3f}")
            print(f"  Backtrack Penalty: {metrics['backtrack_penalty']:.3f}")
            print(f"  Lateral Deviation: {metrics['lateral_deviation']:.3f}")
            print(f"  Path Efficiency: {metrics['path_efficiency']:.3f}")
            print(f"  Final Distance Ratio: {metrics['final_distance_ratio']:.3f}")
        
        return metrics
        
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to analyze target trajectory quality: {e}")
        return _get_default_trajectory_stats()


def _calculate_center_of_mass_trajectory(position_df: pd.DataFrame) -> pd.DataFrame:
    pass                                                      
    com = (
        position_df.groupby("time")[["x", "y", "z"]]
        .mean()
        .reset_index()
        .sort_values("time")
        .reset_index(drop=True)
    )
    return com


def _calculate_trajectory_metrics(
    trajectory_df: pd.DataFrame,
    start_pos: np.ndarray,
    target_pos: np.ndarray,
    verbose: bool = False
) -> Dict[str, float]:
    pass                                                                                             
    eps = 1e-8

                 
    ideal_direction = target_pos - start_pos
    ideal_distance = float(np.linalg.norm(ideal_direction))
    if ideal_distance < 1e-6:
        return _get_default_trajectory_stats()
    unit_direction = ideal_direction / ideal_distance

            
    positions = trajectory_df[["x", "y", "z"]].to_numpy(dtype=float)
    times = trajectory_df["time"].to_numpy(dtype=float)

    if len(positions) < 2:
        return _get_default_trajectory_stats()

                                                                        
    dt = np.diff(times)
    valid_steps = dt > 0.0
    if not np.any(valid_steps):
        return _get_default_trajectory_stats()

    dt = dt[valid_steps]                                            
    dx = np.diff(positions, axis=0)[valid_steps, :]                   
    T = float(times[-1] - times[0]) if times[-1] > times[0] else float(np.sum(dt))
    if T <= 0:
        return _get_default_trajectory_stats()

                                                                                
    velocities = dx / dt[:, None]                                     
    speed = np.linalg.norm(velocities, axis=1)                      

                         
                                              
    relative_positions = positions - start_pos[None, :]
    along_track_positions = relative_positions @ unit_direction        

                            
    max_progress_ratio = float(
        min(1.0, max(0.0, float(np.max(along_track_positions)) / (ideal_distance + eps)))
    )

                                                                              
                                                                  
    along_speed = (velocities @ unit_direction)                                 
    cos_theta = np.divide(along_speed, np.maximum(speed, eps))                  
    c_pos = np.maximum(0.0, cos_theta) * dt
    direction_consistency = float(np.sum(c_pos) / T)                        

                                                                                              
    backtrack_distance = float(np.sum(np.maximum(0.0, -along_speed) * dt))
    backtrack_penalty = float(backtrack_distance / (ideal_distance + eps))

                          
                                                       
    P = np.eye(3) - np.outer(unit_direction, unit_direction)                                   
    lateral_vec = relative_positions @ P.T                               
    e_perp = np.linalg.norm(lateral_vec, axis=1)                        

                                                                        
                                                                                         
                                                          
    e_seg = e_perp[:-1][valid_steps]                                             
    lateral_deviation = float(np.sum(e_seg * dt) / ((ideal_distance + eps) * T))

                                                                                              
    total_path_length = float(np.sum(np.linalg.norm(dx, axis=1)))                                      
    effective_progress = float(max(np.max(along_track_positions), eps))
    path_efficiency = float(max(0.0, total_path_length / effective_progress - 1.0))

                                       
    final_along_track = float(along_track_positions[-1])
    final_distance_ratio = float(max(0.0, (ideal_distance - final_along_track) / (ideal_distance + eps)))

    return {
        "max_progress_ratio": max_progress_ratio,
        "direction_consistency": direction_consistency,
        "backtrack_penalty": backtrack_penalty,
        "lateral_deviation": lateral_deviation,
        "path_efficiency": path_efficiency,
        "final_distance_ratio": final_distance_ratio,
    }


def _get_default_trajectory_stats() -> Dict[str, float]:
    pass                                                      
    return {
        'max_progress_ratio': 0.0,
        'direction_consistency': 0.0,
        'backtrack_penalty': 0.0,
        'lateral_deviation': 0.0,
        'path_efficiency': 0.0,
        'final_distance_ratio': 1.0,                                           
    }


def extract_round_suffix(file_paths: Dict[str, str]) -> str:
    pass                                                        
    
         
                                                               
        
            
                                                                                  
       
                                             
    bsg_filename = os.path.basename(file_paths['machine_bsg_path'])
    
    if "_sim_" in bsg_filename:
                                                                            
        round_part = bsg_filename.split("_sim_")[-1].split(".")[0]
        if round_part.isdigit():
            return f"_{round_part}"
    
    return ""

def save_analysis_result(result: Dict[str, Any], base_dir: str = "datacache/analysis_simulation") -> str:
    pass                                                                        
    
         
                                                                                                           
                                                 
        
            
                              
       
                                      
    filename_base = f"sim_{result['category']}_{result['level']}_{result['model_name']}_{result['machine_id']}"
    if result.get('round_suffix'):
        filename_base += result['round_suffix']
    
    save_path = os.path.join(base_dir, f"{filename_base}.json")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return save_path


def parse_csv_filename(csv_path: str) -> Optional[int]:
    pass                                             
    
         
                                                 
        
            
                                                                                
        
             
                                                 
                                                
                                                
       
    filename = os.path.basename(csv_path)
    
                                                                             
    match = re.search(r'_sim(?:_(\d+))?\.csv$', filename)
    
    if match:
        round_str = match.group(1)                                        
        return int(round_str) if round_str else None
    
    return None


def parse_category_from_path(csv_path: str) -> str:
    pass                                                                     
    
         
                                                 
        
            
                                                           
        
           
                                                              
       
                                                                    
                                                                                                       
    path_parts = os.path.normpath(csv_path).split(os.sep)
    
                                                               
    for part in reversed(path_parts):
        if part.startswith('lift_'):
            return 'lift'
        elif part.startswith('support_'):
            return 'support' 
        elif part.startswith('transport_'):
            return 'transport'
    
    raise ValueError(f"Cannot determine category from path: {csv_path}")


def route_simulation_analysis(csv_path: str, verbose: bool = False) -> Dict[str, Any]:
    pass                                                                                   
                                                     
    
         
                                                 
                                                      
        
            
                                                                         
        
           
                                                                      
                                                        
       
    try:
                                              
        sim_round = parse_csv_filename(csv_path)
        
                                                              
        machine_dir = os.path.dirname(csv_path)
        
                                  
        category = parse_category_from_path(csv_path)
        
        if verbose:
            print(f"Router analysis:")
            print(f"  CSV path: {csv_path}")
            print(f"  Machine dir: {machine_dir}")
            print(f"  Category: {category}")
            print(f"  Simulation round: {sim_round}")
        
                                                                       
        if category == 'lift':
            from .sim_lift import main as analyze_simulation_lift_and_save
            result = analyze_simulation_lift_and_save(machine_dir, sim_round=sim_round, verbose=verbose)
        elif category == 'support':
            from .sim_support import main as analyze_simulation_support_and_save
            result = analyze_simulation_support_and_save(machine_dir, sim_round=sim_round, verbose=verbose)
        elif category == 'transport':
            from .sim_transport import main as analyze_simulation_transport_and_save
            result = analyze_simulation_transport_and_save(machine_dir, sim_round=sim_round, verbose=verbose)
        else:
            raise ValueError(f"Unknown category: {category}")
        
        copy_passed_bsg(result)
            
    except Exception as e:
        raise ValueError(f"Failed to route simulation analysis: {str(e)}") from e
    
def copy_passed_bsg(result: Dict[str, Any], base_dir: str = "datacache/passed_cases") -> Optional[str]:
    pass                                                                     
    
         
                                                                                                                    
                                                 
        
            
                                                                                   
       
                                        
    if not result.get('pass', False):
        return None
    
    try:
                                 
        category = result.get('category', '')
        level = result.get('level', '')
        model_name = result.get('model_name', '')
        machine_id = result.get('machine_id', '')
        machine_bsg_path = result.get('machine_bsg_path', '')
        round_suffix = result.get('round_suffix', '')
        
                                  
        if not all([category, level, model_name, machine_id, machine_bsg_path]):
            raise ValueError("Missing required fields in result dictionary")
        
        if not os.path.exists(machine_bsg_path):
            raise FileNotFoundError(f"Source BSG file not found: {machine_bsg_path}")
        
                                           
        target_dir = os.path.join(base_dir, f"{category}_{level}")
        os.makedirs(target_dir, exist_ok=True)
        
                                                         
        target_filename = f"{model_name}_{machine_id}_sim{round_suffix}.bsg"
        target_path = os.path.join(target_dir, target_filename)
        
                       
        shutil.copy2(machine_bsg_path, target_path)
        
        return target_path
        
    except Exception as e:
        print(f"Warning: Failed to copy BSG file: {e}")
        return None


def main(csv_path: str, verbose: bool = False) -> None:
    pass                                         
    route_simulation_analysis(csv_path, verbose=verbose)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--verbose", action="store_true", required=False, default=False)
    args = parser.parse_args()
    main(args.csv_path, args.verbose)
