#!/usr/bin/env python3
                                                                                                              

                                                                           
                                                               

                                                                                                                    
                                                                                                                    
                                                                                                                   
                                                                                                                        
                                                                                                                        
                                                                                                                   
                                                                                    
   
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))                                                  
BASE = os.environ.get('AGENTB_CODENAMES_SRC') or os.path.join(ROOT, 'vendor', 'codenames')
GPT_DIR = os.path.join(BASE, 'codenames_gpt')
ORIGINAL = os.path.join(BASE, 'original/players')
GLOVE = os.environ.get('AGENTB_CODENAMES_GLOVE') or os.path.join(ROOT, 'data', 'glove')
OUT = os.fdopen(os.dup(1), 'w')


def emit(payload):
    OUT.write(json.dumps(payload) + '\n'); OUT.flush(); os._exit(0)


class NeedClue(Exception):
    pass


class InvalidClue(Exception):
    pass


class GloveVectors:
    pass                                                                                               
    def __init__(self, dimension):
        import numpy as np
        self.np = np
        self.matrix = np.load(os.path.join(GLOVE, f'glove.6B.{dimension}d.f64.npy'), mmap_mode='r')
        with open(os.path.join(GLOVE, 'glove.6B.100d.vocab.json'), encoding='utf-8') as f:
            self.index = {word: i for i, word in enumerate(json.load(f))}

    def __getitem__(self, word):
        return self.np.array(self.matrix[self.index[word]])

    def __contains__(self, word):
        return word in self.index


def load_original(name):
    spec = importlib.util.spec_from_file_location(f'agentb_original_{name}', os.path.join(ORIGINAL, f'{name}.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module.AIGuesser


def main():
    request = json.loads(sys.stdin.read())
    instance, actions = request['instance'], request['actions']
    os.chdir(GPT_DIR); sys.path.insert(0, GPT_DIR)
    from game import Game, GameCondition                       
    from players.codemaster import Codemaster
    queue = list(actions)
    log = {'clues': [], 'invalid': None}

    class AgentBCodemaster(Codemaster):
        def __init__(self, team='Red'):
            super().__init__(); self.team = team

        def set_game_state(self, words, maps):
            self.words, self.maps = words, maps

        def get_clue(self):
            if not queue:
                raise NeedClue()
            action = queue.pop(0); clue = action['clue'].strip().upper(); number = action['number']
            log['clues'].append({'clue': clue, 'number': number})
            if not re.fullmatch(r'[A-Z]+', clue):
                raise InvalidClue('clue_not_a_single_word')
            if number < 1:
                raise InvalidClue('clue_number_below_one')
            for word in self.words:
                if word[0] != '*' and (clue in word or word in clue):
                    raise InvalidClue('clue_derived_from_board_word')
                                                                      
            return [clue.lower(), number]

    partner = load_original('guesser_glove')
    kwargs = {'glove_vecs': GloveVectors({'glove_100d': 100, 'glove_50d': 50}[instance['partner']])}
    game = Game(AgentBCodemaster, partner, AgentBCodemaster, partner, seed=instance['seed'], do_print=False, do_log=False,
                game_name='agentb', gr_kwargs=kwargs, gb_kwargs=kwargs, single_team=True)
    initial_words = list(game.words_on_board); key = list(game.key_grid)
    reason, outcome, ended = None, None, False
    try:
        game.run()
        ended = True
        outcome = 'success' if game.game_winner == 'R' and game.words_on_board.count('*Red*') >= 9 else 'failure'
        reason = 'all_red_words_revealed' if outcome == 'success' else ('assassin_revealed' if '*Assassin*' in game.words_on_board else 'all_blue_words_revealed')
    except NeedClue:
        if len(actions) >= instance['clueBudget']:
            ended, outcome, reason = True, 'failure', 'clue_budget_exhausted'
    except InvalidClue as error:
        ended, outcome, reason = True, 'failure', f'invalid_clue:{error}'
    except Exception as error:                                                                               
        ended, outcome, reason = True, 'failure', f'partner_guesser_error:{type(error).__name__}'
    sys.stdout = sys.__stdout__
    board = list(game.words_on_board); history = [list(m) for m in game.move_history]
    turns = sum(1 for m in history if m[0].endswith('_Codemaster')) + (1 if reason and reason.startswith('invalid_clue') else 0)
    score = turns if outcome == 'success' else (25 if ended else None)
    counts = {t: board.count(f'*{t}*') for t in ['Red', 'Blue', 'Civilian', 'Assassin']}
    lines = ['You are the Red Codemaster in the single-team Codenames track. Your partner guesser never sees the key grid.',
             'Board (unrevealed words in upper case, revealed slots show their identity) and your private key grid:']
    for row in range(5):
        lines.append(' | '.join(f'{board[5 * row + c]} [{key[5 * row + c]}]' for c in range(5)))
    lines.append(f'Revealed so far: {json.dumps(counts)} (9 Red, 8 Blue, 7 Civilian, 1 Assassin in total).')
    lines.append('Move history: ' + (json.dumps(history) if history else '(none)'))
    lines.append(f'Clues used: {len(log["clues"])}/{instance["clueBudget"]}.')
    if ended:
        lines.append(f'Game over: {outcome} ({reason}). Score (turns, lower is better; 25 on any loss): {score}.')
    state = {'seed': instance['seed'], 'partner': instance['partner'], 'board': board, 'keyGrid': key, 'initialWords': initial_words,
             'moveHistory': history, 'clues': log['clues'], 'consumed': len(actions)}
    terminal = {'ended': ended, 'outcome': outcome, 'reason': reason}
    if ended:
        terminal.update({'score': score, 'evaluation': {'turns': score, 'winner': game.game_winner, 'revealed': counts, 'seed': instance['seed'], 'partnerGuesser': instance['partner'],
                                                         'framework': 'stepmat/Codenames_GPT@f13d9fc', 'moveHistory': history}})
    emit({'ok': True, 'state': state, 'text': '\n'.join(lines), 'reward': (25 - score) if ended else 0, 'info': {'cluesUsed': len(log['clues']), 'revealed': counts}, 'terminal': terminal})


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        emit({'ok': False, 'message': f'{type(error).__name__}: {error}'})
