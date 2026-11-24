import sys,json,base64,io
from PIL import Image
im=Image.open(sys.argv[1]).convert('RGB')
assert im.size==(1920,508),im.size
out=[]
for i,name in enumerate(['head camera — fixed scene reference','left wrist camera — arm 0 contact','right wrist camera — arm 1 contact']):
    crop=im.crop((i*640,0,(i+1)*640,508))
    buf=io.BytesIO();crop.save(buf,format='PNG')
    out.extend([{'type':'text','text':'PUBLIC CAMERA CROP: '+name+'. Exact pixels from the current public triptych; no new sensor or inferred state.'},{'type':'image','source':{'type':'base64','media_type':'image/png','data':base64.b64encode(buf.getvalue()).decode()}}])
print(json.dumps(out))
