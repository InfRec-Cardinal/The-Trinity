                                                                               
                                                                              
                                                                                
                                                                             
   
import ast,json,os,re,sys,pathlib,hashlib,types,threading,queue,logging
BASE=pathlib.Path(__file__).resolve().parent
SOURCE=BASE/'resources/source'
bindings=[]

def load_nodes(file,names):
    p=SOURCE/file;tree=ast.parse(p.read_bytes(),filename=str(p));nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    assert len(nodes)==len(names)
    for n in nodes:
        if isinstance(n,ast.ClassDef):
            for method in n.body:
                if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)):method.decorator_list=[]
    bindings.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'selectedOriginalAstNames':names,'decoratorBoundary':'retry removed; original method body unchanged'})
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),namespace)

out_queue=queue.Queue();in_queue=queue.Queue();game=None;thread=None;ended=False;pending=None;session_dir=None

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Message:
    def __init__(self,content):self.content=content
    def to_dict(self):return {'content':self.content,'role':'assistant'}

class NativeChatTransport:
    @staticmethod
    def create(**kwargs):
        global pending
                                                                             
        pending=kwargs
        out_queue.put({'kind':'judge_request','request':kwargs})
        result=in_queue.get()
        if result.get('kind')!='judge_response':raise ValueError('Judge transport input order differs')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=Message(result['text']))])

openai=types.SimpleNamespace(ChatCompletion=NativeChatTransport,api_key=None,api_base=None)
namespace={'json':json,'logging':logging,'os':os,'re':re,'List':list,'Optional':__import__('typing').Optional,'Anthropic':lambda:None,'openai':openai}
load_nodes('game.py',['Q20Game','Q20GameCelebrity'])
load_nodes('eval_result.py',['compute_metric'])

def receive_question(messages):
    out_queue.put({'kind':'player_request'})
    msg=in_queue.get()
    if msg.get('kind')!='player_action':raise ValueError('Player transport input order differs')
    return {'role':'assistant','content':msg['text']}

def play():
    global ended,pending
    try:
        game.game_play();ended=True;pending=None;out_queue.put({'kind':'terminal'})
    except BaseException:
        out_queue.put({'kind':'native_error'})

def snapshot(event):
    state={'category':'celebrities' if isinstance(game,namespace['Q20GameCelebrity']) else 'things','item':game.item,'background':getattr(game,'background',None),'messages':game.guesser_messages,'guesserWin':game.guesser_win,'ended':ended,'pendingRequest':pending,'session':configuration['sessionIndex']}
                                                                      
    public={'category':state['category'],'messages':game.guesser_messages,'turns':max(0,(len(game.guesser_messages)-1)//2),'maxTurns':game.num_turns,'ended':ended}
    metrics=None
    if game.guesser_messages and len(game.guesser_messages)>1:
        game.save_session(session_dir)
        metrics=dict(zip(['numTurns','success','numYes','score'],namespace['compute_metric'](str(pathlib.Path(session_dir)/(game.item+'.txt')))))
    if ended:public['terminal']={'outcome':'success' if game.guesser_win else 'failure','officialMetrics':metrics,'rawNativeReward':game.reward(),'rawNativeNumYes':game.num_yes()}
    return {'kind':event['kind'],'privateState':state,'publicObservation':public,'stateHash':digest(state),'judgeRequest':event.get('request'),'metrics':metrics}

def next_event():
    e=out_queue.get(timeout=30)
    if e['kind']=='native_error':raise ValueError('Original EDA class execution failed')
    return snapshot(e)

configuration=None
for line in sys.stdin:
    rid=None
    try:
        q=json.loads(line);rid=q['id'];cmd=q['command']
        if cmd=='init':
            if game is not None:raise ValueError('Original fresh instance already initialized')
            configuration=q['configuration'];session_dir=q['sessionDir'];assert os.path.isabs(str(session_dir))
            args={'item':configuration['item'],'answerer_model':'gpt-3.5-turbo','num_turns':20}
            game=namespace['Q20GameCelebrity'](background=configuration.get('background',''),**args) if configuration['category']=='celebrities' else namespace['Q20Game'](**args)
            game.guesser=receive_question;thread=threading.Thread(target=play,daemon=True);thread.start();result=next_event()
        elif cmd=='act':
            if ended or pending is not None:raise ValueError('Not awaiting Player action')
            in_queue.put({'kind':'player_action','text':q['text']});result=next_event()
        elif cmd=='judge_response':
            if pending is None or ended:raise ValueError('No pending official judge request')
            pending=None;in_queue.put({'kind':'judge_response','text':q['text']});result=next_event()
        elif cmd=='probe':
            origins=[]
            for name,module in sorted(sys.modules.items()):
                p=getattr(getattr(module,'__spec__',None),'origin',None)
                if p not in [None,'built-in','frozen']:
                    p=pathlib.Path(p).resolve()
                    if p.is_file():origins.append({'module':name,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
            result={'executable':str(pathlib.Path(sys.executable).resolve()),'flags':{'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,'dont_write_bytecode':sys.flags.dont_write_bytecode},'startupFlags':sys.orig_argv[1:-1],'pycachePrefix':sys.pycache_prefix,'origins':origins,'originalASTBindings':bindings,'wholeOriginalPackageExecuted':False}
        elif cmd=='close':
            print(json.dumps({'id':rid,'ok':True,'result':None}),flush=True);break
        else:raise ValueError('Unknown native EDA command')
        print(json.dumps({'id':rid,'ok':True,'result':result},ensure_ascii=False,separators=(',',':')),flush=True)
    except Exception as e:
        print(json.dumps({'id':rid,'ok':False,'error':{'type':type(e).__name__,'message':'Original EDA protocol command failed'}}),flush=True)
