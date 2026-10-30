import {clone, ensure} from './core.mjs';

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;

export function capabilityDefinitions(taxonomy, definitions, {required = true} = {}) {
  if (definitions === undefined && !required) return null;
  ensure(object(definitions), 'Capability definitions required; regenerate the Stage 2 training handoff');
  ensure(Array.isArray(taxonomy) && taxonomy.length === Object.keys(definitions).length &&
    taxonomy.every(id => Object.hasOwn(definitions, id)), 'Capability definitions must cover the taxonomy exactly');
  return Object.fromEntries(taxonomy.map(id => {
    const entry = definitions[id];
    ensure(object(entry) && entry.id === id && text(entry.name) && text(entry.definition), 'Missing or mismatched capability semantics: ' + id);
    const groups = entry.groups ?? {}, excludes = entry.excludes ?? [], typicalSymptoms = entry.typicalSymptoms ?? [];
    ensure(object(groups) && Object.entries(groups).every(([name, definition]) => text(name) && text(definition)), 'Invalid capability groups: ' + id);
    for (const values of [excludes, typicalSymptoms]) ensure(Array.isArray(values) && values.every(text), 'Invalid capability boundaries or symptoms: ' + id);
    return [id, clone({id, name: entry.name, definition: entry.definition, groups, excludes, typicalSymptoms})];
  }));
}

export function capabilityDescription(requirements, definitions) {
  if (!definitions) return 'Fixture capability identifiers (semantic definitions unavailable): ' + requirements.join(', ');
  const cards = requirements.map(id => {
    const entry = definitions[id];
    ensure(entry, 'Missing capability description: ' + id);
    return {id, name: entry.name, definition: entry.definition, groups: entry.groups,
      excludes: entry.excludes, typicalSymptoms: entry.typicalSymptoms};
  });
  return 'Training-induced capability definitions for this Harness path. Identifiers are labels, not meanings.\n' + JSON.stringify(cards, null, 2);
}
