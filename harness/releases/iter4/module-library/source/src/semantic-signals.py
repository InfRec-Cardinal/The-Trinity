



import json,sys,re,pathlib,os,numpy as np
req=json.load(sys.stdin)
assert req.get('source') and req.get('items')
root=pathlib.Path(os.environ['GLOVE_ROOT'])
words=json.loads((root/'glove.6B.100d.vocab.json').read_text());ix={w:i for i,w in enumerate(words)}
vec=np.load(root/'glove.6B.100d.f64.npy',mmap_mode='r')
items=req['items']; names=[r['label'].lower() for r in items]
if any(w not in ix for w in names):
 print(json.dumps({'status':'unmodeled_alternative','missing':[w for w in names if w not in ix]}));sys.exit()
assert all(r['role'] in ['target','avoid','catastrophic'] for r in items)
labels=np.array([r['role']=='target' for r in items])
idx=[i for i,w in enumerate(words[:50000]) if re.fullmatch('[a-z]{3,}',w) and all(w not in n and n not in w for n in names)]
b=np.array(vec[[ix[w] for w in names]]);b/=np.linalg.norm(b,axis=1,keepdims=True)
c=np.array(vec[idx]);c/=np.linalg.norm(c,axis=1,keepdims=True)
sims=c@b.T;order=np.argsort(-sims,axis=1,kind='stable');ordered=np.take_along_axis(sims,order,axis=1)
prefix=np.cumprod(labels[order],axis=1).sum(axis=1)
choices=[]
for j,n in enumerate(prefix):
 n=int(n)
 if not n:continue
                                                                                
 while n and ordered[j,n-1]<0.23:n-=1
 if not n:continue
 margin=float(ordered[j,n-1]-ordered[j,n]) if n<len(names) else 1.0
 if margin<0.015:continue
 choices.append({'signal':words[idx[j]],'count':n,'predictedPrefix':[names[k] for k in order[j,:n]],'weakestSimilarity':float(ordered[j,n-1]),'margin':margin,'nextAlternative':names[order[j,n]] if n<len(names) else None})
                                                                                
                                                                                
targets=[names[i] for i in range(len(names)) if labels[i]]
if len(targets)<=16:
 bits={w:1<<i for i,w in enumerate(targets)};full=(1<<len(targets))-1
 groups={}
 for q in choices:
  mask=sum(bits[w] for w in q['predictedPrefix']);q['_mask']=mask
  if mask not in groups or (q['margin'],q['weakestSimilarity'])>(groups[mask]['margin'],groups[mask]['weakestSimilarity']):groups[mask]=q
 choices=list(groups.values());masks=list(groups)
 from functools import lru_cache
 @lru_cache(None)
 def steps(left):
  if not left:return 0
  anchor=left&-left
  return min([1+steps(left&~m) for m in masks if m&anchor]+[len(targets)+1])
 for q in choices:q['estimatedTotalSignals']=1+steps(full&~q.pop('_mask'))
else:
 for q in choices:q['estimatedTotalSignals']=len(targets)
choices.sort(key=lambda q:(-q['estimatedTotalSignals'],q['count'],q['margin'],q['weakestSimilarity']),reverse=True)
print(json.dumps({'status':'ranked' if choices else 'no_safe_prefix','recommendation':choices[0] if choices else None,'alternatives':choices[:8],'model':'public GloVe 6B 100d cosine; first 50000 vocabulary entries; common alphabetic words only','source':req['source'],'scope':'Conditional ranking model, not access to an actual teammate decision. Confirm signal meaning and legal form before acting; revise if observed responses disagree.'}))
