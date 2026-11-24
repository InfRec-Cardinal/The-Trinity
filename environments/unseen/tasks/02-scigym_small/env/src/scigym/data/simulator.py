import logging
import warnings
from typing import Callable, Dict, List, Optional

import libsedml
import numpy as np
import roadrunner as rr
from tellurium.sedml.tesedml import (
    SEDMLCodeFactory,
    getKisaoStringFromVal,
    getKisaoValFromString,
)

from scigym.api import ExperimentResult
from scigym.data.sbml import SBML

logger = logging.getLogger(__name__)


def onEventTrigger(model: rr.ExecutableModel, eventIndex: int, eventId: str):
    print("event {} was triggered at time {}".format(eventId, model.getTime()))


def onEventAssignment(model: rr.ExecutableModel, eventIndex: int, eventId: str):
    print(dict(zip(model.getFloatingSpeciesIds(), model.getFloatingSpeciesConcentrations())))


def run_simulation(
    _rr: rr.RoadRunner,
    observed_species: List[str],
    observed_parameters: List[str],
    noise: float = 0.0,
    rm_concentration_brackets: bool = False,
    sed_simulation: Optional[libsedml.SedUniformTimeCourse] = None,
) -> ExperimentResult:
                                                            
    observed_species_with_brackets = [f"[{name}]" for name in observed_species]

                                                             
    observed_variables = observed_species_with_brackets + observed_parameters
    _rr.timeCourseSelections = ["time"] + observed_variables

    if sed_simulation is not None:
        initialTime = sed_simulation.getInitialTime()
        outputStartTime = sed_simulation.getOutputStartTime()
        outputEndTime = sed_simulation.getOutputEndTime()
        numberOfSteps = sed_simulation.getNumberOfSteps()
    else:
        print("Using default simulation parameters")
        initialTime = 0
        outputStartTime = 0
        outputEndTime = 10
        numberOfSteps = 100

    try:
                                
        if abs(outputStartTime - initialTime) > 1e-6:
            _rr.simulate(start=initialTime, end=outputStartTime, points=2)
                         
        result = _rr.simulate(start=outputStartTime, end=outputEndTime, steps=numberOfSteps)
    except Exception as e:
                                                                 
        raise

    colnames = result.colnames
    data = np.array(result.data)

                             
    experiment_time: List[float] = data.copy()[:, 0].tolist()                

                                                  
    time_series = {}
    for sid, sidwb in zip(observed_species, observed_species_with_brackets):
        if sidwb in colnames:
            i = colnames.index(sidwb)
            if i > -1:
                key = sid if rm_concentration_brackets else sidwb
                time_series[key] = data[:, i].tolist()

                                                     
    for pid in observed_parameters:
        try:
            i = colnames.index(pid)
            if i > -1:
                time_series[pid] = data[:, i].tolist()
        except ValueError:
                                                                             
            continue

    return ExperimentResult(time=experiment_time, result=time_series, raw_result=result)


