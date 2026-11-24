                                 

                                                                                        
                       
                                                                     

                              
                               
                                                                        

                                                                               
                                                     
                                                              
                                                                           
                                                                                                   
                                                         
   

import os
import sys
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd

from scheduler.task_db import get_engine, Task, Machine, select, Session


@dataclass
class TaskMetrics:
    pass                                        
    task_id: str
    token_input: int
    token_output: int
    turn: int
    duration: float
    
    def __post_init__(self):
        pass                                       
        self.token_input = self.token_input or 0
        self.token_output = self.token_output or 0
        self.turn = self.turn or 0
        self.duration = self.duration or 0.0


@dataclass
class SamplingPath:
    pass                                                        
    plan: Optional[TaskMetrics] = None
    draft_a: Optional[TaskMetrics] = None
    draft_b: Optional[TaskMetrics] = None
    draft_c: Optional[TaskMetrics] = None
    build_a: Optional[TaskMetrics] = None
    refine_a: Optional[TaskMetrics] = None
    build_b: Optional[TaskMetrics] = None
    refine_b: Optional[TaskMetrics] = None
    build_c: Optional[TaskMetrics] = None
    refine_c: Optional[TaskMetrics] = None
    assemble: Optional[TaskMetrics] = None
    
    def get_total_metrics(self) -> Tuple[int, int, int, float]:
        pass                                                                                
        total_token_in = 0
        total_token_out = 0
        total_turn = 0
        total_duration = 0.0
        
        for task in [self.plan, self.draft_a, self.draft_b, self.draft_c, self.build_a, self.refine_a, self.build_b, self.refine_b, 
                     self.build_c, self.refine_c, self.assemble]:
            if task:
                total_token_in += task.token_input
                total_token_out += task.token_output
                total_turn += task.turn
                total_duration += task.duration
                
        return total_token_in, total_token_out, total_turn, total_duration


def retrieve_plan_tasks(db_path: str) -> List[Task]:
    pass                                                    
    
         
                                          
        
            
                                              
       
    engine = get_engine(db_path)
    with Session(engine, expire_on_commit=False) as session:
        statement = select(Task).where(Task.stage == "plan")
        plan_tasks = session.exec(statement).all()
        return plan_tasks


def retrieve_bound_tasks(plan_id: str, db_path: str) -> List[Task]:
    pass                                                              
    
         
                                        
                                          
        
            
                                                   
       
    engine = get_engine(db_path)
    with Session(engine, expire_on_commit=False) as session:
        statement = select(Task).where(Task.bind_plan == plan_id)
        bound_tasks = session.exec(statement).all()
        return bound_tasks


def find_machine_by_task(task_id: str, db_path: str) -> Optional[str]:
    pass                                    
    
         
                                   
                                          
        
            
                                           
       
    engine = get_engine(db_path)
    with Session(engine, expire_on_commit=False) as session:
        statement = select(Machine).where(Machine.bind_task == task_id)
        machine = session.exec(statement).first()
        return machine.id if machine else None


def find_last_task_in_path(path: SamplingPath, plan_task: Task, bound_tasks: List[Task]) -> Optional[Tuple[str, str]]:
    pass                                                                         
    
         
                                 
                                            
                                                 
        
            
                                                                             
       
                                                 
    if plan_task.sub_structure and plan_task.sub_structure > 1:
                                      
        if path.assemble:
            return (path.assemble.task_id, "assemble")
        else:
            return None
    else:
                                                            
                                                         
        all_task_ids = [task.id for task in bound_tasks]
        parent_ids = set()
        
                                                 
        for task in bound_tasks:
            if task.parent_id and task.parent_id in all_task_ids:
                parent_ids.add(task.parent_id)
        
                                                      
        leaf_tasks = []
        for task in bound_tasks:
            if task.id not in parent_ids and task.stage in ['build', 'refine']:
                leaf_tasks.append(task)
        
                                                                           
        if leaf_tasks:
                                                              
            leaf_tasks.sort(key=lambda x: x.created_at)
            last_task = leaf_tasks[-1]
            return (last_task.id, last_task.stage)
        else:
                                                                        
            stage_mapping = {
                'refine_c': 'refine', 'build_c': 'build',
                'refine_b': 'refine', 'build_b': 'build', 
                'refine_a': 'refine', 'build_a': 'build'
            }
            for task_attr in ['refine_c', 'build_c', 'refine_b', 'build_b', 'refine_a', 'build_a']:
                task = getattr(path, task_attr)
                if task:
                    return (task.task_id, stage_mapping[task_attr])
            return None


