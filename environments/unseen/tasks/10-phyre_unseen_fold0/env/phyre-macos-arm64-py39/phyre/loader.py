#!/usr/bin/env python3
                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                      

                                                                             
                                                      
   
from typing import Any, Dict, Mapping, Iterable, Optional, Sequence, Tuple
import collections
import importlib.util
import lzma
import os
import pickle
import re

import phyre.interface.task.ttypes as task_if
import phyre.settings
import phyre.simulator

TaskScript = Any


def load_task_script(template_id_or_path: str) -> Tuple[str, str, TaskScript]:
    pass                                                                      

         
                                                                       
                                                               
                         

            
                                                            
       
    if '/' in template_id_or_path:
        task_dir, task_script_name = template_id_or_path.rsplit('/', 1)
        assert task_script_name.startswith('task'), template_id_or_path
        assert task_script_name.endswith('.py'), template_id_or_path
        template_id = task_script_name[4:-3]
    else:
        task_dir = str(phyre.settings.TASK_SCRIPTS_DIR)
        template_id = template_id_or_path
    loaded = load_task_scripts_from_folder(task_dir, [template_id])
    if len(loaded) != 1:
        raise RuntimeError('Failed to load task script %s from %s' %
                           (template_id, task_dir))
    return loaded[0]


def load_task_scripts_from_folder(
        task_folder=str(phyre.settings.TASK_SCRIPTS_DIR),
        template_id_list=None) -> Sequence[Tuple[str, str, TaskScript]]:
    pass                                   

         
                                                                            
                                                                             
                                                                             
                                                                              
                                                 

            
                                                                    
       
    if not os.path.exists(task_folder):
        raise RuntimeError(f'Cannot find task folder: {task_folder}')
                                                                 
    path_slug = re.sub('[^a-zA-Z0-9]', '_',
                       os.path.realpath(task_folder)).strip('_')
    tasks = []
    for fname in sorted(os.listdir(task_folder)):
        if not fname.startswith('task') or not fname.endswith('.py'):
            continue
        template_id = fname[4:-3]
        if (template_id_list is not None and
                template_id not in template_id_list):
            continue
        fpath = os.path.join(task_folder, fname)
        spec = importlib.util.spec_from_file_location(
            f'{path_slug}.task{template_id}', fpath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, 'build_task'):
            raise RuntimeError(f'Loaded {fname} from {task_folder}, but'
                               ' haven\'t found "build_task" method')
        tasks.append((template_id, fpath, module))
    return tasks


def load_tasks_from_folder(task_folder: str = str(
        phyre.settings.TASK_SCRIPTS_DIR),
                           template_id_list: Optional[Iterable[str]] = None,
                           task_id_list: Optional[Iterable[str]] = None,
                           eval_stats=None) -> Mapping[str, task_if.Task]:
    pass                                                     

         
                                                                            
                                                                             
                                                                             
                                                                            
                                              
                                                               
                                              
                                                                           
                                 

            
                                                              
                                        
       
    if template_id_list is None and task_id_list is not None:
        template_id_list = frozenset(
            task_id.split(':')[0] for task_id in task_id_list)
    task_scripts = load_task_scripts_from_folder(task_folder, template_id_list)

    tasks = collections.OrderedDict()
    for task_name, fpath, task_script in task_scripts:
        if eval_stats is not None:
            template_eval_stats = eval_stats.get(task_name)
        else:
            template_eval_stats = None
        try:
            builded_tasks = task_script.build_task(
                task_name, eval_stats=template_eval_stats)
        except Exception:
            print('Got exception while executing task builder from', fpath)
            raise
        for task in builded_tasks:
            if task_id_list is not None:
                if task.taskId not in task_id_list:
                    continue
            tasks[task.taskId] = task
    return tasks


def task_id_to_pickle(task_id):
    prefix = task_id[:2]
    if prefix == "00":
        return 'tasks.bin.lzma'
    else:
        return f'tasks{prefix}.bin.lzma'


def load_compiled_task_dict(task_ids: Optional[Sequence[str]] = None
                           ) -> Dict[str, task_if.Task]:
    pass                                                
    if task_ids is not None:
        fnames = frozenset(map(task_id_to_pickle, task_ids))
        paths = [phyre.settings.TASK_DIR / fname for fname in fnames]
    else:
        paths = phyre.settings.TASK_DIR.glob("*.bin.lzma")
    data = {}
    for path in paths:
        with lzma.open(path) as stream:
            collection = phyre.simulator.deserialize(task_if.TaskCollection(),
                                                     stream.read())
        data.update({task.taskId: task for task in collection.tasks})
    if task_ids is not None:
        missing = frozenset(task_ids).difference(data)
        if missing:
            raise RuntimeError('Unknown task ids: %s' % missing)
    return data


def load_compiled_template_dict() -> Dict[str, Dict[str, task_if.Task]]:
    pass                                                                 
    all_tasks = load_compiled_task_dict()
    template_ids = {}
    for task in all_tasks:
        template = task.split(':')[0]
        d = template_ids.get(template, {})
        d[task] = all_tasks[task]
        template_ids[template] = d
    return template_ids


def load_compiled_task_list(task_ids: Sequence[str],) -> Sequence[task_if.Task]:
    pass                                                                     
    task_dict = load_compiled_task_dict(task_ids)
    tasks = [task_dict[task_id] for task_id in task_ids]
    return tasks
