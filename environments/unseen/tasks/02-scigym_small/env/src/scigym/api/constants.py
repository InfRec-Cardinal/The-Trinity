import libsbml

                                                  
DEFAULT_METADATA_REMOVAL_CONFIG = {
                                                 
    "default": {
        "del_name": False,
        "del_metaid": True,
        "del_notes": True,
        "del_annotations": True,
        "del_history": True,
        "del_sbo_terms": True,
        "del_cv_terms": True,
        "del_created_date": True,
        "del_modified_date": True,
        "del_user_data": True,
    },
                                            
    libsbml.SBML_SPECIES: {
        "del_annotations": False,
        "del_cv_terms": False,
        "del_sbo_terms": False,
    },
                                                
    libsbml.SBML_COMPARTMENT: {
        "del_annotations": False,
        "del_cv_terms": False,
        "del_sbo_terms": False,
    },
                                                
                     
                                 
        
}


ANONYMIZE_EVERYTHING = {
    "default": {
        "del_name": True,
        "del_metaid": True,
        "del_notes": True,
        "del_annotations": True,
        "del_history": True,
        "del_sbo_terms": True,
        "del_cv_terms": True,
        "del_created_date": True,
        "del_modified_date": True,
        "del_user_data": True,
    },
}


ANONYMIZE_EVERYTHING_EXCEPT_SPECIES_CONFIG = {
    "default": {
        "del_name": True,
        "del_metaid": True,
        "del_notes": True,
        "del_annotations": True,
        "del_history": True,
        "del_sbo_terms": True,
        "del_cv_terms": True,
        "del_created_date": True,
        "del_modified_date": True,
        "del_user_data": True,
    },
    libsbml.SBML_SPECIES: {
        "del_name": False,
    },
}


ANONYMIZE_METADATA_REMOVAL_CONFIG = {
    "default": {
        "del_name": True,
        "del_metaid": True,
        "del_notes": True,
        "del_annotations": True,
        "del_history": True,
        "del_sbo_terms": True,
        "del_cv_terms": True,
        "del_created_date": True,
        "del_modified_date": True,
        "del_user_data": True,
    },
}


SBML_TYPES_TO_NOT_ANONYMIZE = []


SBML_TYPES_TO_CANONICALIZE = [libsbml.SBML_SPECIES]


DEFAULT_AVAILABLE_PACKAGES = [
    "numpy",
    "pandas",
    "libsbml",
    "math",
    "scipy",
    "jax",
    "sklearn",
    "io",
    "traceback",
]


f = lambda t: dict(type=t)

SBML_GRAPH_PARAMS = dict(
    species=f("species"),
    reactions=f("reaction"),
    reactants=f("reactant"),
    products=f("product"),
    modifiers=f("modifier"),
)


MODEL_TO_API_KEY_NAME = {
    "gemini-2.5-pro-preview-03-25": "GEMINI_API_KEY",
    "claude-3-5-haiku-20241022": "CLAUDE_API_KEY",
    "claude-3-7-sonnet-20250219": "CLAUDE_API_KEY",
}


DEMO_SBML_FILENAMES = [
    "BIOMD0000001014",
    "BIOMD0000000929",
    "BIOMD0000000004",
    "BIOMD0000000708",
    "BIOMD0000000306",
    "BIOMD0000000984",
    "BIOMD0000000043",
    "BIOMD0000000962",
    "BIOMD0000000744",
    "BIOMD0000000609",
]
