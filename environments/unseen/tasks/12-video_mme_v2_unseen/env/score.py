#!/usr/bin/env python3
                                                                                             

      
                                                                                       

                                                                                         
                                                                                                    
                                                                                           

                                                                                           
                                                                                                    
                                                   
   
import argparse
import ast
import json
import os.path as osp
import re
import sys

import pandas as pd


                                                         
def extract_characters_regex_v2(s):
    pass                                                
    s = s.strip()
    answer_prefixes = [
        'Final Answer:',
        'The best answer is',
        'The correct answer is',
        'The answer is',
        'The answer',
        'The best option is',
        'The correct option is',
        'Best answer:',
        'Best option:',
        'Answer:',
        'Option:',
    ]
    for prefix in answer_prefixes:
        s = s.replace(prefix, '')
    if len(s.split()) > 10 and not re.search('[A-H]', s):
        return ''
    matches = re.search(r'[A-H]', s)
    if matches is None:
        return ''
    return matches[0]


                                                         
def cal_relevance_rating(scores):
    score_map = {0: 0.0, 1: 100.0 / 16, 2: 100.0 * 4 / 16, 3: 100.0 * 9 / 16, 4: 100.0}
    correct_count = sum(scores)
    return score_map.get(correct_count, 0.0)


                                                         
def cal_logic_rating(scores, group_structure):
    group_structure_list = ast.literal_eval(group_structure)
    last_correct_idx = -1
    for idx, val in enumerate(scores):
        if val:
            last_correct_idx = idx
        else:
            break
    if group_structure_list == [1, 2, 3, 4]:
        score_map = {0: 0.0, 1: 100.0 / 16, 2: 100.0 * 4 / 16, 3: 100.0 * 9 / 16, 4: 100.0}
    elif group_structure_list == [1, [2, 3], 4]:
        score_map = {0: 0.0, 1: 100.0 / 12, 2: 100.0 * 4 / 12, 3: 100.0 * 7 / 12, 4: 100.0}
        if last_correct_idx == 0 and scores[2]:
            last_correct_idx += 1
    elif group_structure_list == [[1, 2], 3, 4]:
        score_map = {0: 0.0, 1: 100.0 / 10, 2: 100.0 * 2 / 10, 3: 100.0 * 5 / 10, 4: 100.0}
        if last_correct_idx == -1 and scores[1]:
            last_correct_idx += 1
    else:
        raise ValueError(f'Unknown group_structure_list: {group_structure_list}')
    return score_map.get(last_correct_idx + 1, 0.0)


                                                         
