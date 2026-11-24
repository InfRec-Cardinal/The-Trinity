                                                                                      
                                                                           
   
import sys, os, json, threading, queue, traceback, shutil, random, ast, math, re, hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
                                                                                                 
SOURCE=Path(os.environ['GLEE_SOURCE']).resolve()
REAL_STDOUT=sys.stdout
STATE=None
GAME_ARGS=dict(is_myopic=False,total_rounds=20,p=0.3333,v=2,c=0,product_price=10000,is_seller_know_cv=True,is_buyer_know_p=True,seller_message_type='text',allow_buyer_message=False)
def detached(v): return json.loads(json.dumps(v))
def clean(v):
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,list):return [clean(x) for x in v]
    return v

def official_score(actions):
    import numpy as np, pandas as pd
    source=(SOURCE/'analyze/metrics.py').read_text();tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PersuasionMetrics')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='calculate_metrics')
    module=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(module)
    scope={'np':np};exec(compile(module,str(SOURCE/'analyze/metrics.py'),'exec'),scope)
    nature={int(x['round']):x['round_quality']=='high-quality' for x in actions if x.get('player')=='Nature'}
    deals={int(x['round']):x['decision']=='yes' for x in actions if x.get('player')=='Bob'}
    row={**{'quality_'+str(i):nature.get(i,False) for i in range(1,21)},**{'deal_'+str(i):deals.get(i,False) for i in range(1,21)},'game_args_v':2}
    holder=SimpleNamespace(data=pd.DataFrame([row]));scope['calculate_metrics'](holder)
    keys=['n_ev','k_ev','r_ev','efficiency','fairness','alice_final_share','bob_final_share','alice_self_gain','bob_self_gain']
    result=clean({k:holder.data.iloc[0][k].item() if hasattr(holder.data.iloc[0][k],'item') else holder.data.iloc[0][k] for k in keys})
    result.update(completedRounds=len(deals),officialCompleteMetric=len(deals)==20,zeroDenominatorRepresentation='null (original NaN)',methodASTHash=hashlib.sha256(ast.dump(fn,include_attributes=False).encode()).hexdigest())
    return result

class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        if self.path!='/chat':self.send_error(404);return
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        role='seller' if body['game_params']['public_name']=='Alice' else 'buyer'
        response=queue.Queue();event={'role':role,'body':detached(body),'responseQueue':response}
        STATE.events.put(event)
        answer=response.get(timeout=360)
        wire=json.dumps({'response':answer}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(wire)));self.end_headers();self.wfile.write(wire)

class NativeSession:
    def __init__(self,home,seed):
        global STATE
        home=Path(home).resolve()
        assert isinstance(seed,int) and 0<=seed<2**32
        home.mkdir(parents=True,exist_ok=True);self.home=home;self.events=queue.Queue();self.current=None;self.finished=False;self.error=None;self.ordinal=0;STATE=self
        shutil.copytree(SOURCE/'games/persuasion/prompts',home/'games/persuasion/prompts',dirs_exist_ok=True)
        os.chdir(home);os.environ['HOME']=str(home);os.environ['TMPDIR']=str(home/'tmp');(home/'tmp').mkdir(exist_ok=True)
        sys.path.insert(0,str(SOURCE));sys.stdout=open(home/'native-output.log','a',buffering=1)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),ChatHandler);self.server.daemon_threads=True;threading.Thread(target=self.server.serve_forever,daemon=True).start()
        from players.http_player import HTTPPlayer
        from utils.utils import DataLogger
        from games.persuasion.persuasion import PersuasionGame
        self.PersuasionGame=PersuasionGame
        url='http://127.0.0.1:'+str(self.server.server_port)
        self.seller=HTTPPlayer(url,public_name='Alice',player_id=0);self.buyer=HTTPPlayer(url,public_name='Bob',player_id=1)
        assert self.seller.api_key is None and self.buyer.api_key is None
        random.seed(seed)
        self.logger=DataLogger(self.seller,self.buyer,game_type='persuasion',game_args=GAME_ARGS,experiment_name='h0-native',source_commit='68a33e98b035b97f945badee8f325001555c0049',controlled_seed_private=True)
        self.game=PersuasionGame.__new__(PersuasionGame)
        def run():
            try:PersuasionGame.__init__(self.game,self.seller,self.buyer,self.logger,**GAME_ARGS)
            except Exception as e:self.error={'type':type(e).__name__,'message':str(e)}
            finally:self.finished=True;self.events.put({'role':'terminal'} )
        self.thread=threading.Thread(target=run,daemon=True);self.thread.start();self.wait_next()
    def wait_next(self):
        self.current=self.events.get(timeout=20);self.ordinal+=1
    def snapshot(self):
        actions=detached(self.logger.actions)
        return {'schema':'glee-original-native-session-snapshot-v1','ordinal':self.ordinal,'pendingRole':self.current['role'],'request':detached(self.current.get('body')),'actions':actions,'sellerMessages':detached(self.seller.messages),'buyerMessages':detached(self.buyer.messages),'sellerBuffer':self.seller.buffer,'buyerBuffer':self.buyer.buffer,'rngState':random.getstate(),'counters':{'sold':self.game.sold_counter,'soldQuality':self.game.sold_quality_counter},'finished':self.finished,'error':self.error,'nativeOutputDirectory':str(self.home/self.logger._get_output_path()),'score':official_score(actions) if self.finished else None}
    def answer(self,role,ordinal,text):
        assert self.current['role']==role and self.ordinal==ordinal,'Native pending role/order mismatch'
        assert isinstance(text,str)
        self.current['responseQueue'].put(text);self.wait_next();return self.snapshot()
    def project_buyer(self,text):
        valid,error=self.game.is_buyer_decision_in_format(text)
        if not valid:return {'valid':False,'error':error,'text':'[Invalid structured reference reply]'}
        action=json.loads(re.search(r'\{.*?\}',text,re.DOTALL).group());return {'valid':True,'text':json.dumps({'decision':action['decision']},ensure_ascii=False,separators=(',',':'))}
    def origins(self):
        import players.base_player as p,players.http_player as h,games.persuasion.persuasion as g,utils.utils as u
        return {'Player':p.__file__,'HTTPPlayer':h.__file__,'PersuasionGame':g.__file__,'DataLogger':u.__file__,'python':sys.executable,'prefix':sys.prefix,'basePrefix':sys.base_prefix,'numpy':__import__('numpy').__file__,'pandas':__import__('pandas').__file__,'requests':__import__('requests').__file__}

for line in sys.stdin:
    try:
        req=json.loads(line);method=req['method'];args=req.get('params',{})
        if method=='open':
            assert STATE is None,'One original native session per process';STATE=NativeSession(args['home'],args['seed']);result=STATE.snapshot()
        elif method=='answer':result=STATE.answer(args['role'],args['ordinal'],args['text'])
        elif method=='snapshot':result=STATE.snapshot()
        elif method=='project_buyer':result=STATE.project_buyer(args['text'])
        elif method=='validate_seller':result=STATE.game.is_offer_in_format(args['text'])
        elif method=='origins':result=STATE.origins()
        elif method=='score':result=official_score(args['actions'])
        elif method=='close':
            if STATE:STATE.logger._save_partial_logs();STATE.server.shutdown()
            result={'closed':True}
        else:raise ValueError('Unknown native method')
        response={'id':req['id'],'result':clean(result)}
    except Exception as e:response={'id':req.get('id') if 'req' in locals() else None,'error':{'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}}
    REAL_STDOUT.write(json.dumps(response,ensure_ascii=False,allow_nan=False)+'\n');REAL_STDOUT.flush()
    if method=='close':break
