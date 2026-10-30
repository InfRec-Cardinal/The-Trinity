import {hostVerificationCall, publicVerificationChecks} from './host-verification.mjs';
import {clone, digest, ensure} from './core.mjs';

const read = (object, pointer) => pointer.split('/').slice(1).reduce((value, key) => value?.[key.replaceAll('~1', '/').replaceAll('~0', '~')], object);
const pointer = value => typeof value === 'string' && value.startsWith('/') && value.length > 1;
const number = value => typeof value === 'number' && Number.isFinite(value);
function changes(before, after, prefix = '') {
  if (digest(before ?? null) === digest(after ?? null)) return [];
  if (!before || !after || typeof before !== 'object' || typeof after !== 'object' || Array.isArray(before) || Array.isArray(after)) return [prefix];
  return [...new Set([...Object.keys(before), ...Object.keys(after)])].flatMap(key =>
    changes(before[key], after[key], prefix + '/' + key.replaceAll('~', '~0').replaceAll('/', '~1')));
}

async function replay(driver, world, route, budget) {
  const steps = [];
  let session, initialStateHash = null, error = null;
  try {
    session = await hostVerificationCall('audit_reset', () => driver.reset(clone(world)));
    ensure(session && session.observation, 'Audit reset has no observation');
    ensure(typeof driver.initialState === 'function', 'Creator route comparison requires initialState');
    initialStateHash = digest(await hostVerificationCall('audit_initial_state', () => driver.initialState(session)));
    for (const action of route.actions) {
      ensure(steps.length < budget, 'Audit route exceeds the host action budget');
      ensure(!steps.at(-1)?.receipt.done, 'Audit route continues after terminal action');
      const receipt = await hostVerificationCall('audit_step', () => driver.step(session, clone(action)));
      ensure(receipt && typeof receipt.done === 'boolean' && typeof receipt.success === 'boolean' && receipt.observation && number(receipt.cost) && receipt.cost >= 0 && (!receipt.success || receipt.done), 'Invalid audit execution receipt');
      steps.push({action: clone(action), receipt: clone(receipt)});
    }
  } catch (caught) {error = String(caught.message);}
  finally {
    if (session && driver.close) try {await hostVerificationCall('audit_cleanup', () => driver.close(session));} catch (caught) {error = 'Audit cleanup failed: ' + caught.message;}
  }
  return {id: route.id, kind: route.kind, steps, error, initialStateHash, complete: !error && steps.length === route.actions.length && steps.at(-1)?.receipt.done === true,
    success: !error && steps.at(-1)?.receipt.done === true && steps.at(-1)?.receipt.success === true,
    actions: steps.length, cost: steps.reduce((sum, step) => sum + step.receipt.cost, 0)};
}


