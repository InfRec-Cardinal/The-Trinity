import argparse
import json
import logging
import multiprocessing
import os

import pandas as pd
import requests
from tqdm import tqdm


class BioModelsDownloader:
    pass                                                                
       

    def __init__(self, output_dir="biomodels_sbml", log_file="biomodels_download.log"):
        pass                                                                    

             
                                                                 
                                             
           
        self.info_url = "https://www.ebi.ac.uk/biomodels/"
        self.base_url = "https://www.ebi.ac.uk/biomodels/model/download"
        query = '*%3A*+AND+curationstatus%3A"Manually+curated"'
        self.model_list_url = f"https://www.ebi.ac.uk/biomodels/search?format=json&query={query}&numResults=1000&offset="
        self.output_dir = output_dir
        self.filename_to_model_id = {}

                                                     
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

                        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def get_model_info(self, model_id):
        pass                                                

                
                                              
           
        try:
            url = f"{self.info_url}{model_id}?format=json"
            response = requests.get(url)

            if response.status_code != 200:
                self.logger.error(f"Failed to get model info for {model_id}")
                return None

            data = response.json()

            if response.status_code == 200:
                return data
            else:
                self.logger.warning(
                    f"Failed to get model {model_id} info: HTTP {response.status_code}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error fetching model {model_id} info: {str(e)}")
            return None

    def get_all_model_ids(self):
        pass                                                   

                
                                   
           
        model_ids = []
        offset = 0
        total_models = None

        self.logger.info("Retrieving list of all BioModels...")

        while True:
            url = f"{self.model_list_url}{offset}"
            response = requests.get(url)

            if response.status_code != 200:
                self.logger.error(
                    f"Failed to get model list at offset {offset}: {response.status_code}"
                )
                break

            data = response.json()

                                                       
            if total_models is None:
                total_models = data.get("matches", 0)
                self.logger.info(f"Found {total_models} models in total")

                                                 
            models = data.get("models", [])

            if not models:
                break

            for model in tqdm(models):
                model_id = model.get("id")
                if model_id:
                    model_ids.append(model_id)

                               
            offset += len(models)

                                                 
            if offset >= total_models:
                break

                                   
                             

        self.logger.info(f"Retrieved {len(model_ids)} model IDs")
        return model_ids

    def download_model(self, model_id, filename):
        pass                                                 

             
                                       
                                                                 

                
                                                                  
           
                                                        
                                                                         
                                                                 
        url = f"{self.base_url}/{model_id}"

                                                                        
        output_path = os.path.join(self.output_dir, f"{model_id}.zip")
        self.filename_to_model_id[filename] = model_id

                                    
        if os.path.exists(output_path):
            self.logger.info(f"Model {model_id} already downloaded, skipping")
            return False

        try:
            response = requests.get(url)

            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                self.logger.warning(
                    f"Failed to download model {model_id}: HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error downloading model {model_id}: {str(e)}")
            return False

    def _download_model_wrapper(self, model_id):
        pass                                                                            

             
                                       

                
                                                                  
           
        filepath = f"{self.output_dir}/{model_id}.json"

        if os.path.exists(filepath):
            return None

        model_info = self.get_model_info(model_id)

        if not model_info:
            print(f"Failed to get model info for {model_id}")
            return None

                                                             

                                          
                         

        with open(filepath, "w") as file:
            json.dump(model_info, file, indent=4)

                         
        return None

                                                           
                                                          

                    
                             

                       

    def download_all_models(self, num_processes=None):
        pass                                                                    

             
                                                                      
                                                                    
           
        model_ids = self.get_all_model_ids()

        if not model_ids:
            self.logger.error("No models found to download")
            return

                                                          
        if num_processes is None:
            num_processes = multiprocessing.cpu_count()

        self.logger.info(
            f"Starting download of {len(model_ids)} models using {num_processes} processes..."
        )

                               
        with multiprocessing.Pool(processes=num_processes) as pool:
                                       
            results = list(
                tqdm(
                    pool.imap(self._download_model_wrapper, model_ids),
                    total=len(model_ids),
                    desc="Downloading models...",
                )
            )

                      
                                                                                              
                                                                    

                                               
        successful = sum(results)                
        failed = len(results) - successful

        self.logger.info(
            f"Download complete. Successfully downloaded: {successful}, Failed: {failed}"
        )


def main():
    parser = argparse.ArgumentParser(description="Download all SBML models from BioModels.")
    parser.add_argument(
        "--output-dir", default="biomodels/all", help="Directory to save downloaded models"
    )
    parser.add_argument("--log-file", default="biomodels_download.log", help="Log file path")
    parser.add_argument(
        "--processes", type=int, default=4, help="Number of processes to use for parallel downloads"
    )
    args = parser.parse_args()

    downloader = BioModelsDownloader(output_dir=args.output_dir, log_file=args.log_file)
    downloader.download_all_models(num_processes=args.processes)
    pd.DataFrame.from_dict(downloader.filename_to_model_id).to_csv(
        args.output_dir + "/index.csv", index=False
    )


if __name__ == "__main__":
    main()
