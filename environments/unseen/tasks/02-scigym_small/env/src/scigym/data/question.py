import os

from scigym.data.sbml import SBML


class Question:
    pass                                                              
       
    research_question: str
    task_difficulty: str
    original_sbml_model: SBML
    partial_sbml_model: SBML
    partial_runnable_sbml_model: SBML

    def __init__(
        self,
        sbml_directory_path: str,
        task_difficulty: str,
    ):
        self.task_difficulty = task_difficulty
        self.sbml_directory_path = sbml_directory_path
        self.load()

    def get_research_question(self) -> str:
        assert self.research_question is not None
        return self.research_question

    def get_partial_sbml(self) -> SBML:
        assert self.partial_sbml_model is not None
        return self.partial_sbml_model

    def get_runnable_partial_sbml(self) -> SBML:
        assert self.partial_runnable_sbml_model is not None
        return self.partial_runnable_sbml_model

    def get_original_sbml(self) -> SBML:
        assert self.original_sbml_model is not None
        return self.original_sbml_model

    def load(self) -> None:
        pass                                                  
           
                                                          
        path_to_truth_sbml = f"{self.sbml_directory_path}/truth.xml"
        path_to_truth_sedml = f"{self.sbml_directory_path}/truth.sedml"
        path_to_partial_sbml = f"{self.sbml_directory_path}/partial.xml"
        path_to_partial_runnable_sbml = f"{self.sbml_directory_path}/partial.xml"

        assert os.path.exists(path_to_truth_sedml)
        assert os.path.exists(path_to_truth_sbml)
        assert os.path.exists(path_to_partial_sbml)
        assert os.path.exists(path_to_partial_runnable_sbml)

        try:
            self.original_sbml_model = SBML(path_to_truth_sbml, path_to_truth_sedml)
            self.partial_sbml_model = SBML(path_to_partial_sbml, path_to_truth_sedml)
            self.partial_runnable_sbml_model = SBML(
                path_to_partial_runnable_sbml, path_to_truth_sedml
            )

        except Exception as e:
            raise ValueError(f"Failed to read question from {self.sbml_directory_path}: {str(e)}")
