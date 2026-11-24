                                                                           
                                                                                                         
                                                                                              
                                                                                                          
                                                                                                        
                                             
                                                        
import base64, io, json, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from score import extract_characters_regex_v2              

PROTO = sys.stdout; sys.stdout = sys.stderr
LIMIT = 28_000_000
Q = {q["questionId"]: q for q in json.load(open(os.path.join(HERE, "questions.json")))}


def emit(o):
    PROTO.write(json.dumps(o) + "\n"); PROTO.flush()


def frames_png(d, side):
    out = []
    for k in range(1, 65):
        im = Image.open(os.path.join(HERE, d, f"frame-{k:02d}.jpg")).convert("RGB")
        w, h = im.size; s = side / max(w, h)
        if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, "PNG", optimize=True); out.append(base64.b64encode(b.getvalue()).decode())
    return out


q = Q[sys.argv[1]]
for side in (768, 640, 512):
    imgs = frames_png(q["frameDir"], side)
    if sum(map(len, imgs)) <= LIMIT: break
emit({"kind": "player_request", "message": "\n".join(q["promptParts"]), "images": imgs, "frameSide": side})
line = sys.stdin.readline()
if not line: raise SystemExit("player stream closed")
resp = str(json.loads(line).get("action", ""))
pred = extract_characters_regex_v2(resp)
emit({"kind": "terminal", "questionId": q["questionId"], "videoId": q["videoId"], "groupId": q["groupId"], "rawResponse": resp,
      "prediction": pred, "answer": q["answer"], "correct": pred == q["answer"], "frameSide": side,
      "groupType": q.get("groupType"), "groupStructure": q.get("groupStructure"), "level": q.get("level")})
