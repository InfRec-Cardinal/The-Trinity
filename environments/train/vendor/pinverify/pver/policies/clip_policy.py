                                          

                                                                               
                                                                       
                              

                                                                         
                                                                      
   

import os
import io
import json
import base64
from typing import Dict, Any, Optional, Tuple, List

import torch
from PIL import Image
from omegaconf import OmegaConf

from pver.policies.server_client import ServerClient


class CLIPPolicy:
    pass                                                    

    SECTORS = ["front", "front-left", "back-left", "back", "back-right", "front-right"]

    def __init__(self, cfg, client: ServerClient):
        self.cfg = cfg
        self.client = client
        self.bbox_mode = cfg.method.get("bbox_mode", "dino")
        self.threshold = cfg.method.get("clip_threshold", 0.25)
        self.aggregation = cfg.method.get("aggregation", "max")                              
        self.desc_aggregation = cfg.method.get("desc_aggregation", "avg")                                       
        self.stop_margin = cfg.method.get("clip_stop_margin", 0.0)                                      

                      
        prompt_dir = os.path.join(os.path.dirname(__file__), "../../configs/prompts")

                                              
        cat_file = cfg.prompt.get("category_file")
        self.p_cat = None
        if cat_file:
            cat_path = os.path.join(prompt_dir, cat_file)
            if os.path.exists(cat_path):
                self.p_cat = OmegaConf.load(cat_path)

                                                    
        merge_file = cfg.prompt.get("merge_file")
        self.p_merge = None
        if merge_file:
            merge_path = os.path.join(prompt_dir, merge_file)
            if os.path.exists(merge_path):
                self.p_merge = OmegaConf.load(merge_path)

                                                          
        clip_model_name = cfg.method.get("clip_model", "openai/clip-vit-large-patch14")
        print(f"[CLIPPolicy] Loading model: {clip_model_name}")
        from transformers import AutoModel, AutoProcessor
        self.clip_model = AutoModel.from_pretrained(clip_model_name).eval()
        self.clip_processor = AutoProcessor.from_pretrained(clip_model_name)

                                                                                  
        model_class = type(self.clip_model).__name__.lower()
        self.is_siglip = "siglip" in model_class

                                  
        if torch.cuda.is_available():
            self.clip_device = torch.device("cuda")
            self.clip_model = self.clip_model.to(self.clip_device)
        else:
            self.clip_device = torch.device("cpu")
        scoring_mode = "sigmoid" if self.is_siglip else "cosine"
        print(f"[CLIPPolicy] Model loaded on {self.clip_device} (scoring: {scoring_mode})")

                                     
        self.multi_view = cfg.env.get("max_steps", 1) > 1
        self.nbv_module = None
        if self.multi_view:
            from pver.policies.nbv import RandomNBV, FarthestPointNBV
            nbv_type = cfg.method.get("nbv", {}).get("type", "random")
            if nbv_type == "farthest" or nbv_type == "fps":
                self.nbv_module = FarthestPointNBV(cfg.method.get("nbv"))
            else:
                self.nbv_module = RandomNBV(cfg.method.get("nbv"))

                                                                                          
        self.category_cache_static = {}
        cache_dir = None
        if cfg.dataset.get("category_cache_path"):
            try:
                with open(cfg.dataset.category_cache_path, 'r', encoding='utf-8') as f:
                    self.category_cache_static = json.load(f)
                print(f"[CLIPPolicy] Loaded {len(self.category_cache_static)} categories from cache.")
                cache_dir = os.path.dirname(cfg.dataset.category_cache_path)
            except Exception as e:
                print(f"[CLIPPolicy] Failed to load category cache: {e}")

                                                                        
        self.merge_cache_static = {}
        if cache_dir:
            merge_cache_path = os.path.join(cache_dir, "merge_cache.json")
            if os.path.exists(merge_cache_path):
                try:
                    with open(merge_cache_path, 'r', encoding='utf-8') as f:
                        self.merge_cache_static = json.load(f)
                    print(f"[CLIPPolicy] Loaded {len(self.merge_cache_static)} merged descriptions from cache.")
                except Exception as e:
                    print(f"[CLIPPolicy] Failed to load merge cache: {e}")

                                      
        self.target_class = ""
        self.object_id = None
        self.query_descs = []
        self.coarse_dialogue = None

    def reset(self, obs):
        pass                               
        meta = obs.get("meta", {})
        self.current_episode = meta

                          
        query_descs = meta.get("query_descriptions") or meta.get("text_pos") or [""] * 3
        self.query_descs = query_descs if isinstance(query_descs, list) else [query_descs] * 3
        while len(self.query_descs) < 3:
            self.query_descs.append(self.query_descs[0] if self.query_descs else "")

                   
        self.object_id = str(meta.get("query_object_id") or meta.get("object_id") or "unknown")

                                                                    
        self.merged_description = None
        self.merge_dialogue = None
        if self.desc_aggregation == "merged" and self.query_descs[0]:
            if self.object_id in self.merge_cache_static:
                                         
                cached = self.merge_cache_static[self.object_id]
                self.merged_description = cached["merged_description"]
                self.merge_dialogue = {
                    "mode": "cache",
                    "merged_result": self.merged_description
                }
            elif self.p_merge:
                                        
                merge_prompt = self.p_merge.template.format(
                    desc1=self.query_descs[0],
                    desc2=self.query_descs[1] if len(self.query_descs) > 1 else "",
                    desc3=self.query_descs[2] if len(self.query_descs) > 2 else ""
                )
                merge_res = self.client.call_qwen_text(merge_prompt)
                merged_text = merge_res.get("text", "").strip()
                if not merged_text:
                    merged_text = ". ".join(d for d in self.query_descs if d)
                self.merged_description = merged_text
                self.merge_dialogue = {
                    "prompt": merge_prompt,
                    "response": merge_res.get("text", ""),
                    "merged_result": merged_text
                }

                                                                                     
        self.target_class = "object"
        self.coarse_dialogue = None
        if self.bbox_mode != "gt":
            if self.object_id in self.category_cache_static:
                self.target_class = self.category_cache_static[self.object_id].get("pred_coarse", "object")
                self.coarse_dialogue = {"mode": "cache", "result": self.target_class}
            elif self.p_cat and self.query_descs[0]:
                categories = list(self.p_cat.get("categories", []))
                categories_str = '", "'.join(categories) if categories else "object"
                prompt = self.p_cat.template.format(
                    categories_str=categories_str,
                    desc1=self.query_descs[0],
                    desc2=self.query_descs[1] if len(self.query_descs) > 1 else self.query_descs[0],
                    desc3=self.query_descs[2] if len(self.query_descs) > 2 else self.query_descs[0]
                )
                res = self.client.call_qwen_text(prompt)
                self.target_class = res.get("text", "object").strip()
                if self.p_cat.get("categories") and self.target_class not in self.p_cat.categories:
                    self.target_class = "object"
                self.coarse_dialogue = {
                    "prompt": prompt,
                    "response": res.get("text", ""),
                    "result": self.target_class
                }

                          
        self.view_scores = []                                         
        self.visited_abs_indices = set()
        self.current_abs_idx = obs.get("current_sector", 0)
        self.visited_abs_indices.add(self.current_abs_idx)
        self._failed_abs_sectors = set()
        self._last_target_abs_idx = None

    def act(self, obs) -> Dict[str, Any]:
        pass                   
        step = obs.get("step_count", 0)
        img_path = obs.get("rgb_path", "")

                                                      
        is_unreachable_nav_fail = False
        if obs.get("navigation_failed") and self._last_target_abs_idx is not None:
            self._failed_abs_sectors.add(self._last_target_abs_idx)
            is_unreachable_nav_fail = True
        self._last_target_abs_idx = None

                              
        env_sector = obs.get("current_sector", -1)
        if env_sector >= 0:
            self.current_abs_idx = env_sector
            self.visited_abs_indices.add(env_sector)

                          
        crop_pil, detection_confidence = self._detect_and_crop(img_path, obs)

                       
        if self.desc_aggregation == "merged":
                                                                             
            merged_text = self.merged_description or " ".join(d for d in self.query_descs if d)
            scores = self._compute_clip_scores(crop_pil, [merged_text])
            view_score = scores[0] if scores else 0.0
        else:
            scores = self._compute_clip_scores(crop_pil, self.query_descs)
            if self.desc_aggregation == "max":
                view_score = max(scores) if scores else 0.0
            else:       
                view_score = sum(scores) / len(scores) if scores else 0.0
                                                                        
                                                                                   
        if not is_unreachable_nav_fail:
            self.view_scores.append((self.current_abs_idx, view_score, scores))

                     
        is_final = step >= self.cfg.env.max_steps - 1

                                                                            
                                                                                 
                                                                                         
        adaptive_stopped = False                                          
        min_views = 2                                                  
        if not is_final and self.multi_view and self.stop_margin > 0:
            k = len(self.view_scores)                          
            all_so_far = [s[1] for s in self.view_scores]

            if k >= min_views:
                running_avg = sum(all_so_far) / k
                if running_avg > self.threshold + self.stop_margin:
                    is_final = True
                    adaptive_stopped = True
                elif running_avg < self.threshold - self.stop_margin:
                    is_final = True
                    adaptive_stopped = True

        if is_final or not self.multi_view:
                                                                                         
            effective_scores = [s[1] for s in self.view_scores]
            if not effective_scores:
                                                                                          
                effective_scores = [view_score]
            if self.aggregation == "max":
                agg_score = max(effective_scores)
            else:       
                agg_score = sum(effective_scores) / len(effective_scores)

            decision = "Yes" if agg_score > self.threshold else "No"

            action = {
                "decision": decision,
                "_step_prediction": decision,
                "_reason": f"clip:desc_{self.desc_aggregation},view_{self.aggregation}={agg_score:.3f}(thr={self.threshold})",
                "_clip_scores": {
                    "per_view": [(s[0], round(s[1], 4), [round(x, 4) for x in s[2]]) for s in self.view_scores],
                    "aggregated": round(agg_score, 4),
                    "threshold": self.threshold,
                    "method": self.aggregation,
                    "descriptions": self.query_descs,
                },
                "_debug_crop": self._pil_to_b64(crop_pil),
                "_coarse_cat": self.target_class,
                "_detection_confidence": detection_confidence,
                "_current_abs_sector": self.SECTORS[self.current_abs_idx] if self.current_abs_idx < 6 else str(self.current_abs_idx),
                "_visited_abs_sectors": [self.SECTORS[s] for s in sorted(self.visited_abs_indices) if s < 6],
                "_adaptive_stopped": adaptive_stopped,
            }
            if self.coarse_dialogue and step == 0:
                action["_coarse_dialogue"] = self.coarse_dialogue
            if self.merge_dialogue and step == 0:
                action["_merge_dialogue"] = self.merge_dialogue
            return action

                                            
        nav_rel = "front"
        nbv_debug = {}
        if self.nbv_module:
            context = {
                "ep_meta": obs.get("meta", {}),
                "failed_abs_sectors": self._failed_abs_sectors,
            }
            nav_rel, target_abs_idx, nbv_debug = self.nbv_module.decide_next_view(
                tracker_state={},
                img_path=img_path,
                prompt_template=None,
                current_abs_idx=self.current_abs_idx,
                visited_abs_indices=self.visited_abs_indices,
                num_sectors=self.cfg.env.sectors,
                context=context
            )
            self._last_target_abs_idx = target_abs_idx

        action = {
            "decision": "Unsure",
            "nav_rel": nav_rel,
            "_step_prediction": "Yes" if view_score > self.threshold else "No",
            "_clip_scores": {
                "current_view": round(view_score, 4),
                "all_scores": [round(x, 4) for x in scores],
                "descriptions": self.query_descs,
                "threshold": self.threshold,
            },
            "_debug_crop": self._pil_to_b64(crop_pil),
            "_nbv_debug": nbv_debug,
            "_coarse_cat": self.target_class,
            "_detection_confidence": detection_confidence,
            "_current_abs_sector": self.SECTORS[self.current_abs_idx] if self.current_abs_idx < 6 else str(self.current_abs_idx),
            "_visited_abs_sectors": [self.SECTORS[s] for s in sorted(self.visited_abs_indices) if s < 6],
        }
        if self.coarse_dialogue and step == 0:
            action["_coarse_dialogue"] = self.coarse_dialogue
        if self.merge_dialogue and step == 0:
            action["_merge_dialogue"] = self.merge_dialogue
        return action

                            

    def _compute_clip_scores(self, image: Image.Image, texts: List[str]) -> List[float]:
        pass                                              

                                                          
                                                                  
           
        if image is None or not texts:
            return [0.0] * len(texts)

        try:
            valid_texts = [t if t else "an object" for t in texts]

                                                                      
            padding = "max_length" if self.is_siglip else True
            inputs = self.clip_processor(
                text=valid_texts, images=image,
                return_tensors="pt", padding=padding
            )
            inputs = {k: v.to(self.clip_device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.clip_model(**inputs)

                if self.is_siglip:
                                                                                       
                    scores = torch.sigmoid(outputs.logits_per_image)[0].cpu().tolist()
                else:
                                                        
                    img_emb = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
                    txt_emb = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
                    scores = (img_emb @ txt_emb.T)[0].cpu().tolist()

            return scores
        except Exception as e:
            print(f"[CLIPPolicy] scoring error: {e}")
            return [0.0] * len(texts)

                                                          

    def _detect_and_crop(self, img_path: str, obs: Dict) -> Tuple[Optional[Image.Image], float]:
        pass                                                                   
        if not img_path:
            return Image.new("RGB", (224, 224)), 0.0

        box_result = None
        detection_confidence = 1.0

        if self.bbox_mode == "gt":
            meta = obs.get("meta", {})
            captures = meta.get("captures", [])
            base_name = os.path.basename(img_path)

            for cap in captures:
                c_path = cap.get("rgb_filename") or cap.get("rgb", "")
                if os.path.basename(c_path) == base_name:
                    if cap.get("mask_bbox_xyxy") is not None:
                        box_result = {"results": [{"score": 1.0, "box": cap["mask_bbox_xyxy"]}]}
                        detection_confidence = 1.0
                    else:
                        box_result = {"results": []}
                        detection_confidence = 0.1
                    break

        if not box_result:
                       
            box_result = self.client.call_gdino(img_path, self.target_class)
            results = box_result.get("results", [])
            if results:
                detection_confidence = max(r.get("score", 0.5) for r in results)
            else:
                detection_confidence = 0.1

        crop_pil = self._crop_image(img_path, box_result)
        return crop_pil, detection_confidence

    def _crop_image(self, img_path: str, gdino_res: Dict) -> Image.Image:
        pass                                     
        try:
            img = Image.open(img_path).convert("RGB")
            results = gdino_res.get("results", [])
            if results:
                best = max(results, key=lambda x: x["score"])
                box = best["box"]
                w, h = img.size
                pad = 3
                x1 = max(0, min(w, box[0] - pad))
                y1 = max(0, min(h, box[1] - pad))
                x2 = max(0, min(w, box[2] + pad))
                y2 = max(0, min(h, box[3] + pad))
                if x2 > x1 and y2 > y1:
                    crop = img.crop((x1, y1, x2, y2))
                    cw, ch = crop.size
                    if min(cw, ch) < 512:
                        s = 512.0 / min(cw, ch)
                        new_w, new_h = int(cw * s + 0.5), int(ch * s + 0.5)
                        crop = crop.resize((new_w, new_h), Image.BICUBIC)
                    return crop
                                  
            w, h = img.size
            if min(w, h) < 512:
                s = 512.0 / min(w, h)
                img = img.resize((int(w * s + 0.5), int(h * s + 0.5)), Image.BICUBIC)
            return img
        except Exception as e:
            print(f"[CLIPPolicy] Crop error: {e}")
            return Image.new("RGB", (224, 224))

                         

    @staticmethod
    def _pil_to_b64(pil_img: Image.Image) -> str:
        pass                                                         
        if pil_img is None:
            return ""
        try:
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG")
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_str}"
        except:
            return ""
