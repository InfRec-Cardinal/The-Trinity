from PIL import Image,ImageDraw
import json,sys,math,io
q=json.load(sys.stdin);n=len(q['frames']);cols=min(2,n);rows=math.ceil(n/cols);out=Image.new('RGB',(cols*400,rows*260),'white');draw=ImageDraw.Draw(out)
for i,f in enumerate(q['frames']):
 im=Image.open(f['path']).convert('RGB');im.thumbnail((396,232));x=(i%cols)*400;y=(i//cols)*260;out.paste(im,(x,y+24));draw.text((x+4,y+4),'Delivered frame '+str(f['index']),fill='black')
for quality in (85,75,65,50,35):
 b=io.BytesIO();out.save(b,'JPEG',quality=quality,optimize=True)
 if len(b.getvalue())<=150000:break
if len(b.getvalue())>150000:
 out.thumbnail((600,800));b=io.BytesIO();out.save(b,'JPEG',quality=35,optimize=True)
assert len(b.getvalue())<=150000,'Derived overview exceeded byte limit'
open(q['output'],'wb').write(b.getvalue())
print(json.dumps({'operation':'bounded_labelled_overview_of_existing_frames','frameIndices':[f['index'] for f in q['frames']],'newEvidenceAcquired':False,'lossyPreview':True,'originalDeliveredFramesPreserved':True,'bytes':len(b.getvalue())}))
