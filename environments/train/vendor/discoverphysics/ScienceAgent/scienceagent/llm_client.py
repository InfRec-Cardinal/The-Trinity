                                                                            

                                                
                                                            
                                                                          
                                                                                   
                                                                                   
                                                               
                                                                   
                                                         
                                                                       
                                                        
                                                          
                                                                               
                                                                                                 
                                      
                                                                           
                                                                           
                                                                                    
                                                                                     
                                       
   

import os
import json
import requests
from typing import Optional

                                                                        
                                                                          
                                                                          
                                                                        
HTTP_TIMEOUT_S = 300.0


def complete(
    model: str,
    messages: list[dict],
    system: Optional[str] = None,
    max_tokens: int = 4096,
) -> str:
    pass                                                                         

         
                                                                          
                                                                             
                                                                               
                                                                              
                                                                 
                                                   

            
                                                

                                                                    
                                                                    
                                                                   
                                                      
       
    if _is_anthropic(model):
        return _anthropic_complete(model, messages, system, max_tokens)
    elif model.startswith("openrouter/"):
        return _openrouter_complete(
            model[len("openrouter/") :], messages, system, max_tokens
        )
    elif model.startswith("groq/"):
        return _groq_complete(model[len("groq/") :], messages, system, max_tokens)
    elif model.startswith("azure/"):
        return _azure_complete(model[len("azure/") :], messages, system, max_tokens)
    else:
        return _openai_complete(model, messages, system, max_tokens)


def _is_anthropic(model: str) -> bool:
    return model.startswith("claude")


                    
                    


def _anthropic_complete(model, messages, system, max_tokens):
    try:
        import anthropic
    except ImportError:
        raise ImportError("pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key, timeout=HTTP_TIMEOUT_S)
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text


            
            
def _openrouter_complete(model, messages, system, max_tokens):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY not set")

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": full_messages,
            "max_tokens": max_tokens,
        },
        timeout=HTTP_TIMEOUT_S,
    )
    if not response.ok:
        raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text}")
    body = response.json()
    if "choices" not in body:
        raise RuntimeError(f"OpenRouter unexpected response: {body}")
    message = body["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning") or ""
    return content


      
      
def _groq_complete(model, messages, system, max_tokens):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=HTTP_TIMEOUT_S,
    )

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


               
              
_AZURE_DEPLOYMENTS = {
    "gpt-5.4": "gpt-5.4-samat",
    "gpt-5.4-pro": "gpt-5.4-pro-samat",
    "gpt-5.5": "gpt-5.5",
}


def _azure_complete(model, messages, system, max_tokens):
    try:
        from openai import AzureOpenAI
    except ImportError:
        raise ImportError("pip install openai  (>= 1.0)")

    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("AZURE_OPENAI_API_KEY not set")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise EnvironmentError("AZURE_OPENAI_ENDPOINT not set")

    deployment = _AZURE_DEPLOYMENTS.get(model)
    if not deployment:
        raise ValueError(
            f"Unknown Azure model '{model}'. " f"Available: {list(_AZURE_DEPLOYMENTS)}"
        )

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2025-04-01-preview",
        timeout=HTTP_TIMEOUT_S,
    )

                                             
    kwargs = dict(
        model=deployment,
        input=messages,
        max_output_tokens=max_tokens,
    )
    if system:
        kwargs["instructions"] = system

    response = client.responses.create(**kwargs)
    return response.output_text


                                                  
_OPENAI_COMPAT_PROVIDERS = {
    "ollama/": ("http://localhost:11434/v1", None),                 
    "hf/": ("https://api-inference.huggingface.co/v1", "HF_API_KEY"),
    "together/": ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
    "openai/": (None, "OPENAI_API_KEY"),                       
}


def _resolve_openai_provider(model: str) -> tuple[str, Optional[str], Optional[str]]:
    pass                                                  
    for prefix, (base_url, key_var) in _OPENAI_COMPAT_PROVIDERS.items():
        if model.startswith(prefix):
            resolved = model[len(prefix) :]
            api_key = os.environ.get(key_var) if key_var else "ollama"
            return resolved, base_url, api_key

                                                                                 
                                                         
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    api_key = os.environ.get("OPENAI_API_KEY")
    return model, base_url, api_key


def _openai_complete(model, messages, system, max_tokens):
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai")

    resolved_model, base_url, api_key = _resolve_openai_provider(model)

    client_kwargs = {"timeout": HTTP_TIMEOUT_S}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

                                                               
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=resolved_model,
        messages=full_messages,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
