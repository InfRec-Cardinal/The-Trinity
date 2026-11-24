
import sys,json,math,hashlib,io
from pathlib import Path
import cv2
from PIL import Image,ImageDraw

q=json.load(sys.stdin)
times=q['times']
assert 1<=len(times)<=96 and all(math.isfinite(t) for t in times)
c=cv2.VideoCapture(q['input'])
fps=c.get(cv2.CAP_PROP_FPS);count=int(c.get(cv2.CAP_PROP_FRAME_COUNT))
assert abs(fps-q['expectedFps'])<.001 and count==q['expectedFrameCount']
indices=sorted(set(round(t*fps) for t in times))
assert indices[0]>=0 and indices[-1]<count
root=Path(q['outDir']);root.mkdir(parents=True,exist_ok=True)
frames=[];images=[]
for index in indices:
    c.set(cv2.CAP_PROP_POS_FRAMES,index)
    ok,frame=c.read();assert ok,'Source decode failed'
    im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
    native=None
    if q.get('saveNativeFrames'):
        native=f'native-{index}.jpg';im.save(root/native,'JPEG',quality=92)
    im.thumbnail((768,768))
    filename=f'frame-{index}.jpg';im.save(root/filename,'JPEG',quality=88)
    frames.append({'sampleIndex':len(frames),'sourceFrame':index,'seconds':index/fps,'path':filename,'nativePath':native,'nativeSha256':hashlib.sha256((root/native).read_bytes()).hexdigest() if native else None,'sha256':hashlib.sha256((root/filename).read_bytes()).hexdigest()})
    images.append(im)
c.release()
sheets=[]
for start in range(0,len(frames),8):
    chunk=frames[start:start+8];cols=2;rows=math.ceil(len(chunk)/cols)
    sheet=Image.new('RGB',(768,rows*244),'white');draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(chunk):
        im=images[start+i].copy();im.thumbnail((380,216));x=i%cols*384;y=i//cols*244
        sheet.paste(im,(x,y+25));draw.text((x+5,y+5),f"Sample {start+i} | {f['seconds']:.3f}s | frame {f['sourceFrame']}",fill='black')
    filename=f'sheet-{start//8}.jpg';sheet.save(root/filename,'JPEG',quality=82,optimize=True)
    assert (root/filename).stat().st_size<400000
    sheets.append(filename)
print(json.dumps({'frames':frames,'sheets':sheets,'fps':fps,'sourceFrameCount':count}))