def get_final_rating(data):
    pass                                                         
    overall_rating = {'total': []}
    group_type_rating = {'relevance': [], 'logic': []}
    level_rating = {'level_1': [], 'level_2': [], 'level_3': []}
    second_head_rating = {}
    third_head_rating = {}

    all_groups = [[] for _ in range(len(data) // 4)]
    for i in range(len(data)):
        group_type, group_structure = data.iloc[i]['group_type'], data.iloc[i]['group_structure']
        level, second_head, third_head = data.iloc[i]['level'], data.iloc[i]['second_head'], data.iloc[i]['third_head']
        score = data.iloc[i]['score']
        all_groups[i // 4].append((group_type, group_structure, level, second_head, third_head, score))

    for group in all_groups:
        group_type, group_structure = group[-1][0], group[-1][1]
        level, second_head, third_head = group[-1][2], group[-1][3], group[-1][4]
        scores = [1 if item[5] == 1 else 0 for item in group]

        if group_type == 'relevance':
            rating = cal_relevance_rating(scores)
            group_type_rating['relevance'].append(rating)
        elif group_type == 'logic':
            rating = cal_logic_rating(scores, group_structure)
            group_type_rating['logic'].append(rating)
        else:
            raise ValueError(f'Unknown group_type: {group_type}')
        overall_rating['total'].append(rating)
        level_rating[f'level_{int(level)}'].append(rating)
        second_head_rating.setdefault(second_head, []).append(rating)
        third_head_rating.setdefault(third_head, []).append(rating)

    overall_rating['total'] = sum(overall_rating['total']) / len(overall_rating['total'])
    group_type_rating = {k: (sum(v)/len(v)) if v else 0.0 for k, v in group_type_rating.items()}
    level_rating = {k: (sum(v)/len(v)) if v else 0.0 for k, v in level_rating.items()}
    second_head_rating = {k: (sum(v)/len(v)) if v else 0.0 for k, v in second_head_rating.items()}
    third_head_rating = {k: (sum(v)/len(v)) if v else 0.0 for k, v in third_head_rating.items()}
    return {
        'overall_rating': overall_rating,
        'group_type_rating': group_type_rating,
        'level_rating': level_rating,
        'second_head_rating': second_head_rating,
        'third_head_rating': third_head_rating,
    }


                                                         
def get_final_acc(data):
    data = data.copy()
    data['score'] = data['score'].apply(lambda x: 100.0 if x == 1 else 0.0)

    overall_acc = float(data['score'].mean())
    group_type_acc = {key: float(items['score'].mean())
                      for key, items in data.groupby('group_type')}
    level_acc = {f'level_{int(level)}': float(items['score'].mean())
                 for level, items in data.groupby('level')}
    second_head_acc = {key: float(items['score'].mean())
                       for key, items in data.groupby('second_head')}
    third_head_acc = {key: float(items['score'].mean())
                      for key, items in data.groupby('third_head')}
    return {
        'overall_acc': overall_acc,
        'group_type_acc': group_type_acc,
        'level_acc': level_acc,
        'second_head_acc': second_head_acc,
        'third_head_acc': third_head_acc,
    }


def main():
    here = osp.dirname(osp.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('responses')
    ap.add_argument('--questions', default=osp.join(here, 'questions.json'))
    ap.add_argument('--out', default=None, help='write the metrics JSON here')
    ap.add_argument('--scored-out', default=None, help='write per-question JSONL (extracted letter, score) here')
    a = ap.parse_args()

    questions = json.load(open(a.questions))
    qids = [q['questionId'] for q in questions]
    known = set(qids)
    resp, dup = {}, 0
    with open(a.responses) as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            r = json.loads(line)
            if r['questionId'] not in known:
                sys.exit(f'line {ln}: unknown questionId {r["questionId"]!r}')
            dup += r['questionId'] in resp
            resp[r['questionId']] = '' if r.get('rawResponse') is None else str(r['rawResponse'])
    if dup:
        print(f'warning: {dup} duplicate questionIds; the last line of each was used', file=sys.stderr)

                                                                                                           
                                                                               
    data = pd.DataFrame([dict(questionId=q['questionId'], videoId=q['videoId'], answer=q['answer'],
                              prediction=resp.get(q['questionId'], ''), group_type=q['groupType'],
                              group_structure=q['groupStructure'], level=q['level'],
                              second_head=q['secondHead'], third_head=q['thirdHead']) for q in questions])
    assert len(data) % 4 == 0
    for g in range(len(data) // 4):
        assert data.iloc[4 * g:4 * g + 4]['videoId'].nunique() == 1, f'group {g} spans videos'

                                                                      
    n_total = len(data)
    n_empty = int((data['prediction'] == '').sum())
    data['extracted'] = ''
    data['score'] = -1
    for i in range(len(data)):
        ans = str(data.iloc[i]['answer'])
        pred = str(data.iloc[i].get('prediction', ''))
        extracted = extract_characters_regex_v2(pred)
        data.at[i, 'extracted'] = extracted
        data.at[i, 'score'] = int(extracted == ans) if extracted else -1
    n_failed = int((data['score'] == -1).sum())

    rating = get_final_rating(data)
    acc = get_final_acc(data)
    valid = data[data['score'] >= 0]
    out = dict(
        n_questions=n_total, n_groups=n_total // 4, n_responses=len(resp), n_no_response=n_empty,
        n_extraction_failed=n_failed - n_empty,
        accuracy=acc['overall_acc'],                                                                           
        nonlinear_score=rating['overall_rating']['total'],                                                      
        simple_acc_valid_only=float(valid['score'].mean() * 100) if len(valid) else None,                     
        rating=rating, acc=acc)
    print(json.dumps({k: out[k] for k in ('n_questions', 'n_groups', 'n_responses', 'n_no_response',
                                          'n_extraction_failed', 'accuracy', 'nonlinear_score')}, indent=2))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=2, default=str)
    if a.scored_out:
        with open(a.scored_out, 'w') as f:
            for _, r in data.iterrows():
                f.write(json.dumps(dict(questionId=r.questionId, answer=r.answer, extracted=r.extracted,
                                        score=int(r.score))) + '\n')


if __name__ == '__main__':
    main()
