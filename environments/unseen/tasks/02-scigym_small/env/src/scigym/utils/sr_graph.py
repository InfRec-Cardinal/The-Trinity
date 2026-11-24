from __future__ import absolute_import, division, print_function

from typing import Any, Dict, Set

import libsbml
import networkx as nx
from six import string_types
from tellurium.visualization.sbmldiagram import SBMLDiagram


def node_match(
    n1_attr: Dict[str, Any],
    n2_attr: Dict[str, Any],
):
    if n1_attr["type"] != n2_attr["type"]:
        return False
    if n1_attr["is_anchor"] == "False":
        return True
    return n1_attr["label"] == n2_attr["label"]


def edge_match(e1_attr: Dict[str, Any], e2_attr: Dict[str, Any]):
    if e1_attr["type"] != e2_attr["type"]:
        return False
    return True


class MySBMLDiagram(SBMLDiagram):
    def __init__(
        self,
        sbml,
        inco_species_ids: Set[str],
        inco_reaction_ids: Set[str],
        species={},
        reactions={},
        reactants={},
        products={},
        modifiers={},
        **kwargs,
    ):
        pass                                                                                      
                       
                      
                         
                        
                         
                        
                        
                       
                         
                        
           
                    
        if isinstance(sbml, string_types):
            self.doc = libsbml.readSBMLFromString(sbml)
            self.model = self.doc.getModel()
        elif isinstance(sbml, libsbml.SBMLDocument):
            self.doc = sbml
            self.model = self.doc.getModel()
        elif isinstance(sbml, libsbml.Model):
            self.model = sbml
        else:
            raise Exception("SBML Input is not valid")
                      
        self.g = MySBMLDiagram._createGraph(
            self.model,
            species=species,
            reactions=reactions,
            reactants=reactants,
            products=products,
            modifiers=modifiers,
            inco_species_ids=inco_species_ids,
            inco_reaction_ids=inco_reaction_ids,
            correct_pred_rp_rids=kwargs.get("correct_pred_rp_rids", set()),
            correct_pred_rpm_rids=kwargs.get("correct_pred_rpm_rids", set()),
            correct_pred_sids=kwargs.get("correct_pred_sids", set()),
        )

    @staticmethod
    def _createGraph(
        model,
        species={},
        reactions={},
        reactants={},
        products={},
        modifiers={},
        inco_species_ids=set(),
        inco_reaction_ids=set(),
        correct_pred_rp_rids: Set[str] = set(),
        correct_pred_rpm_rids: Set[str] = set(),
        correct_pred_sids: Set[str] = set(),
    ):
        pass                                                 
        import pygraphviz as pgv

        g = pgv.AGraph(strict=False, directed=True)

                                          
        g.node_attr["style"] = "filled"
        g.node_attr["shape"] = "circle"
        g.node_attr["fixedsize"] = "true"
        g.node_attr["fillcolor"] = "#ffffff"
        g.node_attr["fontcolor"] = "#000000"
        g.node_attr["fontsize"] = "9"

        anchor_color = "#79bfdb"
        missing_color = "#ed5a55"
        correct_color = "#7edb79"

                       
        for s in (model.getSpecies(k) for k in range(model.getNumSpecies())):
            label = s.getId()
            is_anchor = s.getId() in inco_species_ids
            is_correct = s.getId() in correct_pred_sids
            g.add_node(
                s.getId(),
                label=label,
                                          
                is_anchor=is_anchor,
                **species,
            )
            n: pgv.Node = g.get_node(s.getId())

            color = correct_color if is_correct else anchor_color if is_anchor else missing_color
            n.attr["fillcolor"] = color                

        for r in (model.getReaction(k) for k in range(model.getNumReactions())):
                            
            label = r.getId()
            is_anchor = r.getId() in inco_reaction_ids
            is_rp_correct = r.getId() in correct_pred_rp_rids
            is_rpm_correct = r.getId() in correct_pred_rpm_rids
            is_correct = is_rp_correct or is_rpm_correct
            g.add_node(
                r.getId(),
                label=label,
                width=0.15,
                height=0.15,
                is_anchor=is_anchor,
                **reactions,
            )
            n = g.get_node(r.getId())
            color = correct_color if is_correct else anchor_color if is_anchor else missing_color
            n.attr["fontsize"] = "1"                
            n.attr["fillcolor"] = color                
            n.attr["shape"] = "square"                

                   
            for s in (r.getReactant(k) for k in range(r.getNumReactants())):
                tail_is_anchor = s.getSpecies() in inco_species_ids
                head_is_anchor = is_anchor
                g.add_edge(
                    s.getSpecies(),
                    r.getId(),
                    tail=s.getSpecies(),
                    head=r.getId(),
                    tail_is_anchor=tail_is_anchor,
                    head_is_anchor=head_is_anchor,
                    color=color,
                    **reactants,
                )
            for s in (r.getProduct(k) for k in range(r.getNumProducts())):
                tail_is_anchor = is_anchor
                head_is_anchor = s.getSpecies() in inco_species_ids
                g.add_edge(
                    r.getId(),
                    s.getSpecies(),
                    tail=r.getId(),
                    head=s.getSpecies(),
                    tail_is_anchor=tail_is_anchor,
                    head_is_anchor=head_is_anchor,
                    color=color,
                    **products,
                )
            for s in (r.getModifier(k) for k in range(r.getNumModifiers())):
                tail_is_anchor = s.getSpecies() in inco_species_ids
                head_is_anchor = is_anchor
                color = (
                    correct_color
                    if is_rpm_correct
                    else anchor_color
                    if is_anchor
                    else missing_color
                )
                g.add_edge(
                    s.getSpecies(),
                    r.getId(),
                    tail=s.getSpecies(),
                    head=r.getId(),
                    tail_is_anchor=tail_is_anchor,
                    head_is_anchor=head_is_anchor,
                    color=color,
                    **modifiers,
                )
        return g

    def draw_and_save(self, filename, layout="neato", **kwargs):
        pass                               

                                             
                           
                                                                     
                         
           
        self.g.layout(prog=layout)
        self.g.draw(filename, **kwargs)

    def to_networkx(self):
        return nx.nx_agraph.from_agraph(self.g, create_using=nx.MultiDiGraph)
