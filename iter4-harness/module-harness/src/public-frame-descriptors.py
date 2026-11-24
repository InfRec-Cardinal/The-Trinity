
import json,sys,os
os.environ['HF_HUB_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1'
os.environ['TRANSFORMERS_VERBOSITY']='error'
os.environ['TRANSFORMERS_OFFLINE']='1'
from PIL import Image
import torch
from transformers import AutoImageProcessor,AutoTokenizer,SiglipModel
q=json.load(sys.stdin)
model_path=os.environ['SIGLIP_MODEL_PATH']
processor=AutoImageProcessor.from_pretrained(model_path,local_files_only=True)
device='cuda' if torch.cuda.is_available() else 'cpu'
model=SiglipModel.from_pretrained(model_path,local_files_only=True).to(device).eval()
tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
rows=[]
with torch.inference_mode():
 query=q.get('query') or 'a video frame'
 text_inputs=tokenizer([query],padding='max_length',max_length=64,truncation=True,return_tensors='pt').to(device)
 text_vector=torch.nn.functional.normalize(model.get_text_features(**text_inputs).pooler_output.float(),dim=-1)
 for start in range(0,len(q['frames']),16):
  batch=q['frames'][start:start+16]
  images=[]
  for f in batch:
   im=Image.open(f['path']).convert('RGB')
   if f.get('box') is not None:
    box=f['box'];assert len(box)==4 and all(0<=x<=1 for x in box) and box[2]>box[0] and box[3]>box[1]
    w,h=im.size;im=im.crop(tuple(int(x*d) for x,d in zip(box,[w,h,w,h])));im.thumbnail((384,768))
   images.append(im)
  inputs=processor(images=images,return_tensors='pt').to(device)
  pooled=torch.nn.functional.normalize(model.get_image_features(**inputs).pooler_output.float(),dim=-1)
  relevance=(pooled@text_vector.T).flatten().cpu().tolist()
  for f,v,score in zip(batch,pooled.cpu().tolist(),relevance):rows.append({'index':f['index'],'sha256':f['sha256'],'descriptor':[round(x,7) for x in v],'relevance':round(score,7)})
json.dump({'frames':rows,'method':'siglip-base-patch16-224@7fd15f0-normalized-pooler','publicPixelsAndQuestionOnly':True,'query':query,'device':device},sys.stdout)
