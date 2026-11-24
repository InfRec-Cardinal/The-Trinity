import sys, os
import torch
import transformers
from transformers import AutoTokenizer, AutoModel
from pathlib import Path

                                 
"""
Configuration of model path
"""
model_mapper = {'idefics': 'path_to_your_model',
            'idefics3': 'path_to_your_model',
            'llavanext': 'path_to_your_model',
            'llavaonevision': 'path_to_your_model',
            'mantis': 'path_to_your_model',
            'minicpmv2.5':'path_to_your_model',
            'minicpmv2.6':'path_to_your_model',
            'mplugowl3': 'path_to_your_model',
            'mplugowl2': 'path_to_your_model',
            'qwen2vl': 'path_to_your_model',
            'slime8b': 'path_to_your_model'}

chat_set = {"gpt", "gemini", "idefics", "mantis", "llavaonevision", "minicpmv2.6", "mplugowl3", "qwen2vl"}

                                 
"""
load your model here
"""

def load_model(model_path, model_scale, processpor_path, model_name='Brote'):
                        
                      
                        
    if model_name.lower() in model_mapper or model_path is not None:
        tokenizer, processor, generation_kwargs = None, None, None
        model_name = model_name.lower()
        if model_path is None:
            model_path = model_mapper[model_name]

        if model_name == 'mplugowl2':
            raise NotImplementedError()

        elif model_name == 'mplugowl3':
            sys.path.append("/yeesuanAI05/thumt/dyr/mplug_owl3")
            from mplug_owl3.modeling_mplugowl3 import mPLUGOwl3Model

            model = mPLUGOwl3Model.from_pretrained(model_path, attn_implementation='sdpa', torch_dtype=torch.half).cuda()
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            processor = model.init_processor(tokenizer)
            generation_kwargs = {'tokenizer': tokenizer}

        elif model_name == 'minicpmv2.6':
            sys.path.append(model_path)
            from transformers import AutoModel, AutoTokenizer

            torch.manual_seed(0)
            model = AutoModel.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.bfloat16).to('cuda')
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            generation_kwargs = {'tokenizer': tokenizer}

        elif model_name == 'minicpmv2.5':
            raise NotImplementedError()

        elif model_name == 'qwen2vl':
            from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
            from qwen_vl_utils import process_vision_info

            model = Qwen2VLForConditionalGeneration.from_pretrained(model_path, torch_dtype=torch.bfloat16, device_map="auto")
            processor = AutoProcessor.from_pretrained(model_path, max_pixels = 1040 * 28 * 28, min_pixels = 100 * 28 * 28)
            generation_kwargs = {'process_vision_info': process_vision_info}
            
        elif 'llava' in model_name:                               
            from llava.model.builder import load_pretrained_model
            if 'onevision' in model_name:
                warnings.filterwarnings("ignore")
                from llava.mm_utils import process_images, tokenizer_image_token
                from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
                from llava.conversation import conv_templates
                tokenizer, model, image_processor, max_length = load_pretrained_model(model_path, None, 'llava_qwen', device_map='auto', force_download=False, image_aspect_ratio="anyres")
                generation_kwargs = {
                    'IMAGE_TOKEN_INDEX': IMAGE_TOKEN_INDEX,
                    'DEFAULT_IMAGE_TOKEN': DEFAULT_IMAGE_TOKEN,
                    'conv_templates': conv_templates,
                    'conv_template': "qwen_2",                                                                
                    'tokenizer': tokenizer,
                    'image_processor': image_processor,
                    'process_images': process_images,
                    'tokenizer_image_token': tokenizer_image_token}
            else:
                raise NotImplementedError()

        elif model_name.lower() in ['mantis', 'idefics', 'idefics3']:
            from transformers import AutoProcessor, AutoModelForVision2Seq

            if model_name.startswith('idefics'):
                processor = AutoProcessor.from_pretrained(model_path) 
                                                                                                                
            else:
                print('loading')
                processor = AutoProcessor.from_pretrained(model_path) 
            model = AutoModelForVision2Seq.from_pretrained(model_path, device_map="auto", torch_dtype=torch.bfloat16)
            generation_kwargs = {
                "max_new_tokens": 20,
                "num_beams": 1,
                "do_sample": False}

        elif model_name.lower() in ['brote', 'mmicl']:
            sys.path.append(model_path)
            if not 'MMICL' in  model_path:
                from model.instructblip_icl import InstructBlipConfig, InstructBlipForConditionalGeneration, InstructBlipProcessor
            else:
                from model.instructblip import InstructBlipConfig, InstructBlipModel, InstructBlipPreTrainedModel,InstructBlipForConditionalGeneration,InstructBlipProcessor
            
            config = InstructBlipConfig.from_pretrained(model_path)
            if not 'MMICL' in  model_path:
                config.qformer_config.global_calculation = 'add'
                config.qformer_config.send_condition_to_llm = False
                config.qformer_config.both_condition = False
            
            processor = InstructBlipProcessor.from_pretrained(processor_ckpt)
            model = InstructBlipForConditionalGeneration.from_pretrained(model_ckpt, config=config).to('cuda:0',dtype=torch.bfloat16) 
            
            image_placeholder="图"
            sp = [image_placeholder]+[f"<image{i}>" for i in range(20)]
            sp = sp+processor.tokenizer.additional_special_tokens[len(sp):]
            processor.tokenizer.add_special_tokens({'additional_special_tokens':sp})
            if model.qformer.embeddings.word_embeddings.weight.shape[0] != len(processor.qformer_tokenizer):
                model.qformer.resize_token_embeddings(len(processor.qformer_tokenizer))

        else:
            raise NotImplementedError()
            
        return model.eval(), processor, generation_kwargs


                                
