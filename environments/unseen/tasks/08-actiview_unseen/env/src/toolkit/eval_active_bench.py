import sys, os
import json, re, argparse
import random
random.seed(1234)

from PIL import Image
import torch
from tqdm import tqdm

from evaluator import Evaluator, EvaluatorChat, EvaluatorSingle
from model_config import model_mapper, load_model, predict, predict_chat, chat_set
from image_utils import pil_image_to_base64

import warnings

def load_evaluator(args):
                          
    if args.save_results:
        if not os.path.exists(args.result_dir):
            os.mkdir(args.result_dir)

        result_dir = f'{args.result_dir}/{args.model_name}'
        if args.num_split != 4:
            result_dir += f'_split{args.num_split}'
        os.makedirs(result_dir, exist_ok=True)
    else:
        result_dir = ""

                    
    if 'brote' in args.model_name.lower() or 'mmicl' in args.model_name.lower():
        model, processor, replace_token = load_model(args.model_path, args.model_scale, args.processor_path, model_name=args.model_name)
        evaluator = Evaluator(data_path=args.eval_data,
                image_path=args.eval_image, 
                image_split_path=args.eval_image_split, 
                bbox_dir=args.eval_image_bbox, 
                num_split=args.num_split)
        return evaluator, model, processor, replace_token, result_dir

    elif 'gpt' in args.model_name.lower() or 'gemini' in args.model_name.lower() or 'idefics' in args.model_name.lower() or args.model_name.lower() in chat_set:
        model, processor, generation_kwargs = load_model(args.model_path, args.model_scale, args.processor_path, model_name=args.model_name)
        evaluator = EvaluatorChat(data_path=args.eval_data, 
                image_path=args.eval_image, 
                image_split_path=args.eval_image_split, 
                bbox_dir=args.eval_image_bbox, 
                num_split=args.num_split, 
                model=args.model_name.lower(), 
                generation_kwargs=generation_kwargs)

        return evaluator, model, processor, generation_kwargs, result_dir

    else:                     
        raise NotImplementedError()


def run_eval(evaluator, model, processor, generation_kwargs, result_dir, args, save_name):
    if args.eval_type == 'shifting':
                                                                       
        if args.pre_define_view is not None:                                        
            print('pre_define_initial: ', args.pre_define_view)
            with open(os.path.join(args.eval_data, 'shifting_level.json')) as fr:
                level = json.loads(fr.read())[args.pre_define_view]
            save_name = f'{args.pre_define_view}_{args.model_scale}_{args.eval_type}.json'
        else:
            if args.initial_only:
                save_name = f'initial_{args.model_scale}_{args.eval_type}.json'
            level = []

        pred, all_used_views, orders = evaluator.eval_format_func[args.eval_type](model=model, initial_only=args.initial_only, pre_define_initial=level, generation_kwargs=generation_kwargs, processor=processor)
                                    
                                
                                          

    elif args.eval_type == 'mix': 
        pred, all_used_views, history = evaluator.eval_format_func[args.eval_type](model=model, generation_kwargs=generation_kwargs, processor=processor)
                                
                                          

    else:                
        if args.eval_type == 'full':
            save_name = f'resize_{args.model_scale}_{args.eval_type}.json'
        elif args.eval_type == 'zooming':
            save_name = f'gt_{args.model_scale}_{args.eval_type}.json' if args.use_gt else f'selection_{args.model_scale}_{args.eval_type}.json'

        if args.input_type == 'chat': 
            if args.eval_type == 'zooming':
                                            
                if args.use_gt:
                    print('using gt')
                    with open(os.path.join(args.eval_data, 'groundtruth_views.json')) as fr:
                        generated_text = json.loads(fr.read())
                else:
                    generated_text = predict_chat(model, processor, evaluator, args.eval_type, generation_kwargs, model_name=args.model_name)
                                                
                                                       
                                         
                pred = predict_chat(model, processor, evaluator, 'zoomingQA', generation_kwargs, zooming_select=generated_text, model_name=args.model_name)
            else:
                pred = predict_chat(model, processor, evaluator, args.eval_type, generation_kwargs, model_name=args.model_name)
        else:
            images, prompts = evaluator.eval_format_func[args.eval_type]()
            if args.eval_type == 'zooming' and args.use_gt:
                print('using gt')
                with open(os.path.join(args.eval_data, 'groundtruth_views.json')) as fr:
                    generated_text = json.loads(fr.read())
            else:
                generated_text = []
                for img, pr in zip(images, prompts):
                    _gen = predict(model, [img], [pr], model_name=self.model_name)
                    generated_text.append(_gen[0])

            if args.eval_type == 'zooming':
                if not args.use_gt and result_dir != '': 
                                                             
                    with open(f'{result_dir}/{save_name}', 'w') as fw:
                        fw.write(json.dumps(generated_text))
                    save_name = f'{args.model_scale}_{args.eval_type}.json'

                generated_text_qa = []
                for i, pr in enumerate(generated_text):
                    if args.num_split != 4:
                        images_qa, prompts_qa = evaluator.format_data4zooming_qa_any(pr, data_idx=i, num_splits=args.num_split)
                    else:
                        images_qa, prompts_qa = evaluator.format_data4zooming_qa(pr, data_idx=i)
                    _pred = predict(model, images_qa, prompts_qa, model_name=self.model_name)
                    generated_text_qa.append(_pred[0])
                pred = generated_text_qa
            else:
                pred = generated_text

    acc = evaluator.cal_acc(pred)

    print(pred)
                             
    print('==================')
    print(f'{args.model_name}, {args.model_scale}\nsplit: {args.num_split}')
    if args.eval_type == 'shifting':
        print(f'eval acc for type shifting, initial_only={args.initial_only}, pre-defined views: {args.pre_define_view}')
    else:
        print(f'eval acc for type {args.eval_type}:')
    print(acc)
    print('\n\n')

    if result_dir != '':
        print('finish evaluating, saving results...')
        with open(f'{result_dir}/{save_name}', 'w') as fw:
            save_dict = {'preds': pred, 'acc':acc}
            fw.write(json.dumps(save_dict))
        if args.eval_type == 'mix':
            with open(f'{result_dir}/action_history_{save_name}', 'w') as fw:
                fw.write(json.dumps(history, indent=4))
        print('done\n')


