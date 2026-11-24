import os
import importlib
import logging
import json
import random

import numpy as np
import tqdm
from omegaconf import DictConfig, OmegaConf
import hydra
import pymc as pm
import arviz as az

from boxing_gym.agents.agent import LMExperimenter
import boxing_gym.envs.location_finding as location_finding
import boxing_gym.envs.hyperbolic_temporal_discount as hyperbolic_temporal_discount
import boxing_gym.envs.death_process as death_process
import boxing_gym.envs.irt as irt
import boxing_gym.envs.survival_analysis as survival_analysis
import boxing_gym.envs.peregrines as peregrines
import boxing_gym.envs.dugongs as dugongs
import boxing_gym.envs.lotka_volterra as lotka_volterra
import boxing_gym.envs.moral_machines as moral_machines
import boxing_gym.envs.emotion as emotion
from boxing_gym.agents.box_loop_helper import construct_features

try:
    from boxing_gym.agents.model_search import run_box_loop
except ImportError:
    print("Could not import model_search, make sure you have the correct version of the box-loop repo")
    pass
logging.basicConfig(level=logging.WARNING)


MAX_TRIES = 3

def augment_scientist_with_ppl(scientist, 
                               proposed_programs_all, 
                               critic_info_all, critic_mode=False):
    assert len(proposed_programs_all[-1]) > 0
    
    program_dict = proposed_programs_all[-1][0]
    str_prob_prog = program_dict['str_prob_prog']

    prompt_msg = f"""
To help guide your experimentation, your brilliant colleague has proposed the following program for the data.
Use this program to guide your experimentation.
Program: {str_prob_prog} \n

"""
    if critic_mode:
        assert len(critic_info_all[-1]) > 0
        str_hypotheses = critic_info_all[-1][0]['str_hypotheses']
        synthesis = critic_info_all[-1][0]['synthesis']
        prompt_msg += f"""
Here is criticism of the previous model: 
{str_hypotheses} \n
{synthesis} \n
"""

    system_message = scientist.system
    system_message += f"\n {prompt_msg}"
    print(f"system_message: {system_message}")
    scientist.messages[0]['content'] = [{"type": "text", "text": system_message}]
    
def iterative_experiment(
        goal, 
        scientist, 
        num_experiments, 
        num_evals, 
        include_prior, 
        naive_agent=None, 
        com_limit=None, 
        check_eig=False,
        use_ppl=False,
):
    results = []
    queries = []
    observations = []
    successes = []
    explanations = []
    eigs = []
    proposed_programs_all = [[]]
    critic_info_all = []

    if 0 in num_experiments:
        final_results = "You cannot make observations now. Make assumptions and provide your best guess to the following query."

        if use_ppl:
            if naive_agent is not None:
                result, explanation = evaluate_naive_explanation(final_results, goal, scientist, naive_agent, num_evals, include_prior, com_limit, use_ppl=use_ppl)
                explanations.append(explanation)
            else:
                result = ppl_evaluate(final_results, goal, scientist, num_evals, include_prior, proposed_programs_all, critic_info_all, prior_mode=True, critic_mode=False)
                augment_scientist_with_ppl(scientist, proposed_programs_all, critic_info_all, critic_mode=False)
        else:
            if naive_agent is not None:
                result, explanation = evaluate_naive_explanation(final_results, goal, scientist, naive_agent, num_evals, include_prior, com_limit)
                explanations.append(explanation)
            else:
                result = evaluate(final_results, goal, scientist, num_evals, include_prior)

        results.append(result)
        
    observation = None
    for i in tqdm.tqdm(range(num_experiments[-1])):                
        success = False
        observe = scientist.generate_actions(observation)
        queries.append(observe)
        observation, success = goal.env.run_experiment(observe)
        observations.append(observation)
        successes.append(success)
        tries = 1
        while not success and tries < MAX_TRIES:
            observe, _ = scientist.prompt_llm_and_parse(observation, True)
            queries.append(observe)
            observation, success = goal.env.run_experiment(observe)
            observations.append(observation)
            successes.append(success)
            if not success:
                tries += 1

        if success and check_eig:
            query_point = goal.env.validate_input(observe)
            eig = goal.expected_information_gain(query_point)
            eigs.append(eig)

        if i+1 in num_experiments:
            final_results = f"The final result is {observation}."
            if use_ppl:
                if naive_agent is not None:
                    result, explanation = evaluate_naive_explanation(final_results, goal, scientist, naive_agent, num_evals, include_prior, com_limit, use_ppl=use_ppl)
                    explanations.append(explanation)
                else:
                    result = ppl_evaluate(final_results, goal, scientist, num_evals, include_prior, proposed_programs_all, critic_info_all, critic_mode=True)
                    augment_scientist_with_ppl(scientist, proposed_programs_all, critic_info_all, critic_mode=True)

            else:
                if naive_agent is not None:
                    result, explanation = evaluate_naive_explanation(final_results, goal, scientist, naive_agent, num_evals, include_prior, com_limit)
                    explanations.append(explanation)
                else:
                    result = evaluate(final_results, goal, scientist, num_evals, include_prior)
            results.append(result)


    return results, queries, observations, successes, explanations, eigs, proposed_programs_all