"""
implement the inference method and post processing methods of your model
"""

def predict(model, processor, images, prompt, model_name="GPT", mode=None):
    if model_name=="minicpmv2.5":
        preds = []
        for idx, (image, prompt) in enumerate(zip(images, prompt)):
        
            msgs = [{"role": "user", "content": prompt}]
            inputs = {"image": pil_image_to_base64(image), "question": json.dumps(msgs)}
        
            generated_text = model.chat(inputs, sampling=False)
            preds.append(generated_text)
            
            if mode == "json":
                try:
                    print(f"Select-{idx}: " + json.dumps(json.loads(generated_text)), flush=True)
                except:
                    print(generated_text)
            else:
                print(f"Answer-{idx}: " + generated_text, flush=True)
        return preds
    else:
        inputs = processor(images=images, text=prompt, return_tensors="pt", padding=True)
        
        inputs['pixel_values'] = inputs['pixel_values'].to(torch.bfloat16)
        inputs['img_mask'] = torch.tensor([[1 for i in range(len(images))]])
        inputs['pixel_values'] = inputs['pixel_values'].unsqueeze(0)
        
                            
        inputs = inputs.to('cuda:0')
        
        outputs = model.generate(
                pixel_values = inputs['pixel_values'],
                input_ids = inputs['input_ids'],
                attention_mask = inputs['attention_mask'],
                img_mask = inputs['img_mask'],
                do_sample=False,
                max_length=50,
                min_length=1,
                set_min_padding_size =False,
        )
        
        generated_text = processor.batch_decode(outputs, skip_special_tokens=True)
                              
        return generated_text

def predict_chat(model, processor, evaluator, eval_type, generation_kwargs, zooming_select=None, model_name=''):
    def do_predict(images, messages):
        if model_name == 'minicpmv2.6':
            response = model.chat(image=None, msgs=messages, tokenizer=generation_kwargs['generation_kwargs'],temperature=0., sampling=False, max_new_tokens=20) 
            if 'Answer:' in response:
                response = [response.split('Answer:')[-1].strip()]
            else:
                response = [response]

        elif model_name == 'mplugowl3':
            messages.append({"role": "assistant", "content": ""}) 
            inputs = processor(messages, images=images).to('cuda')
            inputs.update({'tokenizer': generation_kwargs['generation_kwargs'],
                    'max_new_tokens':20,
                    'decode_text':True,
                    'temperature': 0.})
            response = model.generate(**inputs)

        elif model_name == 'qwen2vl':
            image_inputs, video_inputs = process_vision_info(messages)
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            torch.cuda.empty_cache()
            inputs = processor(text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True, return_tensors="pt",).to(model.device).to(model.dtype)

            torch.cuda.empty_cache()
            try:
                response = model.generate(**inputs, max_new_tokens=20)
                generated_ids_trimmed = [out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, response)]
                response = processor.batch_decode(
                    generated_ids_trimmed, 
                    skip_special_tokens=True, 
                    clean_up_tokenization_spaces=False)
            except Exception as e:
                print(e)
                response = ['Z']                                                                         
            torch.cuda.empty_cache()

        elif model_name == 'llavaonevision':
            if not isinstance(images, list):
                images = [images]
            image_tensor = generation_kwargs['process_images'](images, generation_kwargs['image_processor'], model.config)
            image_tensor = [_image.to(dtype=torch.float16, device='cuda') for _image in image_tensor]
            input_ids = tokenizer_image_token(messages, generation_kwargs['tokenizer'], generation_kwargs['IMAGE_TOKEN_INDEX'], return_tensors="pt").unsqueeze(0).to('cuda')
            image_sizes = [image.size for image in images]
            try:
                cont = model.generate(
                    input_ids,
                    images=image_tensor,
                    image_sizes=image_sizes,
                    do_sample=False,
                    temperature=0,
                    max_new_tokens=20)
                response = generation_kwargs['tokenizer'].batch_decode(cont, skip_special_tokens=True)
            except:
                print('OOM')
                response = ['Z']                                                                         
        else:
                                
            prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
            inputs = processor(text=prompt, images=images, return_tensors="pt")
            if model_name == 'idefics':
                inputs = {k: v.to('cuda').to(torch.bfloat16) for k, v in inputs.items()}
            else:                   
                inputs = {k: v.to(model.device) for k, v in inputs.items()}

            if model_name == 'idefics3':
                generated_ids = model.generate(**inputs, max_new_tokens=20)
                response = [r.split('\nAssistant: ')[1] for r in processor.batch_decode(generated_ids, skip_special_tokens=True)]
            else:
                generated_ids = model.generate(**inputs, **generation_kwargs)
                response = processor.batch_decode(generated_ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        return response 

    generated_text = []

    if 'QA' in eval_type:
        for images, messages in tqdm(evaluator.eval_format_func[eval_type](zooming_select)):
            response = do_predict(images, messages)
            generated_text.append(response[0])
    else:
        for images, messages in tqdm(evaluator.eval_format_func[eval_type]()):
            response = do_predict(images, messages)
            generated_text.append(response[0])
        if eval_type == 'zooming':
            print('eval_type', eval_type, '\n',generated_text)
    return generated_text