def create_task_metrics(task: Task) -> TaskMetrics:
    pass                                         
    
         
                                       
        
            
                                                          
       
    return TaskMetrics(
        task_id=task.id,
        token_input=task.token_input or 0,
        token_output=task.token_output or 0,
        turn=task.turn or 0,
        duration=task.duration or 0.0
    )


def organize_sampling_path(plan_task: Task, bound_tasks: List[Task]) -> SamplingPath:
    pass                                                                     
    
         
                                                         
                                                 
        
            
                                                         
       
    path = SamplingPath()
    
                       
    path.plan = create_task_metrics(plan_task)
    
                                   
    draft_tasks = []
    build_tasks = []
    refine_tasks = []
    
    for task in bound_tasks:
        if task.stage == "draft":
            draft_tasks.append(create_task_metrics(task))
        elif task.stage == "build":
            build_tasks.append(create_task_metrics(task))
        elif task.stage == "refine":
            refine_tasks.append(create_task_metrics(task))
        elif task.stage == "assemble":
            path.assemble = create_task_metrics(task)
            
                                    
    if len(draft_tasks) >= 1:
        path.draft_a = draft_tasks[0]
    if len(draft_tasks) >= 2:
        path.draft_b = draft_tasks[1]
    if len(draft_tasks) >= 3:
        path.draft_c = draft_tasks[2]
    
                                    
    if len(build_tasks) >= 1:
        path.build_a = build_tasks[0]
    if len(build_tasks) >= 2:
        path.build_b = build_tasks[1]
    if len(build_tasks) >= 3:
        path.build_c = build_tasks[2]
    
                                                              
    if len(refine_tasks) >= 1:
        path.refine_a = refine_tasks[0]
    if len(refine_tasks) >= 2:
        path.refine_b = refine_tasks[1]
    if len(refine_tasks) >= 3:
        path.refine_c = refine_tasks[2]
    
    return path


def generate_sampling_paths(db_path: str) -> List[SamplingPath]:
    pass                                                  
    
         
                                          
        
            
                                    
       
    plan_tasks = retrieve_plan_tasks(db_path)
    sampling_paths = []
    
    for plan_task in plan_tasks:
        bound_tasks = retrieve_bound_tasks(plan_task.id, db_path)
        path = organize_sampling_path(plan_task, bound_tasks)
        sampling_paths.append(path)
    
    return sampling_paths


