import sys,json,io,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
q=json.load(sys.stdin);out=Path(q['outDir']);out.mkdir(parents=True,exist_ok=True)
try:font=ImageFont.truetype('DejaVuSans.ttf',20)
except OSError:font=ImageFont.load_default()
assert len(q['frames'])==len(q['selected'])<=96
sheets=[]
for start in range(0,len(q['frames']),4):
    chunk=q['frames'][start:start+4];canvas=Image.new('RGB',(768,math.ceil(len(chunk)/2)*620),'white');draw=ImageDraw.Draw(canvas)
    for offset,f in enumerate(chunk):
        i=start+offset;selection=q['selected'][i];assert selection['sampleIndex']==f['sampleIndex'] and selection['sha256']==f['sha256']
        im=Image.open(f['path']).convert('RGB');w,h=im.size;left,top,right,bottom=selection['box']
        crop=im.crop((int(left*w),int(top*h),min(w,math.ceil(right*w)),min(h,math.ceil(bottom*h))))
        x=offset%2*384;y=offset//2*620
        draw.text((x+8,y+7),f"Sample {f['sampleIndex']:02d} | {f['seconds']:.3f}s",font=font,fill='black')
        thumb=im.copy();thumb.thumbnail((180,105));canvas.paste(thumb,(x+(384-thumb.width)//2,y+35))
        crop.thumbnail((370,470));canvas.paste(crop,(x+(384-crop.width)//2,y+145))
    for quality in [80,70,60,50]:
        b=io.BytesIO();canvas.save(b,'JPEG',quality=quality,optimize=True)
        if len(b.getvalue())<=150000:break
    assert len(b.getvalue())<=150000,'Actor evidence image exceeds transport limit'
    name=f'focus-{start//4}.jpg';(out/name).write_bytes(b.getvalue());sheets.append(name)
print(json.dumps({'sheets':sheets,'newTimestampsAcquired':False,'pixels':'same original-video times at native detail, automatic candidate crop plus full context','sampleOrder':'row-major, 4 samples per sheet'}))
