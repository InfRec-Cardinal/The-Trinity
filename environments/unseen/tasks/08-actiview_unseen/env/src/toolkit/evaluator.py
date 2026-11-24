import sys, os
import transformers
import re, copy, json
import random
random.seed(1234)

from PIL import Image
import torch

from transformers.image_utils import load_image 
from tqdm import tqdm

from prompts_config import *
from image_utils import pil_image_to_base64, test_split_image
from model_config import predict

"""
this class tackles the prompt template of our 4 types of evaluation: 
1. full: general vqa
2. zooming: select a view or views, and then answer question based on selected views
3. shifting: shifting to different or multiple views, and then answer question
4. mixed
"""

class Evaluator:
    def __init__(self, 
            data_path=None,  
            data_file_name='data.json',
            image_path=None,
            image_split_path=None,
            bbox_dir=None, 
            model='Brote', 
            initial_view=3, 
            num_split=4,
            **kwargs):

        assert (data_path is not None), "data_path not provided" 
                                                                                                
        if image_path is None:
            image_path = data_path
        if image_split_path is None:
            image_split_path = data_path

                   
        with open(os.path.join(data_path, data_file_name)) as fr:
            data_json = json.loads(fr.read())
            self.data = data_json['data']
            print('Data info:', data_json['meta']['info'])
            print('Num of loaded qa pairs:', len(self.data))

        print('converting path')
        for instance in self.data:
                                                                                              

            imgs = instance['images']
            new_imgs = [os.path.join(image_path, imgs[0].split('/')[-1])]
            for img in imgs[1:]:
                new_imgs.append(os.path.join(image_split_path, img.split('/')[-1]))
            instance['images'] = new_imgs

        self.answers = [d['answer'] for d in self.data]
        self.options = [d['options'] for d in self.data]

        self.bbox_dir = bbox_dir
        self.model_name = model
        self.num_split = num_split
        if num_split != 4:
            self.splits2grid = {6: (3,2), 8: (4,2), 9: (3,3), 16: (4,4)}
         
        self.eval_format_func = {
                'full':self.format_data4full, 
                'shifting': self.format_data4shifting, 
                'zooming': self.format_data4zooming, 'zoomingQA': self.format_data4zooming_qa,  
                }

        if model in ['Brote', 'MMICL']:
            image_placeholder = "图"
            self.replace_token = "".join(32*[image_placeholder])
            self.placeholder = """<image{i}>{placeholder}"""

        self.image_views = ["upperleft", "lowerleft", "upperright", "lowerright"]
        self.initial_image_views = {3:('upperleft', 'Lower, Right'), 4:('lowerleft', 'Upper, Right'), 5:('upperright', 'Lower, Left'), 6:('lowerleft', 'Upper, Right')}

    def cal_acc(self, pred):
        assert len(pred) == len(self.answers)
        options = ["A", "B", "C", "D", "E", "F", "G", "H", "Z"]
        acc = 0.
        for p, y, ops in zip(pred, self.answers, self.options):
            try:
                if "Answer:" in p:
                    p = p.split('Answer:')[1].strip()
                p = options.index(p.split('.')[0])
            except:
                if p.lower().strip() == ops[y].lower():
                    p = y
                else:
                    p = -1
            if p == y: acc+=1.
        return acc/len(pred)

    def format_data4full(self):
        images = []
        prompts = []
        for d in self.data:
            images.append(Image.open(d['images'][1]))
            img = self.placeholder.format(i=0, placeholder=self.replace_token)
            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            prompts.append(QA_TEMPLATES.format(image=img, question=d['question'], option=option))
        return images, prompts

    def format_data4shifting(self, model=None, processor=None, initial_only=False, pre_define_initial=[]):
        pass                                    
                                                                              
           
        if model is None: 
            print('please provide a model for prediction')
            return []

        preds = []
        all_used_views = []
        orders = []
        for idx, d in enumerate(self.data):
            if pre_define_initial:
                start_index = pre_define_initial[idx]
            else:
                if self.num_split ==4:
                    start_index = random.randint(0, 3)                               
                else:
                    start_index = random.randint(0, self.num_split-1)                               
            orders.append(start_index)
            images = []
            img_str = "" 
            i = 0
            used_views = []
            if initial_only:
                used_views.append(start_index)
                images.append(Image.open(d['images'][start_index+3]))
                img_str += f" <image{i}>{self.replace_token} is the {self.image_views[start_index]} view." 
            else:
                if self.num_split ==4:
                    view_order = self.image_views[start_index:] + self.image_views[:start_index]                                                                               
                else:
                    _order = list(range(1, self.num_split+1))
                    order_str = f"{self.splits2grid[self.num_split][0]}*{self.splits2grid[self.num_split][1]} grids"
                    view_order = _order[start_index:] + _order[:start_index] 
                    _, parts = test_split_image(Image.open(d['images'][0]), self.splits2grid[self.num_split])
                while view_order:
                    view = view_order.pop(0)
                    if self.num_split ==4:
                        view_idx = self.image_views.index(view)
                        images.append(Image.open(d['images'][view_idx+3]))
                    else:
                        view_idx = view-1
                        view = f'no. {view}'
                        images.append(parts[view_idx])
                    used_views.append(view_idx)
    
                    img_str += f" <image{i}>{self.replace_token} is the {view} view," 
                    if self.num_split ==4:
                        prompt = [SHIFT_DECISION_TEMPLATES_BROTE1.format(images=img_str, question=d['question'])]
                    else:
                        prompt = [SHIFT_DECISION_TEMPLATES_BROTE1_ANY.format(num_splits=self.num_split, order=order_str, images=img_str, question=d['question'])]
                    generation = predict(model, processor, images, prompt)
                                                
                                                       
                    if generation[0].lower() == 'no':
                        break
                    i += 1

            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            prompt = [QA_TEMPLATES.format(image=img_str, question=d['question'], option=option)]
            all_used_views.append(used_views)
            pred = predict(model, processor, images, prompt) 
            preds.append(pred[0])
        return preds, all_used_views, orders

    def format_data4zooming(self, num_splits=4, description_of_splits = DESC_4_SPLITS):
        pass                                         
                                                            
                                                                                             
           
        if not num_splits == 4:
            grids = f"{self.splits2grid[num_splits][0]}*{self.splits2grid[num_splits][1]}"
            description_of_splits = DESC_ANY_SPLITS.format(grids=grids, num_splits=num_splits)

        images = []
        prompts = []
        for d in self.data:
            img = self.placeholder.format(i=0, placeholder=self.replace_token)
            if num_splits != 4:
                resize_img, parts = test_split_image(Image.open(d['images'][0]), self.splits2grid[self.num_split])
                prompts.append(ZOOM_MANUAL_DECISION_TEMPLATES_ANY.format(image=img, question=d['question'], num_splits=num_splits, description_of_splits=description_of_splits))
            else:
                images.append(Image.open(d['images'][2]))
                prompts.append(ZOOM_MANUAL_DECISION_TEMPLATES.format(image=img, question=d['question'], num_splits=num_splits, description_of_splits=description_of_splits))
        return images, prompts

    def format_data4zooming_qa(self, gen_rsts, data_idx=None, num_splits=4):
        pass                                         
                                                                                             
           
        p = re.compile('\d')
        p_str = re.compile('upperleft|lowerleft|upperright|lowerright|left|right|upper|lower')
        str_mapper = {"left":[1,2], "right":[3,4], "upper":[1,3], "upper":[2,4], "upperleft":[1], "lowerleft":[2], "upperright":[3], "lowerright":[4]}
        images = []
        prompts = []
        select_list = []

        g = gen_rsts
        d = self.data[data_idx]
        zoomed_images = ""
        _select = []
        if isinstance(g, list):
            _select = g
        else:
            for _g in g.split(','):                       
                m = p.match(_g)
                if m:
                    _se = int(_g)
                    _select.append(_se)
                else:
                    m = p_str.match(_g)
                    if m:
                        _se = str_mapper[m.group()]
                        _select.extend(_se)

        if _select:                                  
            _select = sorted(set(_select))
            _images = [Image.open(d['images'][1])]
            for i, _se in enumerate(_select):
                _images.append(Image.open(d['images'][_se+2]))
                zoomed_images += f'<image{i+1}>{self.replace_token} is your selected {self.image_views[_se-1]} view. '
            select_list.append(_select)
            images.extend(_images)
        else:
            select_list.append([])
            images.append(Image.open(d['images'][1]))
        prompts.append(ZOOM_QA_TEMPLATES_BROTE.format(replace_token=self.replace_token, zoomed_images=zoomed_images, question=d['question'],option=option))
        return images, prompts

    def format_data4zooming_qa_any(self, gen_rsts, data_idx=None, num_splits=4):
        p = re.compile('\d')
        images = []
        prompts = []
        select_list = []

        g = gen_rsts
        d = self.data[data_idx]
        zoomed_images = ""
        _select = []
        if isinstance(g, list):
            _select = g
        else:
            for _g in g.split(','):                       
                m = p.match(_g)
                if m:
                    _se = int(_g)
                    _select.append(_se)
                else:
                    m = p_str.match(_g)
                    if m:
                        _se = str_mapper[m.group()]
                        _select.extend(_se)

        resize_img, parts = test_split_image(Image.open(d['images'][0]), self.splits2grid[self.num_split])
        if _select:                                  
            _select = sorted(set(_select))
            _images = [resize_img]
            for i, _se in enumerate(_select):
                _images.append(parts[_se-1])
                zoomed_images += f'<image{i+1}>{self.replace_token} is your selected {self.image_views[_se-1]} view. '
            select_list.append(_select)
            images.extend(_images)
        else:
            select_list.append([])
            images.append(resize_img)

        option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
        prompts.append(ZOOM_QA_TEMPLATES_BROTE.format(replace_token=self.replace_token, zoomed_images=zoomed_images, question=d['question'],option=option))
        return images, prompts


