import logging
from typing import Dict, List

import streamlit as st
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

LOGGER = logging.getLogger(__name__)

avatars: Dict[str, str] = {
    "user": "🤖",
    "assistant": "🧑‍💻",
}


def display_dialog(message_history: List[Dict[str, str]]) -> None:
    pass                                                                      
                                                                

              
              
                                                       
                         
                             
                                               
                                                                                                             
                                                                                         
                                                                                                      
                                                                
                             
                         

           
           
       
    for i in range(len(message_history)):
        with st.chat_message(
            message_history[i]["role"], avatar=avatars[message_history[i]["role"]]
        ):
            st.write(f"{message_history[i]['content']}")
        if i == len(message_history) - 2:
            with st.expander("ChatGPT would've asked"):
                with st.chat_message(
                    message_history[i]["role"],
                    avatar="🦾",
                ):
                    st.write(st.session_state["alternative_question"])


def boolean_string(s):
    if s.lower() not in {"false", "true"}:
        raise ValueError("Not a valid boolean string")
    return s.lower() == "true"


def load_model(path):
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=False)
    print("Tokenizer loaded.")
    model = AutoModelForCausalLM.from_pretrained(
        path, low_cpu_mem_usage=True, torch_dtype=torch.float16
    ).cuda()
    print("Model loaded.")
                         
    return model, tokenizer
