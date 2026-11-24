                                                                               
import os
import sys
import agents
from h0_client import H0ChatCompletionClient

class LocalClient(H0ChatCompletionClient):
    async def _call_node(self, payload):
        result=await super()._call_node(payload)
        if 'error' in result:
                                                                             
                                                                               
            raise RuntimeError(result['error'])
        return result

model=sys.argv[sys.argv.index('--model')+1]
assert model in ['h0-iter1','h0-iter2','h0-iter3']
assert os.environ['H0_MODULE_REGISTRY'].endswith('/'+model.replace('h0-','')+'/registries/c-d.json')
agents.model_clients[model]=LocalClient(max_retries=1)
if __name__=='__main__':
    from script.run_construction import main
    main()