class EvaluatorChat(Evaluator):
    def __init__(self, data_path=None, image_path=None, image_split_path=None, model='GPT', bbox_dir=None, 
            initial_view=3, num_split=4, generation_kwargs=None):
        super().__init__(data_path=data_path, image_path=image_path, image_split_path=image_split_path, 
                model=model, bbox_dir=bbox_dir, initial_view=initial_view, num_split=num_split) 

        self.eval_format_func['mix'] = self.format_data4mix

        if model == 'mplugowl3':
            self.format_flag = "mplugowl3" 
            self.generation_kwargs = generation_kwargs
        elif model.startswith('minicpm'):
            self.format_flag = "minicpm" 
            self.generation_kwargs = generation_kwargs
        elif model == 'qwen2vl':
            self.format_flag = 'qwen2vl'
        elif model == 'llavaonevision':
            self.format_flag = 'ov'
            self.generation_kwargs = generation_kwargs
        else:
            self.format_flag = "gpt" 

    def get_message_list_temp_user(self):
        message_list_temp_user = [
                {
                    "role": "user",
                    "content": ""
                }
            ]
        content_as_list = False

        if self.format_flag == "mplugowl3":
            img_placeholder = "<|image|>" 
        elif self.format_flag == "minicpm":
            img_placeholder = "" 
        elif self.format_flag == "qwen2vl": 
            message_list_temp_user = [
                {
                    "role":"user", 
                    "content":[
                        {"type":"image", "image":""},            
                        {"type":"text", "text":""}]
                }
            ]
            img_placeholder = "" 
            content_as_list = True
        elif self.format_flag == 'ov':
            img_placeholder = self.generation_kwargs['DEFAULT_IMAGE_TOKEN']
            conv_templates = self.generation_kwargs['conv_templates']
            conv_template = self.generation_kwargs['conv_template']
            message_list_temp_user = copy.deepcopy(conv_templates[conv_template])
        else:                       
            message_list_temp_user = [
                {
                    "role":"user", 
                    "content":[
                        {"type":"image"}, 
                        {"type":"text", "text":""}]
                }
            ]
            img_placeholder = "" 
            content_as_list = True
        return message_list_temp_user, img_placeholder, content_as_list

    def get_response(self, model, processor, prompt, images, generation_kwargs):
        if self.format_flag == "mplugowl3":
            prompt.append({"role": "assistant", "content": ""}) 
            inputs = processor(prompt, images=images).to('cuda')
            inputs.update({
                'tokenizer': generation_kwargs['tokenizer'],
                'max_new_tokens': 200,
                'decode_text':True,
                'temperature': 0.})
            return model.generate(**inputs)
        elif self.model_name == 'qwen2vl':
            torch.cuda.empty_cache()
            text = processor.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = generation_kwargs['process_vision_info'](prompt)
            inputs = processor(text=[text],
                images=image_inputs, videos=video_inputs,
                padding=True, return_tensors="pt",
                ).to('cuda').to(model.dtype)

            try:
                response = model.generate(**inputs, max_new_tokens=200)
                generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, response)]
                response = processor.batch_decode(
                    generated_ids_trimmed, 
                    skip_special_tokens=True, 
                    clean_up_tokenization_spaces=False)
            except:
                response = 'Z'
            torch.cuda.empty_cache()
            return response
        elif self.model_name == 'minicpmv2.6':
            response = model.chat(image=None, msgs=prompt, 
                    tokenizer=generation_kwargs['tokenizer'],
                    temperature=0., sampling=False, max_new_tokens=200)  
            return [response]
        elif self.model_name == 'llavaonevision':
            if not isinstance(images, list):
                images = [images]
            image_tensor = generation_kwargs['process_images'](images, generation_kwargs['image_processor'], model.config)
            image_tensor = [_image.to(dtype=torch.float16, device='cuda') for _image in image_tensor]
            input_ids = generation_kwargs['tokenizer_image_token'](prompt, generation_kwargs['tokenizer'], generation_kwargs['IMAGE_TOKEN_INDEX'], return_tensors="pt").unsqueeze(0).to('cuda')
            image_sizes = [image.size for image in images]
            try:
                cont = model.generate(
                    input_ids,
                    images=image_tensor,
                    image_sizes=image_sizes,
                    do_sample=False,
                    temperature=0,
                    max_new_tokens=200)
                response = generation_kwargs['tokenizer'].batch_decode(cont, skip_special_tokens=True)
            except:
                response = 'Z'
                print('OOM')
            return response
        else:
            prompts = processor.apply_chat_template(prompt, add_generation_prompt=True)
            inputs = processor(text=prompts, images=images, return_tensors="pt")
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            if self.model_name == 'idefics3':
                                            
                generated_ids = model.generate(**inputs, max_new_tokens=200)
                return [r.split('\nAssistant: ')[1] for r in processor.batch_decode(generated_ids, skip_special_tokens=True)]
            else:
                generation_kwargs['max_new_tokens'] = 200
                generated_ids = model.generate(**inputs, **generation_kwargs)
                return processor.batch_decode(generated_ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    def format_data4full(self):
                                   
        for d in self.data:
            img_path = d['images'][1]
            images = [load_image(d['images'][1])]
            
            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            prompts, img_placeholder, content_as_list = self.get_message_list_temp_user()
            if content_as_list:
                prompts[0]['content'][1]['text'] = QA_TEMPLATES_CHAT.format(image='image 1', question=d['question'], option=option)
                if self.format_flag == "qwen2vl":
                    prompts[0]['content'][0]['image'] = img_path
            else:
                if img_placeholder == "":
                    img_placeholder = "image 1"

                if self.model_name == 'minicpmv2.6':
                    content = images
                    content.append(QA_TEMPLATES_CHAT.format(image=img_placeholder, question=d['question'], option=option))
                    prompts[0]['content'] = content
                elif self.format_flag == 'ov':
                    question = QA_TEMPLATES_CHAT.format(image=img_placeholder, question=d['question'], option=option)
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()
                else:
                    prompts[0]['content'] = QA_TEMPLATES_CHAT.format(image=img_placeholder, question=d['question'], option=option)
            yield images, prompts

    def format_data4mix(self, model=None, processor=None, generation_kwargs=None, description_of_splits = DESC_4_SPLITS, num_splits=4):
        pass                                    
                                                                              
           
        if model is None: 
            print('please provide a model for prediction')
            return []

        preds = []
        all_used_views = []
        history = []
        for idx, d in tqdm(enumerate(self.data)):
            images = [load_image(d['images'][2])]
            images_path = [d['images'][2]]
            img_str = "" 
            used_views = []
            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            cur_actions = []

                              
            prompts, img_placeholder, content_as_list = self.get_message_list_temp_user()
            if img_placeholder == "": img_placeholder = 'Image 1'

            if content_as_list:
                prompts[0]['content'][1]['text'] = MIX_INIT_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])
                if self.format_flag == "qwen2vl":
                    prompts[0]['content'][0]['image'] = images_path[0]
            else:
                if self.format_flag != 'ov':
                    prompts[0]['content'] = MIX_INIT_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])

                if self.model_name == 'minicpmv2.6':
                    content = images[:]
                    content.append(prompts[0]['content'])
                    prompts[0]['content'] = content
                elif self.format_flag == 'ov':
                    question = MIX_INIT_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()

            generation = self.get_response(model, processor, prompts, images, generation_kwargs)[0]

            if self.model_name == 'minicpmv2.6':
                generation = generation.replace('{\n{', '{')
            elif self.model_name == 'idefics3':
                generation = generation.replace("'",'"')

            try:
                j = json.loads(generation)
            except:
                j = {'part': "none", 'reason': "none"}

            if not 'part' in j:
                j['part'] = "none"
            else:
                if j['part'] != "none":
                    try:
                        init_views = [int(_idx) for _idx in j['part'].split(',') if 0 < int(_idx) < 5]
                    except:
                        j['part'] = "none"

            if j['part'] == 'none':                                             
                all_used_views.append(used_views)
                pred = self._mix_qa(img_placeholder, d, option, images_path, images, model, processor, generation_kwargs)
                preds.append(pred[0])
                print('Answer:', pred[0])
                cur_actions.append({"init": generation, "rst": None, "answer": pred[0]})
                history.append(cur_actions)
                continue
            else:
                used_views.append(init_views)
                cur_actions.append({"init": generation, "rst":used_views[-1]})

                                   
            prompts, img_placeholder, _ = self.get_message_list_temp_user()
            _images, _images_path = images[:], images_path[:]
            zoomed_images = ""
            for i in range(len(used_views[-1])):
                _se = used_views[-1][i]
                _images.append(load_image(d['images'][_se+2]))
                _images_path.append(d['images'][_se+2])

                if content_as_list:
                        prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']

                view = self.image_views[_se-1] 
                if img_placeholder == '':
                    zoomed_images += f" image {i+2}, the {view} view," 
                else:
                    zoomed_images += f" {img_placeholder}, the {view} view," 

            if img_placeholder == '': img_placeholder = 'Image 1'

            if content_as_list:
                prompts[0]['content'][-1]['text'] = MIX_INTER_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'], option=option, zoomed_images=zoomed_images)
                if len(_images)>len(prompts[0]['content'])-1:
                    prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']
                if self.model_name == 'qwen2vl':
                    for _i, img_path in enumerate(_images_path):
                        prompts[0]['content'][_i]['image'] = img_path
            else:
                if self.model_name == 'minicpmv2.6':
                    content = _images[:]
                    content.append(MIX_INTER_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'], option=option, zoomed_images=zoomed_images))
                    prompts[0]['content'] = content
                elif self.format_flag == 'ov':
                    question = MIX_INTER_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'], option=option, zoomed_images=zoomed_images)
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()
                else:
                    prompts[0]['content'] = MIX_INTER_DECISION_TEMPLATE.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'], option=option, zoomed_images=zoomed_images)

            generation = self.get_response(model, processor, prompts, _images, generation_kwargs)[0]
            if self.model_name == 'minicpmv2.6':
                generation = generation.replace('{\n{', '{')
                if "the answer is:" in generation:
                    generation = generation.split('the answer is:', 1)[1].strip()
            elif self.model_name == 'idefics3':
                generation = generation.replace("'",'"')

            try:
                j = json.loads(generation)
                if j['keep'] == 'none' and j['shift'] == 'none':
                    used_views.append([])
                elif j['keep'] == 'none':
                    shift = [int(_idx) for _idx in j['shift'].split(',') if not int(_idx) in used_views[-1] and 0 < int(_idx) < 5]
                    used_views.append(shift)
                elif j['shift'] == 'none':
                    keep = [int(_idx) for _idx in j['keep'].split(',') if int(_idx) in used_views[-1] and 0 < int(_idx) < 5]
                    used_views.append(keep)
                else:
                    shift = [int(_idx) for _idx in j['shift'].split(',') if not int(_idx) in used_views[-1] and 0 < int(_idx) < 5]
                    keep = [int(_idx) for _idx in j['keep'].split(',') if int(_idx) in used_views[-1] and 0 < int(_idx) < 5]
                    new_views = list(set(shift+keep))
                    used_views.append(new_views)
                cur_actions.append({"inter": generation, "rst":used_views[-1]})
            except:
                cur_actions.append({"inter": generation, "rst": None})

                      
            all_used_views.append(used_views)
            _, img_placeholder, _ = self.get_message_list_temp_user()
            if img_placeholder == "":
                zoomed_images = "Image 1 is the full image,"
            else:
                zoomed_images = f"{img_placeholder} is the full image,"

            _images, _images_path = images[:], images_path[:]
            for i in range(len(used_views[-1])):
                _se = used_views[-1][i]
                _images.append(load_image(d['images'][_se+2]))
                _images_path.append(d['images'][_se+2])

                view = self.image_views[_se-1] 
                if img_placeholder == '':
                    zoomed_images += f" image {i+2}, the {view} view," 
                else:
                    zoomed_images += f" {img_placeholder}, the {view} view," 

            pred = self._mix_qa(zoomed_images, d, option, _images_path, _images, model, processor, generation_kwargs)
            preds.append(pred[0])
            print('Answer:', pred[0])
            cur_actions[-1]['answer'] = pred[0]
            history.append(cur_actions)
        return preds, all_used_views, history

    def _mix_qa(self, img_str, d, option, images_path, images, model, processor, generation_kwargs):
        prompts, _, content_as_list = self.get_message_list_temp_user()
        if content_as_list:
            prompts[0]['content'][1]['text'] = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)

            while len(images)>len(prompts[0]['content'])-1:
                prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']

            if self.model_name == 'qwen2vl':
                for _i, img_path in enumerate(images_path):
                    prompts[0]['content'][_i]['image'] = img_path

        else:
            if self.format_flag != 'ov':
                prompts[0]['content'] = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)

            if self.model_name == 'minicpmv2.6':
                content = images[:]
                content.append(QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option))
                prompts[0]['content'] = content
            elif self.format_flag == 'ov':
                question = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)
                prompts.append_message(prompts.roles[0], question)
                prompts.append_message(prompts.roles[1], None)
                prompts = prompts.get_prompt()
            else:
                prompts[0]['content'] = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)

        pred = self.get_response(model, processor, prompts, images, generation_kwargs)
        return pred 


    def format_data4shifting(self, model=None, initial_only=False, pre_define_initial=[], processor=None, generation_kwargs=None):
        pass                                    
                                                                              
           
        if model is None: 
            print('please provide a model for prediction')
            return []

        preds = []
        all_used_views = []
        orders = []
        for idx, d in tqdm(enumerate(self.data)):
            if pre_define_initial:
                start_index = pre_define_initial[idx]
            else:
                if self.num_split ==4:
                    start_index = random.randint(0, 3)                               
                else:
                    start_index = random.randint(0, self.num_split-1)                               
            orders.append(start_index)
            images = []
            images_path = []
            prompts, img_placeholder, content_as_list = self.get_message_list_temp_user()
            img_str = "" 
            i = 0
            used_views = []
            if initial_only:
                used_views.append(start_index)
                images.append(load_image(d['images'][start_index+3]))
                images_path.append(d['images'][start_index+3])
                img_str += f"{'image 1' if img_placeholder == '' else img_placeholder}, the {self.image_views[start_index]} view." 
            else:
                if self.num_split ==4:
                    view_order = self.image_views[start_index:] + self.image_views[:start_index]                                                                               
                else:
                    _order = list(range(1, self.num_split+1))
                    order_str = f"{self.splits2grid[self.num_split][0]}*{self.splits2grid[self.num_split][1]} grids"
                    view_order = _order[start_index:] + _order[:start_index] 
                    _, parts = test_split_image(Image.open(d['images'][0]), self.splits2grid[self.num_split])
        
                while view_order:
                    view = view_order.pop(0)
                    if self.num_split ==4:
                        view_idx = self.image_views.index(view)
                        images.append(load_image(d['images'][view_idx+3]))
                        images_path.append(d['images'][view_idx+3])
                    else:                                          
                        view_idx = view-1
                        view = f'no. {view}'
                        images.append(parts[view_idx])
                        images_path.append("")                
                    used_views.append(view_idx)
    
                    if img_placeholder == '':
                        img_str += f" image {i+1}, the {view} view," 
                    else:
                        img_str += f" {img_placeholder}, the {view} view," 

                    if content_as_list:
                        prompts[0]['content'][-1]['text'] = SHIFT_DECISION_TEMPLATES_CHAT.format(images=img_str, question=d['question'])
                        if len(images)>len(prompts[0]['content'])-1:
                            prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']
                        if self.model_name == 'qwen2vl':
                            for _i, img_path in enumerate(images_path):
                                prompts[0]['content'][_i]['image'] = img_path
                    else:
                        if self.model_name == 'minicpmv2.6':
                            content = images[:]
                            content.append(SHIFT_DECISION_TEMPLATES_CHAT.format(images=img_str, question=d['question']))
                            prompts[0]['content'] = content
                        elif self.format_flag == 'ov':
                            question = SHIFT_DECISION_TEMPLATES_CHAT.format(images=img_str, question=d['question'])
                            prompts, _, _ = self.get_message_list_temp_user()
                            prompts.append_message(prompts.roles[0], question)
                            prompts.append_message(prompts.roles[1], None)
                            prompts = prompts.get_prompt()
                        else:
                            prompts[0]['content'] = SHIFT_DECISION_TEMPLATES_CHAT.format(images=img_str, question=d['question'])

                    torch.cuda.empty_cache()
                    generation = self.get_response(model, processor, prompts, images, generation_kwargs)
                    if self.model_name == 'minicpmv2.6':
                                                         
                        generation = [generation[0].split(',')[0]]

                                                       
                    if generation[0].lower() == 'no':
                        break
                    i += 1

            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            prompts, _, _ = self.get_message_list_temp_user()
            if content_as_list:
                prompts[0]['content'][1]['text'] = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)
                while len(images)>len(prompts[0]['content'])-1:
                    prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']

                if self.model_name == 'qwen2vl':
                    for _i, img_path in enumerate(images_path):
                        prompts[0]['content'][_i]['image'] = img_path
            else:
                if self.model_name == 'minicpmv2.6':
                    content = images[:]
                    content.append(QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option))
                    prompts[0]['content'] = content
                elif self.format_flag == 'ov':
                    question = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()
                else:
                    prompts[0]['content'] = QA_TEMPLATES_CHAT.format(image=img_str, question=d['question'], option=option)

            pred = self.get_response(model, processor, prompts, images, generation_kwargs)

            all_used_views.append(used_views)
            preds.append(pred[0])
        return preds, all_used_views, orders

    def format_data4zooming(self, num_splits=4, description_of_splits = DESC_4_SPLITS):
        pass                                         
                                                            
                                                                                             
           
        for d in self.data:
            images = load_image(d['images'][2])
            img_path = d['images'][2]
            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            prompts, img_placeholder, content_as_list = self.get_message_list_temp_user()
            if img_placeholder == "":
                img_placeholder = 'Image 1'

            if content_as_list:
                prompts[0]['content'][1]['text'] = ZOOM_MANUAL_DECISION_TEMPLATES_CHAT.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])
                if self.format_flag == "qwen2vl":
                    prompts[0]['content'][0]['image'] = img_path

                if self.model_name == 'idefics3':
                    yield [images], prompts
                else:
                    yield images, prompts
            else:
                if self.format_flag != 'ov':
                    prompts[0]['content'] = ZOOM_MANUAL_DECISION_TEMPLATES_CHAT.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])

                if self.model_name == 'minicpmv2.6':
                    content = [images]
                    content.append(prompts[0]['content'])
                    prompts[0]['content'] = content
                    yield [], prompts
                elif self.format_flag == 'ov':
                    question = ZOOM_MANUAL_DECISION_TEMPLATES_CHAT.format(image=img_placeholder, num_splits=num_splits, description_of_splits=description_of_splits, question=d['question'])
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()
                    yield [images], prompts
                else:
                    yield [images], prompts

    def format_data4zooming_qa(self, gen_rsts):
        pass                                         
                                                                                             
           
        p = re.compile('\d')
        p_str = re.compile('upperleft|lowerleft|upperright|lowerright|left|right|upper|lower')
        str_mapper = {"left":[1,2], "right":[3,4], "upper":[1,3], "upper":[2,4], "upperleft":[1], "lowerleft":[2], "upperright":[3], "lowerright":[4]}
        select_list = []
        for d, g in zip(self.data, gen_rsts):
            zoomed_images = ""
            _select = []
            images = []
            images_path = []
            prompts, img_placeholder, content_as_list = self.get_message_list_temp_user()
            if isinstance(g, list):
                _select = g
            else:
                if '.' in g:
                    g = g.replace('.', ',')                          
                for _g in g.split(','):                       
                    if _g == '': continue
                    m = p.match(_g)
                    if m:
                        _se = int(_g)
                        _select.append(_se)
                    else:
                        m = p_str.match(_g)
                        if m:
                            _se = str_mapper[m.group()]
                            _select.extend(_se)

            if _select:                                  
                _select = sorted(set(_select))
                _images = [load_image(d['images'][1])]
                _images_path = [d['images'][1]]
                for i, _se in enumerate(_select):
                    _images.append(load_image(d['images'][_se+2]))
                    _images_path.append(d['images'][_se+2])
                    if content_as_list:
                        prompts[0]['content'] = [{"type":"image"}] + prompts[0]['content']
                    
                    if img_placeholder == "":
                        zoomed_images += f'<image{i+2}> is your selected {self.image_views[_se-1]} view. '
                    else:
                        zoomed_images += f'<|image|> is your selected {self.image_views[_se-1]} view. '
                select_list.append(_select)
                images.extend(_images)
                images_path.extend(_images_path)
            else:
                select_list.append([])
                images.append(load_image(d['images'][1]))
                images_path.append(d['images'][1])

            option = '; '.join([chr(ord('A') + i)+f'. {op}'  for i, op in enumerate(d['options'])])
            if content_as_list:
                prompts[0]['content'][-1]['text'] = ZOOM_QA_TEMPLATES_CHAT.format(image='Image 1', zoomed_images=zoomed_images, question=d['question'],option=option)
                if self.model_name == 'qwen2vl':
                    for _i, img_path in enumerate(images_path):
                        prompts[0]['content'][_i]['image'] = img_path
            else:
                if img_placeholder == '':
                    img_placeholder = 'Image 1'
                if self.model_name == 'minicpmv2.6':
                    content = images
                    content.append(ZOOM_QA_TEMPLATES_CHAT.format(image=img_placeholder, zoomed_images=zoomed_images, question=d['question'],option=option))
                    prompts[0]['content'] = content
                elif self.format_flag == 'ov':
                    question = ZOOM_QA_TEMPLATES_CHAT.format(image=img_placeholder, zoomed_images=zoomed_images, question=d['question'],option=option)
                    prompts.append_message(prompts.roles[0], question)
                    prompts.append_message(prompts.roles[1], None)
                    prompts = prompts.get_prompt()
                else:
                    prompts[0]['content'] = ZOOM_QA_TEMPLATES_CHAT.format(image=img_placeholder, zoomed_images=zoomed_images, question=d['question'],option=option)

            yield images, prompts 


class EvaluatorSingle:
    def __init__(self, data_path=None, image_path=None, image_split_path=None, model='llava', bbox_dir=None, initial_view=3, num_split=4):
        super().__init__(data_path=data_path, image_path=image_path, image_split_path=image_split_path, 
                model=model, bbox_dir=bbox_dir, initial_view=initial_view, num_split=num_split) 
