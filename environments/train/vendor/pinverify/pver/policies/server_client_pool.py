import requests
import time
import base64
import io
import os
import threading
from PIL import Image
from typing import List

class LoadBalancedServerClient:
    pass                                                                                    
                                                             
       
    def __init__(self, qwen_urls: List[str], gdino_urls: List[str]):
        pass             
                                                                                       
                                                                                         
           
        self.qwen_urls = qwen_urls
        self.gdino_urls = gdino_urls

                                         
        self.qwen_idx = 0
        self.gdino_idx = 0
        self.qwen_lock = threading.Lock()
        self.gdino_lock = threading.Lock()

        print(f"[LoadBalanced] Qwen endpoints: {len(qwen_urls)}")
        print(f"[LoadBalanced] GDINO endpoints: {len(gdino_urls)}")

    def _get_next_qwen_url(self):
        pass                                         
        with self.qwen_lock:
            url = self.qwen_urls[self.qwen_idx]
            self.qwen_idx = (self.qwen_idx + 1) % len(self.qwen_urls)
            return url

    def _get_next_gdino_url(self):
        pass                                          
        with self.gdino_lock:
            url = self.gdino_urls[self.gdino_idx]
            self.gdino_idx = (self.gdino_idx + 1) % len(self.gdino_urls)
            return url

    def _post_json_with_retry(self, base_url, endpoint, payload, retries=2, backoff=1.5):
        pass                                                                   

             
                                           
                                                       
                                 
           
        url = base_url + endpoint

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
                    print(f"[LoadBalanced] Failed to call {url}: {e}")
                    return {}                 

    def call_qwen_text(self, prompt: str):
        base_url = self._get_next_qwen_url()
        return self._post_json_with_retry(base_url, "/qwen-text", {"prompt": prompt})

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

        base_url = self._get_next_qwen_url()
        return self._post_json_with_retry(base_url, "/qwen-vl", {"prompt": prompt, "image": img_b64})

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

        base_url = self._get_next_gdino_url()
        return self._post_json_with_retry(base_url, "/groundingdino", payload)

    def call_qwen_vl_multi(self, images: list, prompt: str):
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

        base_url = self._get_next_qwen_url()
        return self._post_json_with_retry(base_url, "/qwen-vl-multi", {"prompt": prompt, "images": images_b64})


def create_client_from_config(cfg):
    pass                                                                  

                                                                             
                                                        
       
    from pver.policies.server_client import ServerClient

    server_cfg = cfg.server

                                           
    qwen_urls = server_cfg.get("qwen_urls", None)
    gdino_urls = server_cfg.get("gdino_urls", None)

    if qwen_urls and gdino_urls:
                        
        return LoadBalancedServerClient(qwen_urls=qwen_urls, gdino_urls=gdino_urls)
    else:
                                     
        qwen_text_url = server_cfg.get("qwen_text_url", "http://127.0.0.1:12182/qwen-text")
        qwen_vl_url = server_cfg.get("qwen_vl_url", "http://127.0.0.1:12182/qwen-vl")
        gdino_url = server_cfg.get("gdino_url", "http://127.0.0.1:12183/groundingdino")

        return ServerClient(
            qwen_text_url=qwen_text_url,
            qwen_vl_url=qwen_vl_url,
            gdino_url=gdino_url
        )
