                                                                     

                                                                                
                                                                             
   
import copy
import json


def select_level(env, configuration):
    index = configuration['levelIndex']
    game = env._game
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(game._levels):
        raise ValueError('Invalid independent level index')
    if len(game._levels) != configuration['levelCount']:
        raise ValueError('Native level count disagrees with frozen manifest')
                                                                           
    if game._score != 0:
        raise ValueError('Independent level must start with zero completed levels')
    if index:
        game.set_level(index)
        observation = copy.copy(env.observation_space)
        observation.frame = [game.camera.render(game.current_level.get_sprites())]
        observation.levels_completed = game._score
        observation.state = game._state
        observation.available_actions = list(game._available_actions)
        observation.full_reset = False
                                                                                 
        env._last_response = observation
                                                                                
                                                                                
    env.scorecard_manager = None
    return game._score


def level_passed(observation, initial_completed):
    return observation.levels_completed > initial_completed


def terminal_reason(observation, initial_completed, attempts, limit):
    if level_passed(observation, initial_completed):
        return 'selected_native_level_completed'
                                                                          
                                                                             
    if observation.state.name == 'WIN':
        return 'native_' + observation.state.name
    if attempts >= limit:
        return 'independent_level_action_budget_exhausted'
    return None


def available_actions(observation):
                                                                           
                                                                          
    if observation.state.name == 'GAME_OVER':
        return [0]
    return sorted(set([0, *observation.available_actions]))


def level_score(configuration, success, native_actions):
    from arc_agi.scorecard import EnvironmentScoreCalculator
    baseline = configuration['baselineActions'][configuration['levelIndex']]
    if not isinstance(baseline, int) or baseline <= 0:
        raise ValueError('No positive version-matched native level baseline')
    calculator = EnvironmentScoreCalculator(id=configuration['id'])
    calculator.add_level(configuration['levelIndex'] + 1, success, native_actions,
                         baseline, configuration['gameId'])
    result = calculator.to_score().model_dump(mode='json')
    return {'score': result['level_scores'][0],
            'metric': 'official per-level RHAE (0..115), independent-start protocol',
            'officialCalculatorResult': result,
            'notComparableToSequentialFullGameScore': True}


def save_receipt(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
