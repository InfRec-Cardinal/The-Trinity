import re

import pandas as pd
import arviz as az

def construct_dataframe(env):
                                       
    data = env.get_data()

    if env.env_name in ["location_finding"]:
        data= [(x, y, value) for ((x, y), value) in data]
    
                                         
    column_names = env.get_ordered_column_names()
    assert len(column_names) == len(data[0])
    df = pd.DataFrame(data, columns=column_names)
    df.index = [f"True Observation {i}" for i in range(len(df))]
    return df

def construct_features(env, data):

    if env.env_name in ["location_finding"]:
        data= [(arr[0][0], arr[0][1]) for arr in data]

    if env.env_name in ["moral"]:
        group1 = data[0][0]
        group2 = data[0][1]
        data_tuple = []
        intervention = data[0][2]
        row = []
        for attribute in ["count", "gender", "age", "social_status", "fitness", "species"]:
            attribute_diff = env.calculate_attr_diff(group1, group2, attribute)
            row.append(attribute_diff)

        if intervention == 'swerve':
            intervention_encoded = 1
        else:
            intervention_encoded = 0

        data_tuple.append(row + [intervention_encoded])
        data = [row + [intervention_encoded]]

                                         
    column_names = env.get_ordered_column_names()[:-1]
    assert len(column_names) == len(data[0])
    df = pd.DataFrame(data, columns=column_names)
    df.index = [f"True Observation {i}" for i in range(len(df))]
    return df

def pymc_evaluate(trace):
    pass                                                  
       

    loo = az.loo(trace)
    elpd_loo = loo.elpd_loo
    waic = az.waic(trace)
    elpd_waic = waic.elpd_waic
    return {"loo": elpd_loo, 
            "waic": elpd_waic}


def extract_python_code(code_string):

                                                                      
                                                                                            
  extracted_code = re.search(r'```python \n(.*?)```', code_string, re.DOTALL)
                                                                         
  extracted_code = extracted_code.group(1).strip() if extracted_code else "No code found"

  if extracted_code == "No code found":
                                                                                                
      extracted_code = re.search(r'```python\n(.*?)```', code_string, re.DOTALL)
                                                                             
      extracted_code = extracted_code.group(1).strip() if extracted_code else "No code found"

  if extracted_code == "No code found":
      raise Exception("No code found :(")

  return extracted_code 

def extract_python_from_llm(llm_response):
    llm_message = llm_response['choices'][0]['message']['content']
    code = extract_python_code(llm_message)
    return code

def extract_text_within_markers(text, marker):
  pass                                                                                  

                                                          
                                                               
                                                                                                
     
  pattern = rf"{marker}\n([\s\S]*?)\n```"
  matches = re.findall(pattern, text)
  return matches
  

