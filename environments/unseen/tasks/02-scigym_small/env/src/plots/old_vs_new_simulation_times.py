from pathlib import Path

import pandas as pd
from utils import *

df = pd.read_csv("data/benchmark_filtered_extended.csv")
sedml_dir = Path("data/biomodels/benchmark/sedml")

                                                   

                                     
                                       
                                                              

                                                                                     
                                                                                         
                                                                                                     

                                                  
                                                           

                                                                   
                                                                   

                                                      
                                                     
                                                     

                                           
                                          
                                          
                          
                          

                                                      
                                                      

                            
                                                
                                                
           
                                                            
                                                            

                                                                                   

                                        
              
                                                                                         

                                                
df = df[df["old_sim_end_time"] < 10000]

fig, ax = plt.subplots(1, 2, figsize=(6.75, 3.0))

                                           
ax[0].hist(
    df["old_sim_end_time"], bins=30, alpha=0.5, label="Old Simulation", color="blue", density=False
)
ax[0].hist(
    df["new_sim_end_time"],
    bins=30,
    alpha=0.5,
    label="New Simulation",
    color="orange",
    density=False,
)
ax[0].legend(loc="upper right")
ax[0].set_xlabel("Simulation End Time (s)")
ax[0].set_ylabel("Count")
ax[0].set_yscale("log")

                                                
boxplots = ax[1].boxplot(
    [
        df["old_max_rate_of_change"],
        df["new_max_rate_of_change"],
    ]
)

                                                       
colors = ["blue", "orange"]
for median, color in zip(boxplots["medians"], colors):
    median.set(color=color, linewidth=2.0)                                        

ax[1].set_ylabel("Max Rate of Change at Endpoint")
ax[1].set_yscale("log")
                        
ax[1].set_xticklabels(["Old Simulation", "New Simulation"])

fig.tight_layout(pad=0.5)
fig.savefig("results/old_vs_new_simulation.pdf", dpi=300)

              
