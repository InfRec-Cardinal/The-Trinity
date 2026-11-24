                                                                                   

                                                                            
                                                                            
                                                                             
                                                                       
   
import sys, os, json, ast, io, contextlib, random, hashlib, importlib, types
                                                                                                     
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vendor', 'boxinggym'))
EP = os.environ.get('H0_NATIVE_EPISODE_DIR', os.getcwd())
os.environ['PYTENSOR_FLAGS'] = 'compiledir=' + EP + '/pytensor-cache,cxx=,blas__ldflags='
os.environ['MPLCONFIGDIR'] = EP + '/matplotlib-cache'
import numpy as np
import pymc as pm
import yaml
import tqdm
from boxing_gym.agents.agent import LMExperimenter

WORLD = {
 'hyperbolic': ('hyperbolic_temporal_discount', 'TemporalDiscount', 'DirectGoalNaive'),
 'location_finding': ('location_finding', 'Signal', 'DirectGoalNaive'),
 'death_process': ('death_process', 'DeathProcess', 'DirectDeathNaive'),
 'dugongs': ('dugongs', 'Dugongs', 'DirectGoalNaive'),
 'peregrines': ('peregrines', 'Peregrines', 'DirectGoalNaive'),
}
tree = ast.parse(open(BASE + '/run_experiment.py').read())
evaluate_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'evaluate')
namespace = {'tqdm': types.SimpleNamespace(tqdm=lambda x: x)}
exec(compile(ast.Module(body=[evaluate_node], type_ignores=[]), BASE + '/run_experiment.py', 'exec'), namespace)
official_evaluate = namespace['evaluate']
draw, prior = pm.draw, pm.sample_prior_predictive
def seeded_draw(*a, **kw):
    if kw.get('random_seed') is None: kw['random_seed'] = int(np.random.randint(0, 2**30))
    return draw(*a, **kw)
def seeded_prior(*a, **kw):
    if kw.get('random_seed') is None: kw['random_seed'] = int(np.random.randint(0, 2**30))
    return prior(*a, **kw)
pm.draw, pm.sample_prior_predictive = seeded_draw, seeded_prior

def clean(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, (tuple,list)): return [clean(v) for v in x]
    return x
