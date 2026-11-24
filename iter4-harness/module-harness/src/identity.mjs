import {facts, cover, equal} from './common.mjs';

function audit({entity, observations, requirements, epoch}) {
  const f = facts(observations, entity, epoch), missing = [], contradictions = [];
  for (const [attribute, expected] of Object.entries(requirements)) {
    if (!(attribute in f.values)) missing.push(attribute);
    else if (!equal(f.values[attribute], expected)) contradictions.push({entity, attribute, expected,
      observed: f.values[attribute], sources: f.sources[attribute]});
  }
  return {...f, missing, contradictions};
}

export function relationalIdentity(input) {
  const {relations, relationEvidence, entity, budget, submitCost = 1} = input;
  const rows = relations.map(r => {
    const evidence = relationEvidence.filter(e => e.entity === entity && e.subject === r.subject &&
      e.object === r.object && e.frame === r.frame && e.visible === true && e.source &&
      (input.epoch === undefined || e.epoch === input.epoch));
    const values = [...new Set(evidence.map(e => e.relation))];
    return {requirement: r, status: values.length > 1 ? 'conflict' : !values.length ? 'missing' :
      values[0] === r.relation ? 'supported' : 'contradicted', sources: evidence.map(e => e.source), observed: values};
  });
  const a = audit(input), bad = rows.find(r => r.status === 'contradicted');
  return {status: a.contradictions.length || bad ? 'reject_with_witness' :
    !a.missing.length && !a.conflicts.length && rows.every(r => r.status === 'supported') ? 'confirm' : 'need_target_relation',
    attributeAudit: a, relationAudit: rows, witness: bad ?? a.contradictions[0] ?? null,
    budgetAllowsCommit: budget >= submitCost,
    excludedEvidence: relationEvidence.filter(e => e.entity !== entity).map(e => e.source)};
}
