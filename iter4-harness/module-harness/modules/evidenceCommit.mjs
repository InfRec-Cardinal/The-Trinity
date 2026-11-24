

import {facts, cover, equal} from '../src/common.mjs';

export default function evidenceCommit({entity, observations, requirements, epoch,
  views = [], budget, submitCost = 1, maxVisits = 100000}) {
  if (!Number.isFinite(budget) || budget < 0 || !Number.isFinite(submitCost) || submitCost < 0)
    throw Error('Finite nonnegative budget and submitCost required');
  const reqs = Array.isArray(requirements) ? requirements.map(r => [r.attribute,r.value]) : Object.entries(requirements);
  if (reqs.some(([attribute]) => typeof attribute !== 'string') || new Set(reqs.map(r => r[0])).size !== reqs.length)
    throw Error('Requirements must have unique attribute names');
  const audit = facts(observations, entity, epoch), missing = [], contradictions = [];
  for (const [attribute, expected] of reqs) {
    if (!(attribute in audit.values)) missing.push(attribute);
    else if (!equal(audit.values[attribute], expected)) contradictions.push({entity,attribute,expected,
      observed:audit.values[attribute],sources:audit.sources[attribute]});
  }
  const relevant = new Set(reqs.map(r => r[0]));
  const conflicts = audit.conflicts.filter(k => relevant.has(k));
  const reserve = submitCost, canSpend = Math.max(0,budget-reserve);
  const base = {entity,missing,conflicts,contradictions,evidence:audit.sources,reserve,canSpend};

  if (contradictions.length) return {...base,status:'reject_with_witness',decision:'reject_with_evidence',
    witness:contradictions[0],action:{decision:'no',reasonAttribute:contradictions[0].attribute},
    savedUnnecessaryChecks:missing,canCommit:budget>=reserve};
  const needs = [...new Set([...missing,...conflicts])];
  if (!needs.length) return {...base,status:'confirm',decision:'confirm',canCommit:budget>=reserve};
  for (const v of views) if (!Number.isFinite(v.cost) || v.cost < 0 || !Array.isArray(v.covers))
    throw Error('Views require nonnegative cost and explicit public covers');
  const plan = cover(needs,views,canSpend,maxVisits);
  const ranking = views.map(v => ({...v,newAttributes:[...new Set(v.covers.filter(k=>needs.includes(k)))]}))
    .filter(v=>v.cost<=canSpend && v.newAttributes.length)
    .sort((a,b)=>b.newAttributes.length/Math.max(b.cost,1e-9)-a.newAttributes.length/Math.max(a.cost,1e-9));
  return {...base,status:'need_observation',decision:conflicts.length?'resolve_conflict':'acquire_evidence',
    canCommit:false,plan,nextView:plan.chosen?.[0] ?? ranking[0]?.id ?? null,viewRanking:ranking,
    note:'View coverage is a plan, not proof of an unseen value. Commit requires sourced, target-bound evidence.'};
}
