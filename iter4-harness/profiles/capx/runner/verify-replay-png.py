import sys,json,base64,io
import numpy as np
from PIL import Image
r=json.load(sys.stdin);a=np.array(Image.open(io.BytesIO(base64.b64decode(r['a']))).convert('RGB'));b=np.array(Image.open(io.BytesIO(base64.b64decode(r['b']))).convert('RGB'))
assert a.shape==b.shape,'image dimensions changed'
d=np.abs(a.astype('int16')-b.astype('int16'));n=int(np.count_nonzero(np.any(d,axis=2)));total=int(a.shape[0]*a.shape[1]);m=int(d.max());ok=m<=1 and n<=max(1,int(total*0.0001))
print(json.dumps({'passed':ok,'maxChannelDifference':m,'changedPixels':n,'totalPixels':total}))
