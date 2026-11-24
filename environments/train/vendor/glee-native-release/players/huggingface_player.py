                                                                                
                                                                     
   

from players.base_player import Player
from utils.conversation import Conversation
import os


class HuggingFacePlayer(Player):
    pass                                                       

                    
                                                        

                    
                                                         
                                                                 
                                                            
                                                                            
                                                                        
                                                        
                                                    
                                                      
                                                                                           
       

    def __init__(self, public_name, delta=1, player_id=0, **kwargs):
        super().__init__(public_name, delta, player_id)

        assert 'model_name' in kwargs, 'model_name must be provided'

        self.model_name = kwargs['model_name']
        self.device = kwargs.get('device', 'auto')
        self.max_new_tokens = kwargs.get('max_new_tokens', 512)
        self.quantization = kwargs.get('quantization', None)
        self.torch_dtype_str = kwargs.get('torch_dtype', 'float16')
        self.trust_remote_code = kwargs.get('trust_remote_code', False)
        self.temperature = kwargs.get('temperature', 0.7)
        self.do_sample = kwargs.get('do_sample', True)
        self.top_p = kwargs.get('top_p', 0.9)
        self.load_hf_model = kwargs.get('load_hf_model', True)

                                 
        self.conv = Conversation("huggingface", roles=("user", "assistant"))
        self.user_name = "user"

                                                       
        self.model = None
        self.tokenizer = None

        if self.load_hf_model:
            self._load_model()

    def _load_model(self):
        pass                                           
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"Loading model: {self.model_name}")

                               
        dtype_map = {
            'float16': torch.float16,
            'bfloat16': torch.bfloat16,
            'float32': torch.float32,
        }
        torch_dtype = dtype_map.get(self.torch_dtype_str, torch.float16)

                        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=self.trust_remote_code
        )

                                  
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

                                      
        model_kwargs = {
            'trust_remote_code': self.trust_remote_code,
            'torch_dtype': torch_dtype,
        }

                               
        if self.device == 'auto':
            model_kwargs['device_map'] = 'auto'
        elif self.device == 'cpu':
            model_kwargs['device_map'] = 'cpu'
        else:
            model_kwargs['device_map'] = self.device

                                
        if self.quantization in ('4bit', '8bit'):
            try:
                from transformers import BitsAndBytesConfig

                if self.quantization == '4bit':
                    model_kwargs['quantization_config'] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch_dtype,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                else:        
                    model_kwargs['quantization_config'] = BitsAndBytesConfig(
                        load_in_8bit=True
                    )
                print(f"Using {self.quantization} quantization")
            except ImportError:
                print("Warning: bitsandbytes not installed. Loading without quantization.")

                    
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            **model_kwargs
        )

        print(f"Model loaded successfully on device: {self.model.device}")

    def add_message(self, message, role='user'):
        pass                                            
        if role == 'system':
            self.conv.system_message = message
        else:
            self.conv.append_message(self.conv.roles[0] if role == 'user' else self.conv.roles[1], message)

    def clean_conv(self):
        pass                                 
        self.conv.messages = []

    def set_system_message(self, message):
        pass                                              
        self.conv.system_message = message

    def _format_messages_for_model(self):
        pass                                                                 
        messages = self.conv.to_openai_api_messages()

                                                           
        if hasattr(self.tokenizer, 'apply_chat_template'):
            try:
                formatted = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                return formatted
            except Exception as e:
                print(f"Warning: Could not apply chat template: {e}")

                                        
        prompt = ""
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt += f"System: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
        prompt += "Assistant:"
        return prompt

    def get_text_answer(self, format_checker, decision=False):
        pass                                     
        import torch

        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded. Set load_hf_model=True or share model from another player.")

        max_retries = 3
        count = 0

        while count < max_retries:
            try:
                                   
                prompt = self._format_messages_for_model()

                          
                inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True)
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

                          
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.max_new_tokens,
                        temperature=self.temperature if self.do_sample else 1.0,
                        do_sample=self.do_sample,
                        top_p=self.top_p if self.do_sample else 1.0,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )

                                            
                input_length = inputs['input_ids'].shape[1]
                generated_tokens = outputs[0][input_length:]
                self.text_response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

                              
                format_result = format_checker(self.text_response)
                if isinstance(format_result, tuple):
                    is_valid, error_msg = format_result
                else:
                    is_valid = format_result
                    error_msg = "Format validation failed"

                if is_valid:
                    print(self.text_response)
                                                            
                    self.conv.append_message(self.conv.roles[1], self.text_response)
                    break
                else:
                    print(f"Format check failed (attempt {count + 1}/{max_retries}): {error_msg}")
                                                              
                    if count < max_retries - 1:
                        self.conv.append_message(self.conv.roles[1], self.text_response)
                        self.conv.append_message(self.conv.roles[0],
                            f"Your response format was invalid: {error_msg}. Please try again with the correct format.")

            except Exception as e:
                print(f"Error during generation (attempt {count + 1}/{max_retries}): {e}")

            count += 1

        return self.text_response
