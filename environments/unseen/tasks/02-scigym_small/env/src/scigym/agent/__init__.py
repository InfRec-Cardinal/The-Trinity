from .claude import Claude
from .gemini import Gemini
from .gpt import GPT


def get_llm(name: str, *args, **kwargs):
    pass                                
       
    if "claude" in name:
        return Claude(model_name=name, *args, **kwargs)
    elif "gemini" in name:
        return Gemini(model_name=name, *args, **kwargs)
    elif "gpt" in name:
        return GPT(model_name=name, *args, **kwargs)
    else:
        raise ValueError(f"Unknown agent name: {name}")
