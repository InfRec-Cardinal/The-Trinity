from utils import *

                                                         
df = pd.read_csv("data/scigym/data/benchmark_filtered_extended.csv")

                                               
                                      

                                                  
                                           

                                                 
                                               

                                         
                                   

                                                
                                  

                                   
                                 

                    
                                             
                                                                               
                                                                                   
                                                                                  
                                                                          
                                                                                 
                                                                    
                                                              


                                                                                                                                
def plot_histograms(df, columns, xlabels, ylabels, save_path=None):
    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.0))

    for i, (column, xlabel, ylabel) in enumerate(zip(columns, xlabels, ylabels)):
        axes[i].hist(df[column], bins=30, color="blue", alpha=0.7, density=(ylabel == "Density"))
        axes[i].set_xlabel(xlabel)
        axes[i].set_ylabel(ylabel)
        axes[i].set_yscale("log")
        axes[i].grid(axis="y", alpha=0.75)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    else:
        plt.show()
    plt.close()


                                      
columns = ["n_species", "n_reactions", "simulation_time"]
xlabels = ["Number of Species", "Number of Reactions", "Wall-Clock Time (s)"]
ylabels = ["Frequency", "Frequency", "Density"]

plot_histograms(df, columns, xlabels, ylabels, "model_statistics.pdf")
