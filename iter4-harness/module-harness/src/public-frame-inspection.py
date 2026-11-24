import json,sys,math
from PIL import Image
q=json.load(sys.stdin);image=Image.open(q['input']);w,h=image.size
x,y,bw,bh=q['box'];assert all(math.isfinite(v) for v in [x,y,bw,bh])
assert min(x,y)>=0 and min(bw,bh)>0 and x+bw<=1.000001 and y+bh<=1.000001
bounds=(round(x*w),round(y*h),round((x+bw)*w),round((y+bh)*h))
assert bounds[2]-bounds[0]>=4 and bounds[3]-bounds[1]>=4
crop=image.crop(bounds).convert('RGB');scale=min(4,768/max(crop.size));crop=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS);crop.save(q['output'])
print(json.dumps({'originalDimensions':[w,h],'cropBounds':bounds,'renderedDimensions':list(crop.size),'operation':'crop_and_lanczos_resize_only','newEvidenceAcquired':False}))
