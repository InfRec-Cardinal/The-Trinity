import os
import pandas as pd
import argparse

                            
parser = argparse.ArgumentParser(description="Breakdown Q20")
parser.add_argument("--dir", type=str, help="Path to the directory containing TXT files.")
parser.add_argument("--keep_order", action='store_true', help="Path to the directory containing TXT files.")
args = parser.parse_args()
input_dir = args.dir                                           

                                                                  
subdirectories = set([d[:-5] for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))])


                                                      
file_data = {}

                                
for subdir in subdirectories:
                                                            
    cumulative_data = pd.DataFrame(columns=["File", "Num_Turns", "Success", "Num_Yes", "Score"])
    skip_flag = False 

                                       
    for i in range(1, 6):
                                                       
        metrics_file = os.path.join(input_dir, f"{subdir}_rep{i}", "metrics.csv")
        
        if os.path.exists(metrics_file):
                                                        
            data = pd.read_csv(metrics_file)
            
                                                      
            cumulative_data = pd.concat([cumulative_data, data], ignore_index=True)

            if args.keep_order:
                                                                      
                file_order = data[data.keys()[0]].unique()

        else:
            print(f"Warning: missing {subdir}_rep{i}")
            skip_flag = True
            break
    
    if skip_flag:
        continue
    
                                           
    avg_data = cumulative_data.groupby("File").mean().reset_index()

    if args.keep_order:
                                                                            
        avg_data = avg_data.reindex(avg_data["File"].map({file: i for i, file in enumerate(file_order)}).sort_values().index)
    
                                                        
    file_data[subdir] = avg_data


                                              
for subdir, avg_data in file_data.items():
    output_file = os.path.join(input_dir, f"{subdir}.avg.csv")
    avg_data.to_csv(output_file, index=False)
