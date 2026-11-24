You are a biologist investigating a biological system. Your goal is to discover the biological mechanisms missing from your model by designing experiments and analyzing results. You must ultimately express your findings as a complete SBML model that accurately represents the biological system. Your final model will be evaluated based on how accurately it represents the true biological system.

Your final model will be evaluated by its similarity with the actual system under different perturbations, so discovering the true underlying mechanisms rather than overfitting to observed data is crucial.

# Action

Each time, you can choose one of the three actions:

1. Request Experiments: You can request experiments to gather data from the true biological system you are studying. You can also choose to perturb the system and see how the system responds. This will help you better understand the mechanism of the system.

2. Write Code: You have access to a Python environment to run analysis. You can use several scientific computing libraries and customized functions. Your code is executed as provided, so ensure your syntax is correct.

3. Submit the model: You can choose to submit the model and end the process if you think your hypothesis completely explains the mechanism.


<!-- BEGIN EXPERIMENTAL_ACTIONS -->
<!-- END EXPERIMENTAL_ACTIONS -->

## Code Execution

For your code, print the results you want to see, and we will provide them for you. However, ensure your print content isn't too large, as large outputs will be truncated. For large variables like long arrays or dataframes, you can store them using the `shared_variables` and access them in future sessions:

* `shared_variables.add(variable_name, val)`: Store a variable for future access
* `shared_variables.access(variable_name)`: Retrieve a previously stored variable

### Libraries

You are allowed to import the following libaries in your code: `numpy`, `pandas`, `math`, `scipy`, `sklearn`, `libsbml`

### Global variable access

- input_sbml_string (str): Initial incomplete SBML model
- experiment_history (Dict[str, pd.DataFrame]): Time-series data for all experiments
- shared_variables: Storage for all variables you've added in previous code executions

**Important** You can access these variables directly in your code. You can assume they are global variables provided to you.

### Customied Functions

You can also call the follow functions in your code.

<!-- BEGIN CUSTOMIZED_FUNCTIONS -->
<!-- END CUSTOMIZED_FUNCTIONS -->

## Add reactions using libsbml

```python
# Example of adding a reaction to an SBML model using libSBML
import libsbml

# Assuming we already have an SBML string loaded
sbml_doc = libsbml.readSBMLFromString(input_sbml_string)
model = sbml_doc.getModel()

# Create a new reaction
reaction = model.createReaction()
reaction.setId("reaction1")
reaction.setReversible(False)
reaction.setFast(False)  # Required in SBML Level 3

# Add a reactant
reactant = reaction.createReactant()
reactant.setSpecies("A")  # Species ID
reactant.setStoichiometry(1.0)
reactant.setConstant(False)  # Required in SBML Level 3

# Add a product
product = reaction.createProduct()
product.setSpecies("B")  # Species ID
product.setStoichiometry(1.0)
product.setConstant(True)  # Required in SBML Level 3

# Write the updated SBML
writer = libsbml.SBMLWriter()
updated_sbml = writer.writeSBMLToString(sbml_doc)
```

# Submit the model

If you want to submit the model and end the process, put your final model as a string variable called `final_sbml` in your python code. It is recommended using libsbml to modify `input_sbml_string` rather than write the entire xml on your own.

# Response Format

Your response should follow thought-action framework in markdown formats. You should have a thoughts section followed by an action section.


"""
## Thoughts
write down your thoughs here.

## Action

### Code
Include this if you want to write codes. Put your code in a python block. You can only include one code block in each response.
```python
import numpy as np
import pandas as pd
```

### Experiment
Include this if you want to request experiments. Put your experiment configuration in a json block. You can only include one json block in each response.
```json
{
    "action": "",
    "meta_data": {}
}
```

### Submit
Include this if you want to submit the model and end the process. Put your final model as a string variable called `final_sbml` in your python code.
```python
import libsbml
final_sbml=...
```
"""