def get_gen_model(gen_code):
    with open("ppl_gen_model.py", 'w') as file:
        file.write(gen_code)
    importlib.invalidate_caches()
    import src.boxing_gym.agents.ppl_gen_model as ppl_gen_model
    importlib.reload(ppl_gen_model)
    from src.boxing_gym.agents.ppl_gen_model import gen_model
    return gen_model

def get_ppl_prediction(env, program_dict, question, prior_mode):

    if prior_mode:
        str_prob_prog = program_dict['str_prob_prog']
        prior_model = get_gen_model(str_prob_prog)
        observed_df = construct_features(env, data=[question])
        model, prior_predictive = prior_model(observed_df)
        assert "y_obs" in prior_predictive

        if env.env_name == "irt":
            return str(1 if prior_predictive['y_obs'].mean() >= 0.5 else 0)

        elif env.env_name == "moral":
            return str(2 if prior_predictive['y_obs'].mean() >= 0.5 else 1)
        else:
            return str(prior_predictive['y_obs'].mean())

    else:
        model = program_dict['model']
        ordered_features = env.get_ordered_features() 
        trace = program_dict['trace']
        
        if env.env_name == "location_finding":
            question = question[0]
        elif env.env_name == "moral":
            assert 1 == 1
        else:
            assert len(ordered_features) == len(question)

        if env.env_name == "moral":
            group1 = question[0]
            group2 = question[1]
            intervention = question[2]
            row = []
            for attribute in ["count", "gender", "age", "social_status", "fitness", "species"]:
                attribute_diff = env.calculate_attr_diff(group1, group2, attribute)
                row.append(attribute_diff)
            data_dict = {}
            for i in range(0, len(row)):
                data_dict[ordered_features[i]] = np.array([row[i]])
            data_dict['intervention'] = np.array([1]) if intervention == 'swerve' else np.array([0])

        else:
            data_dict = {}
            for i in range(0, len(question)):
                data_dict[ordered_features[i]] = np.array([question[i]])
            
        
        with model:
            pm.set_data(data_dict)
            post_pred = pm.sample_posterior_predictive(trace, var_names=['y_obs'], return_inferencedata=False)
            assert 'y_obs' in post_pred
            numerical_pred = post_pred['y_obs'].flatten().mean()
            if env.env_name == "irt":
                print('env name is irt')
                numerical_pred = 1 if numerical_pred >= 0.5 else 0

            if env.env_name == "moral":
                print('env name is moral')
                numerical_pred = 2 if numerical_pred >= 0.5 else 1
            
            prediction = str(numerical_pred)
        return prediction