def create_table_row(path: SamplingPath, plan_task: Task = None, bound_tasks: List[Task] = None, db_path: str = None) -> Dict[str, Any]:
    pass                                                     
    
         
                                 
                                                            
                                                                         
                                                      
        
            
                                           
       
    row = {}
    
                                                              
    plan_failed = plan_task and plan_task.status == "failed"
    
                  
    if path.plan and not plan_failed:
        row.update({
            'plan_id': path.plan.task_id,
            'plan_token_in': path.plan.token_input,
            'plan_token_out': path.plan.token_output,
            'plan_turn': path.plan.turn,
            'plan_time': path.plan.duration
        })
    else:
        row.update({
            'plan_id': path.plan.task_id if path.plan else 'N/A',                            
            'plan_token_in': 'N/A',
            'plan_token_out': 'N/A',
            'plan_turn': 'N/A',
            'plan_time': 'N/A'
        })
    
                   
    if path.draft_a and not plan_failed:
        row.update({
            'draft_a_id': path.draft_a.task_id,
            'draft_a_token_in': path.draft_a.token_input,
            'draft_a_token_out': path.draft_a.token_output,
            'draft_a_turn': path.draft_a.turn,
            'draft_a_time': path.draft_a.duration
        })
    else:
        row.update({
            'draft_a_id': 'N/A',
            'draft_a_token_in': 'N/A',
            'draft_a_token_out': 'N/A',
            'draft_a_turn': 'N/A',
            'draft_a_time': 'N/A'
        })
    
                     
    if path.draft_b and not plan_failed:
        row.update({
            'draft_b_id': path.draft_b.task_id,
            'draft_b_token_in': path.draft_b.token_input,
            'draft_b_token_out': path.draft_b.token_output,
            'draft_b_turn': path.draft_b.turn,
            'draft_b_time': path.draft_b.duration
        })
    else:
        row.update({
            'draft_b_id': 'N/A',
            'draft_b_token_in': 'N/A',
            'draft_b_token_out': 'N/A',
            'draft_b_turn': 'N/A',
            'draft_b_time': 'N/A'
        })
    
                     
    if path.draft_c and not plan_failed:
        row.update({
            'draft_c_id': path.draft_c.task_id,
            'draft_c_token_in': path.draft_c.token_input,
            'draft_c_token_out': path.draft_c.token_output,
            'draft_c_turn': path.draft_c.turn,
            'draft_c_time': path.draft_c.duration
        })
    else:
        row.update({
            'draft_c_id': 'N/A',
            'draft_c_token_in': 'N/A',
            'draft_c_token_out': 'N/A',
            'draft_c_turn': 'N/A',
            'draft_c_time': 'N/A'
        })
    
                     
    if path.build_a and not plan_failed:
        row.update({
            'build_a_id': path.build_a.task_id,
            'build_a_token_in': path.build_a.token_input,
            'build_a_token_out': path.build_a.token_output,
            'build_a_turn': path.build_a.turn,
            'build_a_time': path.build_a.duration
        })
    else:
        row.update({
            'build_a_id': 'N/A',
            'build_a_token_in': 'N/A',
            'build_a_token_out': 'N/A',
            'build_a_turn': 'N/A',
            'build_a_time': 'N/A'
        })
    
                      
    if path.refine_a and not plan_failed:
        row.update({
            'refine_a_id': path.refine_a.task_id,
            'refine_a_token_in': path.refine_a.token_input,
            'refine_a_token_out': path.refine_a.token_output,
            'refine_a_turn': path.refine_a.turn,
            'refine_a_time': path.refine_a.duration
        })
    else:
        row.update({
            'refine_a_id': 'N/A',
            'refine_a_token_in': 'N/A',
            'refine_a_token_out': 'N/A',
            'refine_a_turn': 'N/A',
            'refine_a_time': 'N/A'
        })
    
                     
    if path.build_b and not plan_failed:
        row.update({
            'build_b_id': path.build_b.task_id,
            'build_b_token_in': path.build_b.token_input,
            'build_b_token_out': path.build_b.token_output,
            'build_b_turn': path.build_b.turn,
            'build_b_time': path.build_b.duration
        })
    else:
        row.update({
            'build_b_id': 'N/A',
            'build_b_token_in': 'N/A',
            'build_b_token_out': 'N/A',
            'build_b_turn': 'N/A',
            'build_b_time': 'N/A'
        })
    
                      
    if path.refine_b and not plan_failed:
        row.update({
            'refine_b_id': path.refine_b.task_id,
            'refine_b_token_in': path.refine_b.token_input,
            'refine_b_token_out': path.refine_b.token_output,
            'refine_b_turn': path.refine_b.turn,
            'refine_b_time': path.refine_b.duration
        })
    else:
        row.update({
            'refine_b_id': 'N/A',
            'refine_b_token_in': 'N/A',
            'refine_b_token_out': 'N/A',
            'refine_b_turn': 'N/A',
            'refine_b_time': 'N/A'
        })
    
                     
    if path.build_c and not plan_failed:
        row.update({
            'build_c_id': path.build_c.task_id,
            'build_c_token_in': path.build_c.token_input,
            'build_c_token_out': path.build_c.token_output,
            'build_c_turn': path.build_c.turn,
            'build_c_time': path.build_c.duration
        })
    else:
        row.update({
            'build_c_id': 'N/A',
            'build_c_token_in': 'N/A',
            'build_c_token_out': 'N/A',
            'build_c_turn': 'N/A',
            'build_c_time': 'N/A'
        })
    
                      
    if path.refine_c and not plan_failed:
        row.update({
            'refine_c_id': path.refine_c.task_id,
            'refine_c_token_in': path.refine_c.token_input,
            'refine_c_token_out': path.refine_c.token_output,
            'refine_c_turn': path.refine_c.turn,
            'refine_c_time': path.refine_c.duration
        })
    else:
        row.update({
            'refine_c_id': 'N/A',
            'refine_c_token_in': 'N/A',
            'refine_c_token_out': 'N/A',
            'refine_c_turn': 'N/A',
            'refine_c_time': 'N/A'
        })
    
                      
    if path.assemble and not plan_failed:
        row.update({
            'assemble_id': path.assemble.task_id,
            'assemble_token_in': path.assemble.token_input,
            'assemble_token_out': path.assemble.token_output,
            'assemble_turn': path.assemble.turn,
            'assemble_time': path.assemble.duration
        })
    else:
        row.update({
            'assemble_id': 'N/A',
            'assemble_token_in': 'N/A',
            'assemble_token_out': 'N/A',
            'assemble_turn': 'N/A',
            'assemble_time': 'N/A'
        })
    
                                               
    if not plan_failed:
        total_token_in, total_token_out, total_turn, total_time = path.get_total_metrics()
        row.update({
            'total_token_in': total_token_in,
            'total_token_out': total_token_out,
            'total_turn': total_turn,
            'total_time': total_time
        })
    else:
        row.update({
            'total_token_in': 'N/A',
            'total_token_out': 'N/A',
            'total_turn': 'N/A',
            'total_time': 'N/A'
        })
    
                                        
    if not plan_failed and plan_task and bound_tasks and db_path:
        last_task_info = find_last_task_in_path(path, plan_task, bound_tasks)
        if last_task_info:
            last_task_id, last_task_stage = last_task_info
            machine_id = find_machine_by_task(last_task_id, db_path)
            row['final_machine_id'] = machine_id if machine_id else 'N/A'
            row['final_machine_stage'] = last_task_stage
        else:
            row['final_machine_id'] = 'N/A'
            row['final_machine_stage'] = 'N/A'
    else:
        row['final_machine_id'] = 'N/A'
        row['final_machine_stage'] = 'N/A'
    
    return row


