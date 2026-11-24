                                                                                        
                                                                                    
                                               
                                                                                                
   
import agents
from h0_client import H0ChatCompletionClient

agents.model_clients["h0-opus-5"] = H0ChatCompletionClient()

if __name__ == "__main__":
    from script.run_construction import main
    main()