def ppl_evaluate(final_results, goal, scientist, num_evals, include_prior, proposed_programs_all, critic_info_all, prior_mode=False, critic_mode=False):

    if not prior_mode:
        goal.env.get_df()

    if len(critic_info_all) > 0:
        if len(critic_info_all[-1]) > 0:
            prev_str_hypotheses = critic_info_all[-1][0]['str_hypotheses']
            prev_synthesis = critic_info_all[-1][0]['synthesis']
        else:
            prev_str_hypotheses = None
            prev_synthesis = None

    else:
        prev_str_hypotheses = None
        prev_synthesis = None

    proposed_programs, critic_info = run_box_loop(env=goal.env, 
                                                  prior_mode=prior_mode,
                                                  critic_mode=critic_mode,
                                                  prev_synthesis=prev_synthesis,
                                                  prev_str_hypotheses=prev_str_hypotheses,
                                                  warm_start_examples=proposed_programs_all[-1])

    proposed_programs_all.append(proposed_programs)
    critic_info_all.append(critic_info)

    assert len(proposed_programs_all[-1]) > 0
    program_dict = proposed_programs_all[-1][0]

    predictions, gts, questions = [], [], []
    print(f"running {num_evals} evals")
    goal.eval_pointer = 0                                                   
    for _ in tqdm.tqdm(range(num_evals)):
        _, _= goal.get_goal_eval_question(include_prior)

        input_output_tuple = goal.eval_points[goal.eval_pointer-1]
        question = input_output_tuple[:-1]
        gt = input_output_tuple[-1]
        prediction = get_ppl_prediction(goal.env, program_dict, question, prior_mode)

        gts.append(gt)
        questions.append(str(question))
        predictions.append(prediction)
        print(f"prediction: {prediction}, gt: {gt}")
    

    return goal.evaluate_predictions(predictions, gts), questions, gts, predictions

def evaluate(final_results, goal, scientist, num_evals, include_prior):
    predictions, gts, questions = [], [], []
    print(f"running {num_evals} evals")
    goal.eval_pointer = 0                                                   
    for i in tqdm.tqdm(range(num_evals)):
        question, gt = goal.get_goal_eval_question(include_prior)
        question = final_results + '\n' + question
        prediction = scientist.generate_predictions(question)
        gts.append(gt)
        questions.append(question)
        predictions.append(prediction)
        print(f"prediction: {prediction}, gt: {gt}")
    return goal.evaluate_predictions(predictions, gts), questions, gts, predictions