class Simulator:
    pass                                                                  

    _rr: rr.RoadRunner
    event_ids: List[str]
    event_tracker: Dict[str, bool]
    simulation: libsedml.SedUniformTimeCourse

    def __init__(self, sbml: SBML, **kwargs) -> None:
        if not isinstance(sbml.sed_simulation, libsedml.SedUniformTimeCourse):
            raise ValueError(
                "The simulation configuration must be set on your SBML object to run the simulator."
            )
        self.sbml = sbml
        self.event_tracker = {}
        self.simulation = sbml.sed_simulation.clone()
        self._rr = SBML._get_rr_instance(sbml.to_string())
        self.event_ids = self._rr.model.getEventIds()

        Simulator._setup_integrator(
            self.simulation,
            self._rr,
            onTrigger=self.onEventTrigger,
            **kwargs,
        )
                                             

    def onEventTrigger(self, model: rr.ExecutableModel, eventIndex: int, eventId: str):
        self.event_tracker[eventId] = True

    def prepare_simulation(self) -> None:
        self._rr.resetSeed()
        self._rr.resetToOrigin()
        self.event_tracker = dict(zip(self.event_ids, [False] * len(self.event_ids)))

    def getSimulationParameters(self) -> Dict[str, float]:
        return dict(
            initialTime=self.simulation.getInitialTime(),
            outputStartTime=self.simulation.getOutputStartTime(),
            outputEndTime=self.simulation.getOutputEndTime(),
            numberOfSteps=self.simulation.getNumberOfPoints(),
        )

    def updateSimulationParameters(
        self,
        initialTime: Optional[float] = None,
        outputStartTime: Optional[float] = None,
        outputEndTime: Optional[float] = None,
        numberOfSteps: Optional[int] = None,
    ) -> None:
        pass                                  
        if initialTime is not None:
            self.simulation.setInitialTime(initialTime)
        if outputStartTime is not None:
            self.simulation.setOutputStartTime(outputStartTime)
        if outputEndTime is not None:
            self.simulation.setOutputEndTime(outputEndTime)
        if numberOfSteps is not None:
            self.simulation.setNumberOfPoints(numberOfSteps)

    def run(
        self,
        observed_species: List[str] | None = None,
        observed_parameters: List[str] = [],
        noise: float = 0.0,
        rm_concentration_brackets: bool = False,
    ) -> ExperimentResult:
        pass                                           
        self.prepare_simulation()
        try:
            if not observed_species:
                observed_species = self.sbml.get_species_ids()
            else:
                observed_species = [
                    species
                    for species in observed_species
                    if species in self.sbml.get_species_ids()
                ]
            return run_simulation(
                self._rr,
                observed_species=observed_species,
                observed_parameters=observed_parameters,
                noise=noise,
                rm_concentration_brackets=rm_concentration_brackets,
                sed_simulation=self.simulation,
            )
        except Exception as e:
            raise

    @staticmethod
    def _setup_integrator(
        simulation: libsedml.SedSimulation,
        _rr: rr.RoadRunner,
        onTrigger: Optional[Callable] = None,
        onAssignment: Optional[Callable] = None,
        force_cvode: bool = False,
    ):
        pass                                           
        algorithm = simulation.getAlgorithm()
        if algorithm is None:
            warnings.warn("Algorithm missing on simulation, defaulting to 'cvode: KISAO_0000019'")
            algorithm = simulation.createAlgorithm()
            algorithm.setKisaoID(getKisaoStringFromVal(19))

        kisao = getKisaoValFromString(algorithm.getKisaoID())
        kisaoname = ""
        if algorithm.isSetName():
            kisaoname = " (" + algorithm.getName() + ")"

                                         
        if force_cvode or not SEDMLCodeFactory.isSupportedAlgorithmForSimulationType(
            kisao=kisao, simType=libsedml.SEDML_SIMULATION_UNIFORMTIMECOURSE
        ):
            warnings.warn(
                "Algorithm {}{} unsupported for {} simulation '{}'.  Using CVODE.".format(
                    kisao, kisaoname, simulation.getElementName(), simulation.getId()
                )
            )
            algorithm = simulation.createAlgorithm()
            algorithm.setKisaoID(getKisaoStringFromVal(19))
            kisao = getKisaoValFromString(algorithm.getKisaoID())
            kisaoname = " (" + algorithm.getName() + ")"

                               
        integratorName = SEDMLCodeFactory.getIntegratorNameForKisaoID(kisao)
        if not integratorName:
            raise RuntimeError("No integrator exists for {} in roadrunner".format(kisao))

        _rr.setIntegrator(integratorName)

        if integratorName == "gillespie":
            _rr.integrator.setValue("variable_step_size", False)

                                                          
        eventIds = _rr.model.getEventIds()
        for eid in eventIds:
            try:
                e = _rr.model.getEvent(eid)
                if onTrigger is not None:
                    e.setOnTrigger(onTrigger)
                if onAssignment is not None:
                    e.setOnAssignment(onAssignment)
            except Exception as ex:
                logger.warning(f"Failed to set event listener for {eid}: {str(ex)}")

                                     
        if kisao == 288:       
            _rr.integrator.setValue("stiff", True)
        elif kisao == 280:                 
            _rr.integrator.setValue("stiff", False)

                                                          
        for par in algorithm.getListOfAlgorithmParameters():
            try:
                pkey = SEDMLCodeFactory.algorithmParameterToParameterKey(par)
                                                        
                if pkey:
                    if pkey.dtype is str:
                        value = "'{}'".format(pkey.value)
                    else:
                        value = pkey.value

                    if value == str("inf") or pkey.value == float("inf"):
                        value = "float('inf')"

                    if pkey.key == "conserved_moiety_analysis":
                        if pkey.dtype == str and pkey.value.isdigit():
                            _rr.conservedMoietyAnalysis = bool(int(pkey.value))
                        else:
                            _rr.conservedMoietyAnalysis = pkey.value
                    else:
                        _rr.integrator.setValue(pkey.key, value)
            except Exception as ex:
                logger.warning(f"Failed to set algorithm parameter: {str(ex)}")

        if getattr(_rr, "conservedMoietyAnalysis", False) == True:
            _rr.conservedMoietyAnalysis = False
