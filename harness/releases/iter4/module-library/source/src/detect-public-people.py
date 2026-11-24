import sys,json,os,contextlib
from pathlib import Path
q=json.load(sys.stdin)
cfg=Path(q['configDir']);cfg.mkdir(parents=True,exist_ok=True);os.environ['YOLO_CONFIG_DIR']=str(cfg)
with contextlib.redirect_stdout(sys.stderr):
    from ultralytics import YOLO
    model=YOLO(q['model'])
    results=model.predict([f['path'] for f in q['frames']],classes=[0],conf=.4,imgsz=640,device=0,batch=16,verbose=False)
rows=[]
for f,r in zip(q['frames'],results):
    rows.append({'sampleIndex':f['sampleIndex'],'sha256':f['sha256'],'detections':[{'box':b,'confidence':c} for b,c in zip(r.boxes.xyxyn.cpu().tolist(),r.boxes.conf.cpu().tolist())]})
print(json.dumps({'frames':rows,'detector':'yolo11n person proposals only'}))