export async function inspectCreatorBuild({driver, world, design, buildDigest, context}) {
  const native = await hostVerificationCall('native_inspection', () => driver.inspect(clone(world), clone(design), buildDigest));
  ensure(native.buildDigest === buildDigest && Array.isArray(native.checks), 'Invalid native inspection');
  const report = {buildDigest, checks: publicVerificationChecks(native.checks), measurements: {...clone(native.measurements ?? {}), core: {}}, hostEvidence: null};
  try {
    ensure(typeof driver.creatorAuditPlan === 'function', 'Adapter must implement creatorAuditPlan; boolean audit flags are not evidence');
    const plan = await hostVerificationCall('audit_plan', () => driver.creatorAuditPlan(clone(world), clone(design)));
    ensure(plan?.schema === 'creator-audit-plan-v1', 'Unsupported Creator audit plan');
    ensure(Array.isArray(plan.routes) && plan.routes.length >= 3 && plan.routes.length <= 16, 'Provide bounded witness, negative and detour routes');
    ensure(new Set(plan.routes.map(r => r.id)).size === plan.routes.length, 'Duplicate audit route IDs');
    for (const route of plan.routes) ensure(typeof route.id === 'string' && ['witness', 'negative', 'detour'].includes(route.kind) &&
      Array.isArray(route.actions) && route.actions.length > 0 && route.actions.length <= context.actionBudget, 'Invalid bounded audit route');
    for (const kind of ['witness', 'negative', 'detour']) ensure(plan.routes.some(r => r.kind === kind), 'Missing audit route: ' + kind);
    ensure(Array.isArray(plan.axes) && plan.axes.length > 0 && plan.axes.every(axis => pointer(axis.path) && number(axis.min) && number(axis.max) && axis.min <= axis.max && (axis.maxStep === undefined || number(axis.maxStep) && axis.maxStep > 0) && ['increase', 'decrease'].includes(axis.harder)), 'Declare bounded difficulty axes');
    ensure(Array.isArray(plan.bindings) && plan.bindings.length > 0 && plan.bindings.every(b => pointer(b.world) && pointer(b.design)), 'Frozen design bindings required');
    ensure(Array.isArray(plan.repairPaths) && plan.repairPaths.every(pointer), 'Repair paths required');
    ensure(Array.isArray(plan.layoutPaths) && plan.layoutPaths.length > 0 && plan.layoutPaths.every(pointer), 'Layout evidence paths required');
    const routes = [];
    for (const route of plan.routes) routes.push(await replay(driver, world, route, context.actionBudget));
    const currentDigest = digest(await hostVerificationCall('audit_fingerprint', () => driver.fingerprint(clone(world))));
    ensure(currentDigest === buildDigest, 'Build mutated during host audit replay');
    const witnesses = routes.filter(r => r.kind === 'witness'), negatives = routes.filter(r => r.kind === 'negative'), detours = routes.filter(r => r.kind === 'detour');
    ensure(routes.every(r => r.initialStateHash && r.initialStateHash === routes[0].initialStateHash), 'Creator audit routes have different initial states');
    const directActions = Math.min(...witnesses.filter(r => r.complete && r.success).map(r => r.actions));
    const detourActions = Math.min(...detours.filter(r => r.complete && r.success).map(r => r.actions));
    const changed = context.previousWorld ? changes(context.previousWorld, world) : [];
    const axisChanges = plan.axes.filter(axis => changed.includes(axis.path));
    const adjusting = context.feedback?.kind === 'difficulty_adjustment';
    const allowed = adjusting ? plan.axes.map(axis => axis.path) : plan.repairPaths;
    const isAllowed = changed.every(field => allowed.some(base => field === base || field.startsWith(base + '/')));
    const axisValues = plan.axes.map(axis => ({...axis, value: read(world, axis.path), previous: context.previousWorld ? read(context.previousWorld, axis.path) : null}));
    const directionValid = !adjusting || axisChanges.length === 1 && axisValues.filter(a => changed.includes(a.path)).every(axis => {
      const harder = context.feedback.reason === 'too_easy';
      const expectedIncrease = harder === (axis.harder === 'increase');
      return number(axis.previous) && number(axis.value) && (axis.maxStep === undefined || Math.abs(axis.value - axis.previous) <= axis.maxStep) && (expectedIncrease ? axis.value > axis.previous : axis.value < axis.previous);
    });
    const layout = plan.layoutPaths.map(field => ({field, value: read(world, field)}));
    const bindingsValid = plan.bindings.every(binding => read(world, binding.world) !== undefined && read(design, binding.design) !== undefined && digest(read(world, binding.world)) === digest(read(design, binding.design)));


    ensure(['witnessCost', 'witnessActions'].includes(plan.effortMetric), 'Declare a replayed effort metric');
    ensure(plan.neutralizedWorld && typeof plan.neutralizedWorld === 'object', 'A neutralized control world is required');
    const controlChanges = changes(world, plan.neutralizedWorld);
    ensure(controlChanges.every(field => plan.axes.some(axis => axis.path === field)), 'Neutralized control changes non-difficulty mechanisms');
    const measure = rows => Math.min(...rows.filter(r => r.kind === 'witness' && r.complete && r.success)
      .map(r => plan.effortMetric === 'witnessCost' ? r.cost : r.actions));
    const replayWorld = async other => {
      const otherPlan = await hostVerificationCall('control_plan', () => driver.creatorAuditPlan(clone(other), clone(design)));
      ensure(otherPlan.effortMetric === plan.effortMetric && otherPlan.routes.length <= 16, 'Incompatible control audit plan');
      const rows = [];
      for (const route of otherPlan.routes) rows.push(await replay(driver, other, route, context.actionBudget));
      ensure(rows.every(r => r.initialStateHash && r.initialStateHash === rows[0].initialStateHash), 'Creator control routes have different initial states');
      const valid = rows.some(r => r.kind === 'witness') && rows.every(r => r.complete && (r.kind === 'negative' ? !r.success : r.success));
      return {worldDigest: digest(await hostVerificationCall('control_fingerprint', () => driver.fingerprint(clone(other)))), routes: rows, valid, effort: Number.isFinite(measure(rows)) ? measure(rows) : null};
    };
    const control = await replayWorld(plan.neutralizedWorld);
    const previous = adjusting && context.previousWorld ? await replayWorld(context.previousWorld) : null;
    const effort = measure(routes);
    const effectiveChange = !adjusting || Boolean(previous && number(effort) && number(previous.effort) &&
      (context.feedback.reason === 'too_easy' ? effort > previous.effort : effort < previous.effort));
    const neutralizedControlValid = control.valid && number(effort) && number(control.effort) &&
      (controlChanges.length ? control.effort < effort : control.effort === effort);
    const core = {
      witnessValid: witnesses.every(r => r.complete && r.success && r.actions <= context.actionBudget),
      negativeRoutesValid: negatives.every(r => r.complete && !r.success),
      detoursValid: detours.every(r => r.complete && r.success),
      maxWitnessActions: Math.max(...witnesses.map(r => r.actions)), actionBudget: context.actionBudget,
      axisValid: axisValues.every(axis => number(axis.value) && axis.value >= axis.min && axis.value <= axis.max),
      directionValid, layoutTracked: layout.every(entry => entry.value !== undefined),
      effectiveChange: effectiveChange && (!adjusting || axisChanges.length === 1 && context.previousBuildDigest !== buildDigest),
      neutralizedControlValid,
      singleChange: !adjusting || changed.length === 1 && axisChanges.length === 1,
      repairScopeValid: bindingsValid && (!context.previousWorld || isAllowed),
      evidenceComplete: routes.every(r => r.complete) && bindingsValid,
      searchBounded: routes.every(r => r.actions <= context.actionBudget) && routes.length <= 16,
      submissionRemaining: context.maxBuildAttempts - context.attempt,
      attemptedRoutes: routes.length, executedActions: routes.reduce((sum, route) => sum + route.actions, 0)
    };
    if (number(directActions) && number(detourActions)) core.commitmentCost = detourActions - directActions;
    const evidence = {schema: 'creator-host-evidence-v1', buildDigest, designDigest: digest(design), planDigest: digest(plan),
      context: {attempt: context.attempt, maxBuildAttempts: context.maxBuildAttempts, actionBudget: context.actionBudget},
      routes, control, previous, effortMetric: plan.effortMetric, effort, axisValues, changedPaths: changed, layoutDigest: digest(layout), measurements: core,
      notApplicable: adjusting ? [] : ['screening_direction', 'effective_change', 'single_change']};
    report.measurements.core = core;
    report.hostEvidence = evidence;
    report.checks.push({id: 'host_execution_evidence', passed: core.witnessValid && core.negativeRoutesValid && core.detoursValid && core.evidenceComplete,
      message: 'Current-build witness, negative and detour routes must reproduce their declared outcomes'});
    report.checks.push({id: 'host_difficulty_evidence', passed: core.directionValid && core.effectiveChange && core.singleChange && core.neutralizedControlValid && core.repairScopeValid,
      message: 'Difficulty changes must alter replayed effort in the intended direction and pass the neutralized control'});
    report.checks.push({id: 'host_budget_ceiling', passed: core.searchBounded && core.submissionRemaining > 0,
      message: 'Host execution and submission budgets must remain within the frozen limits'});
  } catch (error) {
    report.measurements.core = {};
    report.checks.push({id: 'host_evidence_unavailable', passed: false, message: String(error.message)});
  }
  return report;
}
