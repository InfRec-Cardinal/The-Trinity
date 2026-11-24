from collections import defaultdict
from typing import Dict, List

import networkx as nx

from scigym.api import SBML_GRAPH_PARAMS, EvaluationResult
from scigym.data import SBML, Simulator
from scigym.utils.sr_graph import *        

from .utils import *        


class Evaluator:
    pass                                                            
       

    def __init__(
        self,
        true_sbml: SBML,
        incomplete_sbml: SBML,
        incomplete_runnable_sbml: SBML,
        mse_norm_type: str | None = "l2",
        ged_timeout: int = 30,
        mse_round: int = 50,
    ):
        self.true_sbml = true_sbml
        self.incomplete_sbml = incomplete_sbml
        self.mse_round = mse_round

        incomplete_runnable_sbml.load_sedml_from_string_or_file(true_sbml.to_sedml_string())
        self.incomplete_runnable_sbml = incomplete_runnable_sbml

                                 
        self.true_rpm_hashes, self.true_rp_hashes = extract_reaction_hashes(true_sbml.model)
        self.inco_rpm_hashes, self.inco_rp_hashes = extract_reaction_hashes(incomplete_sbml.model)
        self.missing_rp_hashes = self.true_rp_hashes.difference(self.inco_rp_hashes)
        self.missing_rpm_hashes = self.true_rpm_hashes.difference(self.inco_rpm_hashes)

                        
        self.inco_forward_hausdorff, self.inco_reverse_hausdorff = calculate_hausdorff_score(
            self.true_sbml.model,
            self.incomplete_sbml.model,
        )
        self.inco_mean_hausdorff = (self.inco_forward_hausdorff + self.inco_reverse_hausdorff) / 2

             
        self.mse_norm_type = mse_norm_type
        self.setup_mse_evaluation()

                             
        self.ged_timeout = ged_timeout
        self.inco_rids = set(incomplete_sbml.get_reaction_ids())
        self.inco_sids = set(incomplete_sbml.get_species_ids())
        self.true_graph = self.get_sbml_nx_graph(true_sbml)
        self.inco_graph = self.get_sbml_nx_graph(incomplete_sbml)
        self.inco_ged = compute_ged(self.inco_graph, self.true_graph, timeout=ged_timeout)

                                
        self.true_rid_to_klaw = extract_rid_to_kinetic_law(true_sbml.model)
        self.inco_rid_to_klaw = extract_rid_to_kinetic_law(incomplete_sbml.model)
        self.missing_rid_to_klaw = {
            r: k
            for r, k in self.true_rid_to_klaw.items()
            if r in self.inco_rid_to_klaw and self.inco_rid_to_klaw[r] == None
        }

    def setup_mse_evaluation(self) -> None:
        true_traj = self.run_simulations(self.true_sbml)
        inco_traj = self.run_simulations(self.incomplete_runnable_sbml)
        self.inco_traj = inco_traj
        self.true_traj = true_traj

    def evaluate_smape(self, pred_sbml: SBML) -> Dict[str, float]:
        pred_sbml.load_sedml_from_string_or_file(self.true_sbml.to_sedml_string())
        pred_traj = self.run_simulations(pred_sbml)

        pred_species = [f"[{sid}]" for sid in pred_sbml.get_species_ids()]
        pred_smape = compute_dict_smape(self.true_traj, pred_traj)
        return dict(observe_smape=pred_smape)

    def evaluate_smape_noise(self, pred_sbml: SBML, noise: float) -> Dict[str, Dict]:
        results = []
        pred_sbml.load_sedml_from_string_or_file(self.true_sbml.to_sedml_string())
        results = {}
        results[f"perturb_mse_{str(noise)}"] = {}
        for num_iter in range(self.mse_round):
            (
                noise_true_sbml,
                noise_inco_sbml,
                noise_pred_sbml,
            ) = SBML.eval_add_noise_to_initial_concentrations(
                self.true_sbml, self.incomplete_sbml, pred_sbml, noise
            )
            try:
                pred_traj = self.run_simulations(noise_pred_sbml)
                true_traj = self.run_simulations(noise_true_sbml)
            except:
                continue

            pred_species = [f"[{sid}]" for sid in pred_sbml.get_species_ids()]
            inco_species = [f"[{sid}]" for sid in self.incomplete_sbml.get_species_ids()]

            if not all([x in pred_species for x in inco_species]):
                raise ValueError(
                    f"Predicted species {pred_species} do not contain all incomplete species {inco_species}"
                )

            pred_species = [f"[{sid}]" for sid in pred_sbml.get_species_ids()]
            pred_smape = compute_dict_smape(self.true_traj, pred_traj)
            results[f"perturb_mse_{str(noise)}"][f"perturbation_{num_iter}"] = pred_smape
        pred_mse_values = []

                                                                   
        for key in results[f"perturb_mse_{str(noise)}"]:
                                                    
            if key.startswith("perturbation_"):
                                                        
                pred_mse = results[f"perturb_mse_{str(noise)}"][key]
                pred_mse_values.append(pred_mse)

                            
        stats = {
            "mean_pred_mse": sum(pred_mse_values) / len(pred_mse_values) if pred_mse_values else 0,
            "max_pred_mse": max(pred_mse_values) if pred_mse_values else 0,
            "min_pred_mse": min(pred_mse_values) if pred_mse_values else 0,
        }

                                                   
        results[f"perturb_mse_{str(noise)}"]["stats"] = stats
        return results

    def evaluate_solution_complexity(self, pred_sbml: SBML) -> Dict[str, float]:
        return dict(
            pred_length=len(pred_sbml.to_string()),
            true_length=len(self.true_sbml.to_string()),
            inco_length=len(self.incomplete_sbml.to_string()),
        )

    def evaluate_kinetic_law_similarity(self, pred_sbml: SBML) -> Dict[str, float]:
        metrics: Dict[str, List[float]] = defaultdict(list)
        pred_rid_to_klaw = extract_rid_to_kinetic_law(pred_sbml.model)
        for rid, true_klaw in self.missing_rid_to_klaw.items():
            assert true_klaw is not None
            pred_klaw = pred_rid_to_klaw.get(rid, None)
            if pred_klaw is None:
                metrics["bleu"].append(0.0)
            else:
                metrics["bleu"].append(get_average_bleu_from_klaw(true_klaw, pred_klaw))
        return {k: sum(v) / len(v) for k, v in metrics.items()}

    def evaluate_hausdorff_reaction_recovery(self, pred_sbml: SBML) -> Dict[str, float]:
        pred_forward_hausdorff, pred_reverse_hausdorff = calculate_hausdorff_score(
            self.true_sbml.model,
            pred_sbml.model,
        )
        pred_mean_hausdorff = (pred_forward_hausdorff + pred_reverse_hausdorff) / 2
        normalized_mean_hausdorff = normalized_metric(
            pred_mean_hausdorff,
            self.inco_mean_hausdorff,
        )
        return dict(
            normalized_hausdorff=normalized_mean_hausdorff,
            pred_hausdorff=pred_mean_hausdorff,
            inco_hausdorff=self.inco_mean_hausdorff,
        )

    def evaluate_exact_reaction_recovery(self, pred_sbml: SBML) -> Dict[str, float | List[int]]:
        pred_rpm_hashes, pred_rp_hashes = extract_reaction_hashes(pred_sbml.model)

        added_rp_hashes = pred_rp_hashes.difference(self.inco_rp_hashes)
        added_rpm_hashes = pred_rpm_hashes.difference(self.inco_rpm_hashes)

        rp_precision, rp_recall, rp_f1 = 0, 0, 0
        rpm_precision, rpm_recall, rpm_f1 = 0, 0, 0

                                                                        
        found_reaction_reactant_counts = []
        found_reaction_product_counts = []

                                                                      
        true_reactant_counts = []
        true_product_counts = []
        pred_reactant_counts = []
        pred_product_counts = []

                                                    
        for i in range(self.true_sbml.model.getNumReactions()):
            reaction = self.true_sbml.model.getReaction(i)
            true_reactant_counts.append(reaction.getNumReactants())
            true_product_counts.append(reaction.getNumProducts())

                                                         
        for i in range(pred_sbml.model.getNumReactions()):
            reaction = pred_sbml.model.getReaction(i)
            pred_reactant_counts.append(reaction.getNumReactants())
            pred_product_counts.append(reaction.getNumProducts())

        if len(self.missing_rp_hashes) > 0 and len(added_rp_hashes):
            found_rp_hashes = added_rp_hashes.intersection(self.missing_rp_hashes)
            rp_recall = len(found_rp_hashes) / len(self.missing_rp_hashes)
            rp_precision = len(found_rp_hashes) / len(added_rp_hashes)
            rp_f1 = (
                2 * rp_precision * rp_recall / (rp_precision + rp_recall)
                if (rp_precision + rp_recall) > 0
                else 0.0
            )

                                                                                   
                                                    
            for i in range(pred_sbml.model.getNumReactions()):
                reaction = pred_sbml.model.getReaction(i)
                rpm_hash, rp_hash = get_reaction_hash(reaction)
                if rp_hash in found_rp_hashes:
                    found_reaction_reactant_counts.append(reaction.getNumReactants())
                    found_reaction_product_counts.append(reaction.getNumProducts())

        if len(self.missing_rpm_hashes) > 0 and len(added_rpm_hashes):
            found_rpm_hashes = added_rpm_hashes.intersection(self.missing_rpm_hashes)
            rpm_recall = len(found_rpm_hashes) / len(self.missing_rpm_hashes)
            rpm_precision = len(found_rpm_hashes) / len(added_rpm_hashes)
            rpm_f1 = (
                2 * rpm_precision * rpm_recall / (rpm_precision + rpm_recall)
                if (rpm_precision + rpm_recall) > 0
                else 0.0
            )

        return dict(
            rp_precision=rp_precision,
            rp_recall=rp_recall,
            rp_f1=rp_f1,
            rpm_precision=rpm_precision,
            rpm_recall=rpm_recall,
            rpm_f1=rpm_f1,
        )

    def get_sbml_nx_graph(self, sbml: SBML) -> nx.MultiDiGraph:
        d = MySBMLDiagram(
            sbml.model,
            inco_species_ids=self.inco_sids,
            inco_reaction_ids=self.inco_rids,
            **SBML_GRAPH_PARAMS,
        )
        return nx.nx_agraph.from_agraph(d.g, create_using=nx.MultiDiGraph)

    def evaluate_graph_edit_distance(self, pred_sbml: SBML) -> Dict[str, float]:
        pred_graph = self.get_sbml_nx_graph(pred_sbml)
        pred_ged = compute_ged(pred_graph, self.true_graph, self.ged_timeout)
        normalized_ged = normalized_metric(pred_ged, self.inco_ged)
        return dict(pred_ged=pred_ged, inco_ged=self.inco_ged, normalized_ged=normalized_ged)

    def evaluate_species_interaction(self, pred_sbml: SBML) -> Dict[str, float]:
        metrics = evaluate_typed_species_interaction_f1(self.true_sbml.model, pred_sbml.model)
        return metrics

    def run_simulations(self, sbml: SBML) -> Dict[str, List[float]]:
        simulation = Simulator(sbml)
        data = simulation.run(observed_species=sbml.get_species_ids())
        assert data.result is not None
        return data.result

    def __call__(
        self, pred_sbml: SBML, perturb: bool = False, noise: float = 0.0
    ) -> EvaluationResult:
        if perturb:
            metrics = self.evaluate_smape_noise(pred_sbml, noise)
            return EvaluationResult(detailed_scores=metrics)
        metrics = self.evaluate_smape(pred_sbml)
        metrics |= self.evaluate_solution_complexity(pred_sbml)
        metrics |= self.evaluate_exact_reaction_recovery(pred_sbml)
        return EvaluationResult(detailed_scores=metrics)
