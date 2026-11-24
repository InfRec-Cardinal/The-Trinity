from __future__ import annotations

import os
import random
import traceback
import warnings
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Set, Tuple

import libsbml
import libsedml
import roadrunner
import tellurium as te
from libsbml import Model, SBase, SBMLDocument

from scigym.api import (
    DEFAULT_METADATA_REMOVAL_CONFIG,
    ApplyExperimentActionError,
    ExperimentConstraint,
    ModifySpeciesAction,
    NullifySpeciesAction,
    ParseExperimentActionError,
)
from scigym.utils.id_scrambler import SIdScrambler
from scigym.utils.main import *        


class SBML:
    pass                                                                     
                                                                                   
       

    model: Model
    document: SBMLDocument
    sed_simulation: libsedml.SedUniformTimeCourse
    sedml_document: libsedml.SedDocument | None = None

    def __init__(
        self,
        sbml_string_or_file: str,
        sedml_string_or_file: str | None = None,
    ):
        pass                                                    

             
                                                      
                                                                                       
           
        self.load_sbml_from_string_or_file(sbml_string_or_file)
        self.load_sedml_from_string_or_file(sedml_string_or_file)
        self.experiment_action_to_fn = {
            ModifySpeciesAction: self.change_initial_concentration,
            NullifySpeciesAction: self.nullify_species,
                                                              
                                                           
        }

    def load_sbml_from_string_or_file(self, sbml_string_or_file: Any) -> int:
        reader = libsbml.SBMLReader()

        doc: SBMLDocument
        model: Model
        if os.path.isfile(sbml_string_or_file):
            if not os.path.exists(sbml_string_or_file):
                raise ValueError(f"File {sbml_string_or_file} does not exist.")
            doc = reader.readSBMLFromFile(str(sbml_string_or_file))                
        else:
            doc = reader.readSBMLFromString(sbml_string_or_file)

        for i in range(doc.getNumErrors()):
            error: libsbml.SBMLError = doc.getError(i)
            if error.getSeverity() >= libsbml.LIBSBML_SEV_ERROR:
                raise ValueError(error.getMessage())

                                                 
        converter = libsbml.SBMLLocalParameterConverter()

        if converter.setDocument(doc) != libsbml.LIBSBML_OPERATION_SUCCESS:
            raise RuntimeError("Failed to set document for local parameter converter")

        if converter.convert() != libsbml.LIBSBML_OPERATION_SUCCESS:
            raise RuntimeError("Failed to convert local parameters to global ones")

                                                                        
                                                  
                                                                             
                                                                              
                                                                      
                                                                                        

                                                             
        if not doc.expandInitialAssignments():
            raise RuntimeError("Failed to expand initial assignments")

        if not doc.expandFunctionDefinitions():
            raise RuntimeError("Failed to expand function definitions")

                                              
        model = doc.getModel()

        if model is None:
            raise ValueError(f"Model object does not exist for {doc}")

                                                          
        for i in range(model.getNumParameters()):
            parameter: libsbml.Parameter = model.getParameter(i)
            if not parameter.isSetValue():
                parameter.setValue(0.0)

        self.document = doc
        self.model = model

        return True

    def load_sedml_from_string_or_file(self, sedml_string_or_file: Any | None) -> int:
        if not sedml_string_or_file:
            return False

        self.sedml_document = load_sedml_from_string_or_file(sedml_string_or_file)
        if self.sedml_document.getNumModels() != 1:
            print([model.getId() for model in self.sedml_document.getListOfModels()])
            print(sedml_string_or_file)

        sed_simulation = None
        outputEndTime = -float("inf")
        simulations: libsedml.SedListOfSimulations = self.sedml_document.getListOfSimulations()

        for i in range(simulations.size()):
            sim: libsedml.SedSimulation = simulations.get(i)
            simType: int = sim.getTypeCode()
            if simType is not libsedml.SEDML_SIMULATION_UNIFORMTIMECOURSE:
                continue
            assert isinstance(sim, libsedml.SedUniformTimeCourse)
            if sed_simulation is None or sim.getOutputEndTime() > outputEndTime:
                sed_simulation = sim
                outputEndTime = sim.getOutputEndTime()

        if sed_simulation is None:
            warnings.warn("No SedUniformTimeCourse simulation found in the SEDML document")
            tc = self.sedml_document.createUniformTimeCourse()
            tc.setInitialTime(0)
            tc.setOutputStartTime(0)
            tc.setOutputEndTime(10)
            tc.setNumberOfSteps(51)
            tc.setId("69")
            alg = tc.createAlgorithm()
            alg.setKisaoID("KISAO:0000019")
            self.sed_simulation = tc.clone()
        else:
            self.sed_simulation = sed_simulation.clone()

        return True

    def get_parameter_ids(self) -> List[str]:
        parameters: libsbml.ListOfParameters = self.model.getListOfParameters()
        return [parameters.get(j).getId() for j in range(parameters.size())]

    def get_functions_ids(self) -> List[str]:
        functions: libsbml.ListOfFunctionDefinitions = self.model.getListOfFunctionDefinitions()
        return [functions.get(j).getId() for j in range(functions.size())]

    def get_reaction_ids(self) -> List[str]:
        reactions: libsbml.ListOfReactions = self.model.getListOfReactions()
        return [reactions.get(j).getId() for j in range(reactions.size())]

    def get_species_ids(self, floating_only=False, boundary_only=False) -> List[str]:
        floating_sids = []
        boundary_sids = []
        all_species: libsbml.ListOfSpecies = self.model.getListOfSpecies()
        for i in range(all_species.size()):
            species: libsbml.Species = all_species.get(i)
            if species.getBoundaryCondition():
                boundary_sids.append(species.getId())
            else:
                floating_sids.append(species.getId())
        if floating_only:
            return floating_sids
        elif boundary_only:
            return boundary_sids
        return floating_sids + boundary_sids

    def get_experiment_constraints(
        self,
    ) -> Tuple[List[ExperimentConstraint], List[ExperimentConstraint]]:
        pass                                                         
        reaction_constraints = []
        for i in range(self.model.getNumReactions()):
            reaction: libsbml.Reaction = self.model.getReaction(i)
            reaction_constraints.append(get_experimental_constraint(reaction))
        species_constraints = []
        for i in range(self.model.getNumSpecies()):
            species: libsbml.Species = self.model.getSpecies(i)
            species_constraints.append(get_experimental_constraint(species))
        return reaction_constraints, species_constraints

    def get_initial_parameter_values(
        self, _rr: roadrunner.RoadRunner | None = None
    ) -> Dict[str, float]:
        _rr = SBML._get_rr_instance(self.to_string()) if _rr is None else _rr
        names = _rr.getGlobalParameterIds()
        values = _rr.getGlobalParameterValues()
        return {
            name: float(value) for name, value in zip(names, values) if name not in ["time", "t"]
        }

    def change_initial_parameter_value(
        self,
        pid: str,
        value: float,
        _rr: roadrunner.RoadRunner,
    ) -> int:
        assert pid in self.get_parameter_ids(), f"Parameter {pid} not found in the model"
        try:
            return _rr.setGlobalParameterByName(pid, value)
        except Exception as e:
            raise ApplyExperimentActionError(
                f"Failed to set initial parameter value for {pid} to {value}: {e}"
            )

    def get_initial_concentrations(
        self, _rr: roadrunner.RoadRunner | None = None
    ) -> Dict[str, float]:
        _rr = SBML._get_rr_instance(self.to_string()) if _rr is None else _rr
        floating_arr = _rr.getFloatingSpeciesConcentrationsNamedArray()
        boundary_arr = _rr.getBoundarySpeciesConcentrationsNamedArray()
        floating_conditions = dict(zip(floating_arr.colnames, floating_arr.tolist()[0]))
        boundary_conditions = dict(zip(boundary_arr.colnames, boundary_arr.tolist()[0]))
        initial_concentrations: Dict[str, float] = floating_conditions | boundary_conditions
        for sid, initc in initial_concentrations.items():
            if initc < 0:
                warnings.warn(f"Found negative initial concentration for {sid}: {initc}")
        return initial_concentrations

    def get_kinetic_law(self, reaction_id) -> libsbml.KineticLaw | None:
        reaction: libsbml.Reaction | None = self.model.getReaction(reaction_id)
        assert reaction is not None, f"Reaction {reaction_id} not found in the model"
        return reaction.getKineticLaw()

    def shuffle_all(self):
        pass                                           
        shuffle_parameters(self.model)
        shuffle_reactions(self.model)
        shuffle_species(self.model)
        shuffle_compartments(self.model)

    def remove_parameter(self, param_id: str | List[str]) -> int:
        param_ids = [param_id] if isinstance(param_id, str) else param_id
        valid_ids = self.get_parameter_ids()
        return_status = []
        for pid in param_ids:
            if pid not in valid_ids:
                raise ValueError(f"Parameter {pid} not found in the model")
            param: libsbml.Parameter = self.model.getParameter(pid)
            objects_to_remove = find_parameter_initializations(self.model, pid)
            for object in objects_to_remove:
                assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
            return_status.append(param.unsetValue())
        return return_status.count(libsbml.LIBSBML_OPERATION_SUCCESS)

    def remove_kinetic_law(self, reaction_id: str | List[str]) -> int:
        react_ids = [reaction_id] if isinstance(reaction_id, str) else reaction_id
        valid_ids = self.get_reaction_ids()
        removal_counter = 0
        for rid in react_ids:
            if rid not in valid_ids:
                raise ValueError(f"Reaction {rid} not found in the model")
            react: libsbml.Reaction = self.model.getReaction(rid)
            if not react.isSetKineticLaw():
                raise ValueError(f"Reaction {rid} does not have a kinetic law")
            removal_counter += self._remove_kinetic_law(rid)
        return removal_counter

    def _remove_kinetic_law(self, reaction_id: str) -> int:
        reaction: libsbml.Reaction = self.model.getReaction(reaction_id)
        if not reaction.isSetKineticLaw():
            return 1
        kinetic_law: libsbml.KineticLaw = reaction.getKineticLaw()
        assert kinetic_law.getNumLocalParameters() == 0
        assert kinetic_law.getNumParameters() == 0
        if not kinetic_law.isSetMath():
            return 1
        ast_node: libsbml.ASTNode = kinetic_law.getMath()
        objects_to_check: Dict[str, libsbml.SBase] = self._recursively_parse_ast_node(ast_node)
        assert kinetic_law.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
        for key, object in objects_to_check.items():
            assert key == object.getId()
            if self._count_usages(key) <= 1:
                assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
        return 1

    def _recursively_parse_ast_node(self, ast_node: libsbml.ASTNode) -> Dict[str, SBase]:
        objects = defaultdict(SBase)
        name = ast_node.getName()
        units = ast_node.getUnits()
        if name is not None:
            for o in [
                self.model.getParameter(name),
                self.model.getFunctionDefinition(name),
                self.model.getUnitDefinition(units),
            ]:
                if isinstance(o, libsbml.SBase):
                    objects[o.getId()] = o

        for j in range(ast_node.getNumChildren()):
            objects |= self._recursively_parse_ast_node(ast_node.getChild(j))

        return objects

    def _count_usages(self, sid: str) -> int:
        if sid is None or sid == "":
            return 0
        sbml_string = self.to_string()
        return (
            sbml_string.count(f" {sid} ")
            + sbml_string.count(f"'{sid}'")
            + sbml_string.count(f'"{sid}"')
        )

    def remove_reaction(self, reaction_id: str | List[str]) -> int:
        react_ids = [reaction_id] if isinstance(reaction_id, str) else reaction_id
        valid_ids = self.get_reaction_ids()
        return_success = 0
        for rid in react_ids:
            if rid not in valid_ids:
                raise ValueError(f"Reaction {rid} not found in the model")
            self._remove_kinetic_law(rid)
            return_success += self._remove_reaction(rid)
                                                 
        return return_success

    def _remove_reaction(self, reaction_id: str) -> int:
        reaction: libsbml.Reaction = self.model.getReaction(reaction_id)
        reaction_refs = find_reaction_references(self.model, reaction_id)
        for object in reaction_refs:
            assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
        return reaction.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS

    def remove_species(self, species_id: str | List[str]):
        species_ids = [species_id] if isinstance(species_id, str) else species_id
        valid_ids = self.get_species_ids()
        return_success = 0
        for sid in species_ids:
            if sid not in valid_ids:
                raise ValueError(f"Species {sid} not found in the model")
            return_success += self._remove_species(sid)
                                                 
        return return_success

    def _remove_species(self, species_id: str) -> int:
        species: libsbml.Species = self.model.getSpecies(species_id)
        species_refs = find_species_references(self.model, species_id)
        for object in species_refs:
            assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
        return species.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS

    def change_initial_concentration(
        self,
        action: ModifySpeciesAction,
        _rr: roadrunner.RoadRunner,
        verify_constraints=False,
        **kwargs,
    ) -> int:
        pass                                                                    
        species_id = action.species_id
        value = action.value
        assert species_id in self.get_species_ids(), f"Species {species_id} not found in the model"
        species: libsbml.Species = self.model.getSpecies(species_id)
        if verify_constraints:
            constraint = get_experimental_constraint(species)
            if not constraint.can_modify:
                raise ApplyExperimentActionError(f"Species {species_id} cannot be modified")
        try:
            if species.getConstant():
                raise ApplyExperimentActionError(f"Cannot modify a constant species {species_id}")
            return _rr.setInitConcentration(species_id, value, forceRegenerate=False)
        except ApplyExperimentActionError as e:
            raise
        except Exception as e:
            print(e)
            raise ApplyExperimentActionError(
                f"Failed to set initial concentration for {species_id} to {value}"
            )

    def nullify_species(
        self,
        action: NullifySpeciesAction,
        verify_constraints=False,
        **kwargs,
    ) -> int:
        species_id = action.species_id
        assert species_id in self.get_species_ids(), f"Species {species_id} not found in the model"
        species: libsbml.Species = self.model.getSpecies(species_id)
        if verify_constraints:
            constraint = get_experimental_constraint(species)
            if not constraint.can_nullify:
                raise ApplyExperimentActionError(f"Species {species_id} cannot be modified")
        try:
            ref_objects = find_species_knockout_references(self.model, species_id)
            for obj in ref_objects:
                assert obj.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
            dangling_objects = find_dangling_objects(self.model)
            for obj in dangling_objects:
                assert obj.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
            assert species.setBoundaryCondition(False) == libsbml.LIBSBML_OPERATION_SUCCESS
            assert species.setHasOnlySubstanceUnits(True) == libsbml.LIBSBML_OPERATION_SUCCESS
            assert species.setConstant(True) == libsbml.LIBSBML_OPERATION_SUCCESS
            return species.setInitialAmount(0.0) == libsbml.LIBSBML_OPERATION_SUCCESS
        except Exception as e:
            raise ApplyExperimentActionError(f"Failed to nullify species {species_id}")

    @classmethod
    def apply_experiment_actions(
        cls,
        sbml: SBML,
        experiment_actions: List[str],
        valid_species_ids: List[str],
        valid_reaction_ids: List[str],
        **kwargs,
    ) -> SBML:
        actions: List[ExperimentAction] = []
        for action in experiment_actions:
            try:
                action = parse_experiment_action(
                    action,
                    valid_species_ids,
                    valid_reaction_ids,
                )
                actions.append(action)
            except ParseExperimentActionError as e:
                raise
        return SBML._apply_experiment_actions(sbml, actions, **kwargs)

    @classmethod
    def _apply_experiment_actions(
        cls, sbml: SBML, actions: Sequence[ExperimentAction], **kwargs
    ) -> SBML:
        new_sbml = deepcopy(sbml)

        actions_by_type = defaultdict(list)
        for action in actions:
            actions_by_type[type(action)].append(action)

        modify_actions: List[ModifySpeciesAction] = actions_by_type.get(ModifySpeciesAction, [])
        nullify_actions: List[NullifySpeciesAction] = actions_by_type.get(NullifySpeciesAction, [])

        for a in nullify_actions:
            try:
                new_sbml.nullify_species(a, **kwargs)
            except ApplyExperimentActionError as e:
                raise

        _rr = SBML._get_rr_instance(new_sbml.to_string())

        for a in modify_actions:
            try:
                new_sbml.change_initial_concentration(a, _rr=_rr, **kwargs)
            except ApplyExperimentActionError as e:
                raise

        if len(modify_actions) > 0:
            try:
                new_sbml_string = str(_rr.getCurrentSBML())
                new_sbml = SBML(new_sbml_string, new_sbml.to_sedml_string())
            except Exception as e:
                raise ApplyExperimentActionError(f"Failed to apply experiment actions: {e}")

        return new_sbml

    @classmethod
    def add_noise_to_initial_concentrations(
        cls,
        sbml,
        noise_lower_bound=0.8,
        noise_upper_bound=1.2,
    ) -> SBML:
        new_sbml = cls(sbml.to_string(), sbml.to_sedml_string())
        _rr = SBML._get_rr_instance(new_sbml.to_string())
        init_concentrations = new_sbml.get_initial_concentrations(_rr)
        experiment_actions: List[ModifySpeciesAction] = []
        for species, concentration in init_concentrations.items():
            noise = random.uniform(noise_lower_bound, noise_upper_bound)
            experiment_actions.append(ModifySpeciesAction(species, noise * concentration))
        return SBML._apply_experiment_actions(new_sbml, experiment_actions)

    @classmethod
    def eval_add_noise_to_initial_concentrations(cls, true_sbml, inco_sbml, pred_sbml, noise):
        new_true_sbml = cls(true_sbml.to_string(), true_sbml.to_sedml_string())
        new_inco_sbml = cls(inco_sbml.to_string(), inco_sbml.to_sedml_string())
        new_pred_sbml = cls(pred_sbml.to_string(), pred_sbml.to_sedml_string())

        _rr_inco = SBML._get_rr_instance(new_inco_sbml.to_string())
        inco_concentrations = new_inco_sbml.get_initial_concentrations(_rr_inco)

        noise_dict = {}
        for species, concentration in inco_concentrations.items():
            Species: libsbml.Species = new_inco_sbml.model.getSpecies(species)
            if Species.getConstant() or Species.getBoundaryCondition():
                continue
            noise_dict[species] = perturb_concentration_proportional(concentration, noise)

        models = [new_true_sbml, new_inco_sbml, new_pred_sbml]
        noised_models = []

        for model in models:
            _rr = SBML._get_rr_instance(model.to_string())
            init_concentrations = model.get_initial_concentrations(_rr)
            experiment_actions: List[ModifySpeciesAction] = []

            for species, concentration in init_concentrations.items():
                if species in noise_dict:
                    experiment_actions.append(ModifySpeciesAction(species, noise_dict[species]))

            noised_model = SBML._apply_experiment_actions(model, experiment_actions)
            noised_models.append(noised_model)

        return noised_models

    def to_string(self) -> str:
        pass                                                         

             
                                      

                
                                                   
           
        return libsbml.writeSBMLToString(self.document)

    def save(self, path: str) -> int:
        pass                                          

             
                                               
           
        return libsbml.writeSBMLToFile(self.document, path)

    def to_sedml_string(self) -> str | None:
        if not self.sedml_document:
            return None
        return libsedml.writeSedMLToString(self.sedml_document)

    def save_sedml(self, path: str) -> int:
        return libsedml.writeSedMLToFile(self.sedml_document, path)

    @default_document_parameter
    def _remove_metadata(
        self,
        object: SBase,
        touched_elements: Set[int] = set(),
        config: Dict[Any, Dict[str, bool]] = DEFAULT_METADATA_REMOVAL_CONFIG,
    ) -> Set[int]:
        pass                                                           
                                                           
                                                        
           
        elements: libsbml.SBaseList = object.getListOfAllElements()

        for j in range(elements.getSize() + 1):
            if j == elements.getSize():
                element: SBase = object
            else:
                element: SBase = elements.get(j)

            settings = config["default"] | config.get(element.getTypeCode(), {})

            if settings["del_name"] and element.isSetName():
                element.unsetName()

            if settings["del_notes"] and element.isSetNotes():
                element.unsetNotes()

            if settings["del_annotations"] and element.isSetAnnotation():
                element.unsetAnnotation()

                                           
                                                             

            if settings["del_history"] and element.isSetModelHistory():
                element.unsetModelHistory()

            if settings["del_sbo_terms"] and element.isSetSBOTerm():
                element.unsetSBOTerm()

            if settings["del_cv_terms"] and element.getNumCVTerms() > 0:
                element.unsetCVTerms()

            if settings["del_created_date"] and element.isSetCreatedDate():
                element.unsetCreatedDate()

            if settings["del_modified_date"] and element.isSetModifiedDate():
                element.unsetModifiedDates()

            if settings["del_user_data"] and element.isSetUserData():
                element.unsetUserData()

            touched_elements.add(element.getMetaId())

            if settings["del_metaid"] and element.isSetMetaId():
                element.unsetMetaId()

        return touched_elements

    def _scramble_ids(self, type_codes_to_ignore: List[int] = []) -> Dict[int, Dict[str, str]]:
        pass                                                                   
                                                                     
           
        self._assign_unique_metaids()
        allElements = self.document.getListOfAllElements()
        oldIds = getAllIds(allElements=allElements)
        idScrambler = SIdScrambler(oldIds, type_codes_to_ignore)
        self.model.renameIDs(elements=allElements, idTransformer=idScrambler)
        self._remove_metaids()
                                                                        
        return idScrambler.real_to_fake_ids

    @default_document_parameter
    def _assign_unique_metaids(self, object: SBase, metaids: Set[str] = set()):
        elements: libsbml.SBaseList = object.getListOfAllElements()
        for j in range(elements.getSize()):
            element: SBase = elements.get(j)
            new_metaid = generate_new_id(prefix="metaid_", ban_list=metaids)
            element.setMetaId(new_metaid)
            metaids.add(new_metaid)

    @default_document_parameter
    def _remove_metaids(self, object: SBase, metaids: Set[str] = set()):
        elements: libsbml.SBaseList = object.getListOfAllElements()
        for j in range(elements.getSize()):
            element: SBase = elements.get(j)
            if element.isSetMetaId():
                element.unsetMetaId()
                metaids.add(element.getMetaId())

    def _canonicalize_names(
        self, type_codes_to_include: List[int] = []
    ) -> Dict[int, Dict[str, str]]:
        pass                                                                     
                                                                                                
           
        real_to_fake_names: Dict[int, Dict[str, str]] = defaultdict(dict)
        allElements: libsbml.SBaseList = self.document.getListOfAllElements()
        for j in range(allElements.getSize()):
            element: libsbml.SBase = allElements.get(j)
            type_code = element.getTypeCode()
            if type_code not in type_codes_to_include:
                continue
            if not element.isSetName():
                oldName = element.getId()
            else:
                oldName = element.getName()
            if oldName == "" or oldName is None:
                continue
                                                  
            newName = oldName
            if newName != oldName:
                assert element.setName(newName) == libsbml.LIBSBML_OPERATION_SUCCESS
                real_to_fake_names[type_code][oldName] = newName
        return real_to_fake_names

    def _validate_references(self, real_to_fake_ids: Dict[int, Dict[str, str]] = {}) -> bool:
        pass                                                           
        sbml_string = self.to_string()
                                              
        for type_code in real_to_fake_ids.keys():
            for old_id in real_to_fake_ids[type_code].keys():
                                                                      
                if old_id in ["time"]:
                    continue
                for query in [f'"{old_id}"', f"'{old_id}'", f" {old_id} "]:
                    if query in sbml_string:
                        where = sbml_string.find(query)
                        print(
                            f"WARNING: Found old ID '{query}' still in document at position {where}"
                        )
                        return False
        return True

    @classmethod
    def _get_rr_instance(cls, sbml_string_or_file: str, *args, **kwargs) -> roadrunner.RoadRunner:
        return te.loadSBMLModel(sbml_string_or_file)
                                                                            

    @classmethod
    def code_to_sbml(
        cls, sbml: "SBML", executable_file_as_string: str, safe_globals: Dict[str, Any] = {}
    ) -> SBML:
        pass                                                                                  
                                                                                   
                                                                                 
                                     

             
                                                  
                                                                              

                
                                          
           

        try:
                                                                         
            code = (
                "import numpy as np\nimport pandas as pd\nimport math\nimport scipy\nimport sklearn\nimport jax\nimport tellurium as te\nimport roadrunner as rr\nimport libsbml\n"
                + executable_file_as_string
            )

                                                                                          
            safe_globals["modified_sbml_string"] = None

                                                                       
            exec(code, safe_globals)

            modified_sbml_string: str = safe_globals["modified_sbml_string"]                
            return SBML(modified_sbml_string)

        except Exception as e:
                                       
            error_message = traceback.format_exc()
            raise ValueError(error_message)

    def __deepcopy__(self, memo):
        pass                                       

             
                                                                          
                                                                   
           
                                                                
        if id(self) in memo:
            return memo[id(self)]

                                                                      
        result = SBML(
            sbml_string_or_file=self.to_string(),
            sedml_string_or_file=self.to_sedml_string(),
        )
        return result