def evaluate_naive_explanation(
        final_results, 
        goal, scientist, 
        naive_agent, 
        num_evals, 
        include_prior, 
        com_limit,
        use_ppl=False,
):
    if use_ppl:
        goal.env.get_df()
        proposed_programs, _ = run_box_loop(
            env=goal.env, 
            warm_start_examples=None
        )
        str_prob_prog = proposed_programs[0]['str_prob_prog']
        trace = proposed_programs[0]['trace']
        params_summary_str = az.summary(trace)['mean'].to_string()
        request_prompt = goal.get_comm_prompt(
            com_limit=com_limit, 
            include_prior=include_prior, 
            use_ppl=use_ppl, 
            str_prob_prog=str_prob_prog,
            params_summary_str=params_summary_str,
        )
    else:
        str_prob_prog = None
        request_prompt = goal.get_comm_prompt(com_limit=com_limit, include_prior=include_prior)

    print(f"request prompt: {request_prompt}")
    explanation = scientist.prompt_llm(request_prompt)
    print(f"explanation: {explanation}")
    naive_system_message = goal.get_naive_system_message(include_prior)
    naive_system_message += explanation
    print(f"naive_system_message: {naive_system_message}")
    naive_agent.set_system_message(naive_system_message)
    return evaluate(final_results, goal, naive_agent, num_evals, include_prior), explanation

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(config: DictConfig):
    seed = config.seed
    print(f"seed: {seed}")
    random.seed(seed)
                               

    model_name = config.llms.model_name
    temperature = config.llms.temperature
    max_tokens = config.llms.max_tokens
    num_experiments = config.exp.num_experiments
    env_params = config.envs.env_params
    experiment_type = config.exp.experiment_type
    include_prior = config.include_prior
    num_evals = config.envs.num_evals
    env_name = config.envs.env_name
    goal_name = config.envs.goal_name
    com_limit = config.envs.com_limit
    check_eig = False
    use_ppl= config.use_ppl

    nametoenv = {    
        "location_finding": location_finding.Signal,
        "hyperbolic_temporal_discount": hyperbolic_temporal_discount.TemporalDiscount,
        "death_process": death_process.DeathProcess,
        "irt": irt.IRT,
        "survival": survival_analysis.SurvivalAnalysis,
        "dugongs": dugongs.Dugongs,
        "peregrines": peregrines.Peregrines,
        "morals": moral_machines.MoralMachine,
        "emotion": emotion.EmotionFromOutcome,
        "lotka_volterra": lotka_volterra.LotkaVolterra,
    }
    nameenvtogoal = {
        ("hyperbolic_temporal_discount", "direct"): hyperbolic_temporal_discount.DirectGoal,
        ("hyperbolic_temporal_discount", "discount"): hyperbolic_temporal_discount.DiscountGoal,
        ("hyperbolic_temporal_discount", "direct_discovery"): hyperbolic_temporal_discount.DirectGoalNaive,
        ("location_finding", "direct"): location_finding.DirectGoal,
        ("location_finding", "source"): location_finding.SourceGoal,
        ("location_finding", "direct_discovery"): location_finding.DirectGoalNaive,
        ("death_process", "direct"): death_process.DirectDeath,
        ("death_process", "direct_discovery"): death_process.DirectDeathNaive,
        ("death_process", "infection"): death_process.InfectionRate,
        ("irt", "direct"): irt.DirectCorrectness,
        ("irt", "direct_discovery"): irt.DirectCorrectnessNaive,
        ("irt", "best_student"): irt.BestStudent,
        ("irt", "difficult_question"): irt.DifficultQuestion,
        ("irt", "discriminate_question"): irt.DiscriminatingQuestion,
        ("survival", "direct"): survival_analysis.DirectGoal,
        ("survival", "direct_discovery"): survival_analysis.DirectGoalNaive,
        ("dugongs", "direct"): dugongs.DirectGoal,
        ("dugongs", "direct_discovery"): dugongs.DirectGoalNaive,
        ("peregrines", "direct"): peregrines.DirectGoal,
        ("peregrines", "direct_discovery"): peregrines.DirectGoalNaive,
        ("emotion", "direct"): emotion.DirectEmotionPrediction,
        ("emotion", "direct_discovery"): emotion.DirectEmotionNaive,
        ("morals", "direct"): moral_machines.DirectPrediction,
        ("morals", "direct_discovery"): moral_machines.DirectPredictionNaive,
        ("lotka_volterra", "direct"): lotka_volterra.DirectGoal,
        ("lotka_volterra", "direct_discovery"): lotka_volterra.DirectGoalNaive,
    }

    env = nametoenv[env_name](**env_params)
    env.include_prior = include_prior
    goal = nameenvtogoal[(env_name, goal_name)](env)

    scientist_agent = LMExperimenter(model_name=model_name, temperature=temperature, max_tokens=max_tokens)
    naive_agent = None
    if experiment_type == "discovery":
        naive_agent = LMExperimenter(model_name=model_name, temperature=temperature, max_tokens=max_tokens)

    system_message = goal.get_system_message(include_prior)
    scientist_agent.set_system_message(system_message)
    
    print(f"running {num_experiments} experiments")
    all_data = iterative_experiment(goal, scientist_agent, num_experiments, num_evals, include_prior, naive_agent, com_limit, check_eig, use_ppl)

                                
    scientist_messages = scientist_agent.all_messages
    naive_messages = None
    if experiment_type == "discovery":
        naive_messages = naive_agent.all_messages
    
    results = []
    for d in all_data[0]:
        new_d1, new_d2 = None, None
        if isinstance(d[0], np.ndarray):
            new_d1 = d[0].tolist()
        else:
            new_d1 = d[0]
        if isinstance(d[1], np.ndarray):
            new_d2 = d[1].tolist()
        else:
            new_d2 = d[1]
        results.append([new_d1, new_d2])
    
                                  
    observations = []
    for i in range(len(all_data[2])):
        new_obs = None
        if isinstance(all_data[2][i], np.ndarray):
            new_obs = all_data[2][i].tolist()
        else:
            new_obs = all_data[2][i]
        observations.append(new_obs)

    only_programs = []
    for elem in all_data[-1]:
        try:
            if len(elem) > 0:
                only_programs.append(elem[0]['full_llm_response'])
        except:
            continue


    store_dict = {
        "config": OmegaConf.to_container(config, resolve=True),
        "data": {
            "results": all_data[0],
            "queries": all_data[1],
            "observations": all_data[2],
            "successes": all_data[3],
            "explanations": all_data[4],
            "eigs": all_data[5],
            "programs": only_programs,
        },
        "scientist_messages": scientist_messages,
        "naive_messages": naive_messages
    }
    res_dir = f"results/{env_name}"

    if use_ppl:
        model_name = model_name+"-boxloop"
    res_filename = f"{goal_name}_{model_name}_{experiment_type}_{include_prior}_{seed}_critic=True.json"
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)
    with open(os.path.join(res_dir, res_filename), 'w') as f:
        json.dump(store_dict, f, indent=4)

    print(model_name)
    print("finished successfully :)")

if __name__ == "__main__":
    main()