def digest(x): return hashlib.sha256(json.dumps(clean(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
class NeedModel(Exception):
    def __init__(self, request, index): self.request, self.index = request, index
class FixtureClient:
    def __init__(self, receipts): self.receipts, self.index, self.requests = receipts, 0, []; self.messages = self
    def create(self, **kw):
        request = clean(kw); self.requests.append(request)
        i = self.index; self.index += 1
        if i >= len(self.receipts): raise NeedModel(request, i)
        receipt = self.receipts[i]
        if digest(request) != receipt['requestHash']: raise RuntimeError('Original novice SDK request receipt changed')
        return types.SimpleNamespace(content=[types.SimpleNamespace(text=receipt['text'])])
class PredictionQueue:
    def __init__(self, answers): self.answers, self.index = answers, 0
    def generate_predictions(self, question):
        if self.index >= len(self.answers): raise RuntimeError('H0 prediction batch incomplete')
        value = str(self.answers[self.index]); self.index += 1; return value
def metric(goal, domain, answers, prior_condition):
    result, questions, gts, predictions = official_evaluate('', goal, PredictionQueue(answers), 10, prior_condition)
    mean, std = map(float, result)
    error = 1-mean if domain == 'hyperbolic' else mean
    norm_mu = 1-goal.norm_mu if domain == 'hyperbolic' else goal.norm_mu
    return dict(rawOfficialMetric='accuracy' if domain == 'hyperbolic' else 'mse', rawOfficialMean=mean, rawOfficialStd=std,
                error=error, standardizedError=(error-norm_mu)/goal.norm_sigma, sourceNormMean=goal.norm_mu,
                sourceNormStd=goal.norm_sigma, questions=questions, groundTruth=clean(gts), predictions=predictions)
def run(q):
    c=q['configuration']; domain=c['domain']; include=c['include_prior']; seed=c['seed']
    if domain not in WORLD or type(seed) is not int or seed not in range(1,6) or type(include) is not bool: raise RuntimeError('Unknown first-five selector')
    random.seed(seed); np.random.seed(seed)
    module_name, env_name, goal_name = WORLD[domain]
    module=importlib.import_module('boxing_gym.envs.'+module_name)
    conf=yaml.safe_load(open(BASE+'/conf/envs/'+domain+'_direct_discovery.yaml'))
    env=getattr(module,env_name)(**conf['env_params']); goal=getattr(module,goal_name)(env)
    source_prompt=goal.get_system_message(include)
    goal.eval_pointer=0; pairs=[goal.get_goal_eval_question(include) for _ in range(10)]; goal.eval_pointer=0
    questions=[x[0] for x in pairs]; gts=clean([x[1] for x in pairs])
    phase='scientist_step0'; successes=0; metrics={}; queries=[]; observations=[]; success_flags=[]; programs=[]; explanation=None; last=None; calls=0
    client=FixtureClient(q.get('externalReceipts',[]))
    pub=dict(phase=phase,sourcePrompt=source_prompt,questions=questions,successfulExperiments=0,toolResult=None,remainingActions=25,com_limit=200)
    terminal=dict(ended=False)
    for action in q.get('actions',[]):
        if terminal['ended']: raise RuntimeError('Native action after terminal')
        calls+=1; kind=action['action']; feedback=None
        if kind=='submit_program': programs.append(action['program']); feedback={'accepted':True,'scored':False,'executed':False}
        elif phase in ('scientist_step0','scientist_step10') and kind=='answer_predictions':
            if len(action['predictions'])!=10: raise RuntimeError('Exactly ten answers required')
            metrics[phase]=metric(goal,domain,action['predictions'],include)
            phase='experiments' if phase=='scientist_step0' else 'explanation'
            feedback={'accepted':True,'correctnessFeedback':False}
        elif phase=='experiments' and kind=='run_experiment':
                                                                                
                                                                                 
                                                                            
                                                                         
            try:
                env.validate_input(action['design'])
            except (ValueError, TypeError, OverflowError) as malformed:
                observation, success = 'Error: original numeric design parser rejected input (' + type(malformed).__name__ + ').', False
            else:
                observation, success=env.run_experiment(action['design'])
            success=bool(success)
            queries.append(action['design']); observations.append(clean(observation)); success_flags.append(success)
            last=clean(observation); successes+=int(success)
            feedback={'observation':last,'success':success}
            if successes==10: phase='scientist_step10'
        elif phase=='explanation' and kind=='explain_to_novice':
            explanation=action['explanation']
            if not explanation.strip() or len(explanation.split())>200:
                terminal={'ended':True,'success':False,'reason':'missing_or_over_word_limit_explanation'}
            else:
                                                                                               
                novice=object.__new__(LMExperimenter)
                novice.model_name='claude-opus-5'; novice.temperature=0.0; novice.max_tokens=256
                novice.system=None; novice.messages=[]; novice.all_messages=[]; novice.llm=client
                novice.set_system_message(goal.get_naive_system_message(include)+explanation)
                try:
                    result, nq, ngt, predictions=official_evaluate('',goal,novice,10,include)
                except NeedModel as need:
                    return {'ok':True,'needsModel':True,'request':need.request,'externalIndex':need.index,'requestHash':digest(need.request)}
                mean,std=map(float,result); error=1-mean if domain=='hyperbolic' else mean
                norm_mu=1-goal.norm_mu if domain=='hyperbolic' else goal.norm_mu
                metrics['novice']={'rawOfficialMetric':'accuracy' if domain=='hyperbolic' else 'mse','rawOfficialMean':mean,'rawOfficialStd':std,'error':error,'standardizedError':(error-norm_mu)/goal.norm_sigma,'predictions':predictions,'questions':nq,'groundTruth':clean(ngt),'sdkCalls':client.index}
                passed=successes==10 and metrics['scientist_step10']['standardizedError']<metrics['scientist_step0']['standardizedError'] and metrics['novice']['standardizedError']<metrics['scientist_step0']['standardizedError']
                terminal={'ended':True,'success':bool(passed),'reason':'both_source_error_comparisons_strictly_improved' if passed else 'source_error_comparison_failed_or_tied'}
                feedback={'accepted':True,'noviceCompleted':True,'correctnessFeedback':False}; phase='completed'
        else: feedback={'accepted':False,'reason':'action_not_available_in_current_phase'}
        if calls>=25 and not terminal['ended']: terminal={'ended':True,'success':False,'reason':'25_action_budget'}
        pub={'phase':phase,'sourcePrompt':source_prompt,'questions':questions if phase in ('scientist_step0','scientist_step10') else [],'communicationPrompt':goal.get_comm_prompt(include_prior=include,com_limit=200) if phase=='explanation' else None,'successfulExperiments':successes,'toolResult':feedback,'remainingActions':max(0,25-calls),'com_limit':200}
    priv={'metrics':metrics,'evalQuestions':questions,'evalGroundTruth':gts,'queries':queries,'observations':observations,'successes':success_flags,'explanation':explanation,'programs':programs,'externalRequests':client.requests,'npState':clean(np.random.get_state()),'pythonState':clean(random.getstate()),'sourceLatent':{k:clean(v) for k,v in vars(env).items() if isinstance(v,(int,float,str,tuple,np.ndarray,np.generic)) and k not in ('env_name',)},'loadedModules':{n:getattr(m,'__file__',None) for n,m in sys.modules.items() if getattr(m,'__file__',None)}}
    return {'ok':True,'public':clean(pub),'terminal':terminal,'private':clean(priv),'nativeStateHash':digest({'public':pub,'terminal':terminal,'metrics':metrics,'npState':priv['npState'],'pythonState':priv['pythonState'],'latents':priv['sourceLatent']})}
for line in sys.stdin:
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): result=run(json.loads(line))
        print(json.dumps(result,allow_nan=False,separators=(',',':')),flush=True)
    except Exception as e:
        print(json.dumps({'ok':False,'message':type(e).__name__+': '+str(e)}),flush=True)
