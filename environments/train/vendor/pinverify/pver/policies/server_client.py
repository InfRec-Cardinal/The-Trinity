import requests
import time
import base64
import io
import os
from PIL import Image

class ServerClient:
    def __init__(self, qwen_text_url, qwen_vl_url, gdino_url):
        self.qwen_text_url = qwen_text_url
        self.qwen_vl_url = qwen_vl_url
        self.gdino_url = gdino_url
        
    def _post_json_with_retry(self, url, payload, retries=2, backoff=1.5):
        for k in range(retries + 1):
            try:
                r = requests.post(url, json=payload, timeout=(5, 60))
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                return r.json()
            except Exception as e:
                if k < retries:
                    time.sleep(backoff ** k)
                else:
                    print(f"[ServerClient] Failed to call {url}: {e}")
                    return {}                

    def call_qwen_text(self, prompt: str):
        return self._post_json_with_retry(self.qwen_text_url, {"prompt": prompt})

    def call_qwen_vl(self, image_input, prompt: str):
                                       
        if isinstance(image_input, Image.Image):
             buf = io.BytesIO()
             image_input.save(buf, format="PNG")
             img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        elif isinstance(image_input, str):
             if os.path.isfile(image_input):
                 with open(image_input, "rb") as f:
                     img_b64 = base64.b64encode(f.read()).decode("utf-8")
             else:
                                                                              
                 if len(image_input) < 256 and (os.sep in image_input or "/" in image_input):
                      raise FileNotFoundError(f"Image file not found: {image_input}")
                 img_b64 = image_input
        else:
             raise ValueError("Invalid image input")
             
        return self._post_json_with_retry(self.qwen_vl_url, {"prompt": prompt, "image": img_b64})

    def call_gdino(self, image_input, prompt: str, box_threshold=0.25, text_threshold=0.25):
        if isinstance(image_input, Image.Image):
             buf = io.BytesIO()
             image_input.save(buf, format="PNG")
             img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        elif isinstance(image_input, str):
             if os.path.isfile(image_input):
                 with open(image_input, "rb") as f:
                     img_b64 = base64.b64encode(f.read()).decode("utf-8")
             else:
                 img_b64 = image_input
        else:
             raise ValueError("Invalid image input")
             
        payload = {
            "image": img_b64,
            "prompt": prompt,
            "box_threshold": box_threshold,
            "text_threshold": text_threshold
        }
        return self._post_json_with_retry(self.gdino_url, payload)

    def call_qwen_vl_multi(self, images: list, prompt: str, system: str = ""):
        pass                              
             
                                                                     
                                   
                                                                            
                
                                
           
        images_b64 = []
        for img in images:
            if isinstance(img, Image.Image):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                images_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
            elif isinstance(img, str):
                if os.path.isfile(img):
                    with open(img, "rb") as f:
                        images_b64.append(base64.b64encode(f.read()).decode("utf-8"))
                else:
                                                
                    images_b64.append(img)
            else:
                raise ValueError(f"Invalid image input type: {type(img)}")

                                
        multi_url = self.qwen_vl_url.replace("/qwen-vl", "/qwen-vl-multi")
        payload = {"prompt": prompt, "images": images_b64}
        if system:
            payload["system"] = system
        return self._post_json_with_retry(multi_url, payload)