def get_numerical_columns() -> List[str]:
    pass                                                            
    
            
                                                        
       
    return [
        'plan_token_in', 'plan_token_out', 'plan_turn', 'plan_time',
        'draft_a_token_in', 'draft_a_token_out', 'draft_a_turn', 'draft_a_time',
        'draft_b_token_in', 'draft_b_token_out', 'draft_b_turn', 'draft_b_time',
        'draft_c_token_in', 'draft_c_token_out', 'draft_c_turn', 'draft_c_time',
        'build_a_token_in', 'build_a_token_out', 'build_a_turn', 'build_a_time',
        'refine_a_token_in', 'refine_a_token_out', 'refine_a_turn', 'refine_a_time',
        'build_b_token_in', 'build_b_token_out', 'build_b_turn', 'build_b_time',
        'refine_b_token_in', 'refine_b_token_out', 'refine_b_turn', 'refine_b_time',
        'build_c_token_in', 'build_c_token_out', 'build_c_turn', 'build_c_time',
        'refine_c_token_in', 'refine_c_token_out', 'refine_c_turn', 'refine_c_time',
        'assemble_token_in', 'assemble_token_out', 'assemble_turn', 'assemble_time',
        'total_token_in', 'total_token_out', 'total_turn', 'total_time'
    ]


def calculate_statistics(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    pass                                                                      
    
         
                                                       
        
            
                                                          
       
    numerical_cols = get_numerical_columns()
    stats = {}
    
                                                                       
    df_numeric = df[numerical_cols].replace('N/A', pd.NA)
    
                          
    stats['AVERAGE'] = {}
    stats['MAX'] = {}
    stats['MIN'] = {}
    stats['SUM'] = {}
    
    for col in numerical_cols:
                                                                          
        numeric_series = pd.to_numeric(df_numeric[col], errors='coerce')
        
        if numeric_series.notna().sum() > 0:                                             
            stats['AVERAGE'][col] = numeric_series.mean()
            stats['MAX'][col] = numeric_series.max()
            stats['MIN'][col] = numeric_series.min()
            stats['SUM'][col] = numeric_series.sum()
        else:
            stats['AVERAGE'][col] = 'N/A'
            stats['MAX'][col] = 'N/A'
            stats['MIN'][col] = 'N/A'
            stats['SUM'][col] = 'N/A'
    
    return stats


def generate_analysis_table(db_path: str) -> pd.DataFrame:
    pass                                                                            
    
         
                                          
        
            
                                               
       
                             
    sampling_paths = generate_sampling_paths(db_path)
    
    if not sampling_paths:
        print("No sampling paths found in the database.")
        return pd.DataFrame()
    
                           
    rows = []
    plan_tasks = retrieve_plan_tasks(db_path)
    plan_task_dict = {task.id: task for task in plan_tasks}
    
    for path in sampling_paths:
        plan_task = plan_task_dict.get(path.plan.task_id) if path.plan else None
        bound_tasks = retrieve_bound_tasks(path.plan.task_id, db_path) if path.plan else []
        row = create_table_row(path, plan_task, bound_tasks, db_path)
        rows.append(row)
    
                      
    df = pd.DataFrame(rows)

    return df


def main():
    pass                                                    
       
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze sampling paths from task database')
    parser.add_argument('db_path', help='Path to the task database file')
    parser.add_argument('--output', '-o', default='analysis_table.csv', help='Output CSV file path (optional)')
    parser.add_argument('--display', '-d', action='store_true', help='Display table in console')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db_path):
        print(f"Error: Database file '{args.db_path}' not found.")
        sys.exit(1)
    
    try:
                                     
        df = generate_analysis_table(args.db_path)
        
        if df.empty:
            print("No data found to analyze.")
            return
        
                                    
        if args.display:
            print("\nSampling Path Analysis Table:")
            print("=" * 120)
            print(df.to_string(index=False, max_cols=None, max_colwidth=None))
        
                                             
        if args.output:
            df.to_csv(args.output, index=False)
            print(f"\nTable saved to: {args.output}")
        
        print(f"\nAnalysis completed. Found {len(df)} sampling paths.")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