def load_args():
    parser = argparse.ArgumentParser(description='args for ActiView evaluation')
    parser.add_argument('--model_path', type=str, default=None, help='The local path to the model to be evaluated, or the name in hugging face model hub. If model path is not provided, will pick up the path of model_name in model_mapper in the model_config.py script.')
    parser.add_argument('--input_type', type=str, default='multi', help='Please choose from: multi, chat, single. "multi": for multi-image model such as MMICL and Brote; "chat": for models that accept input in chat format (of user and assistant roles); "single": for single-image models such llava.')
    parser.add_argument('--model_name', type=str, default='qwen2vl', help='Please specify the name of model to be evaluated. This arg will be used for saving results and selecting the class of evaluator. If it is not manually specified, we will use the name "qwen2vl" with the evaluator class EvaluatorChat by default.')
    parser.add_argument('--initial_only', action="store_true", help='Whether to evaluate with the initial view only. This is employed as the baseline of the shifting type, which addresses the importance of multi-image input.')
    parser.add_argument('--use_gt', action="store_true", help='Whether to evaluate the performance given views containing human annotated clues.')
    parser.add_argument('--processor_path', type=str, required=False, help='Some models might require path to their processor when initializing and for input processing, please specify here.')
    parser.add_argument('--eval_data', type=str, required=True, help='Path to data.json file.')
    parser.add_argument('--eval_image', type=str, required=False, help='Path of image dir, by default, it is placed under eval_data dir. You can alse place it elsewhere and specify here.')
    parser.add_argument('--model_scale', type=str, default='xl', help='Different model scale, if applicable')
    parser.add_argument('--num_split', type=int, default=4, help='The number of view splits. By default, it is 4. We also support other splits such as 6,8,9,16.')
    parser.add_argument('--eval_image_split', type=str, required=False, help='path of dir of image splits')
    parser.add_argument('--eval_image_bbox', type=str, required=False, help='path to bbox')
    parser.add_argument('--eval_type', type=str, default='full', help='Choose from: shifting, zooming, mix, full. Note that full is for general VQA results, while shifting, zooming, and mix are for acitve perception.')
    parser.add_argument('--pre_define_view', type=str, default=None, help='Predefined difficulty for shifting: hard, medium, easy')
    parser.add_argument('--result_dir', type=str, default='../results')
    parser.add_argument('--save_results', action="store_true", help='whether to save model generated results. If false, will directly print acc')
    args = parser.parse_args()

    if 'gpt' in args.model_name.lower() or 'gemini' in args.model_name.lower() or 'idefics' in args.model_name.lower() or args.model_name.lower() in chat_set:
        args.input_type = 'chat'

    return args

if __name__ == '__main__':
    args = load_args()
    
    save_name = f'{args.eval_type}.json'
    print('eval_type: ', args.eval_type)
        
    evaluator, model, processor, generation_kwargs, result_dir = load_evaluator(args)
    run_eval(evaluator, model, processor, generation_kwargs, result_dir, args, save_name)

