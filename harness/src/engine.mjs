import {hostVerificationCall} from './host-verification.mjs';
import {screeningPolicy} from './screening-policy.mjs';
import {runCreatorCoding, creatorSourceDigest} from './creator-coding.mjs';
import {completeTraining} from './protocol-state.mjs';
import {freezeExplorationInstances} from './exploration-plan.mjs';
import {mergeRoutingCandidates} from './routing-candidates.mjs';
import {capabilityDefinitions, capabilityDescription} from './capabilities.mjs';
import {verifyTerminalReceipt} from './receipts.mjs';
import {scoreSummary, usageReport} from './metrics.mjs';
import {clone, digest, ensure, compose, snapshot, buildTree, validateConfig} from './core.mjs';
import {runBatch, screeningDecision, chooseInheritance, performanceDecision, completions, matchedInstances} from './explorer.mjs';
import {emptyCreator, retainCreatorChoice, auditCreator, consolidateCreator, creatorEvolutionChoices, validateArtifact} from './creator.mjs';
import {buildNodeModuleGenerationRequest, retainNodeModuleGeneration} from './generation.mjs';

export class Trinity {
  constructor({config, agent, driver, store}) {
    this.config = validateConfig(clone(config));
    this.agent = agent;
    this.driver = driver;
    this.store = store;
    const initial = clone(config.creatorBase ?? emptyCreator());
    this.creatorBase = {modules: initial.modules, skills: []};
    this.creatorNodeSkills = new Map(Object.entries(clone(config.creatorNodeSkills ?? {})));
    for (const skill of initial.skills) {
      const list = this.creatorNodeSkills.get(skill.node) ?? [];
      list.push(skill);
      this.creatorNodeSkills.set(skill.node, list);
    }
    this.nodes = new Map();
    this.baseline = [];
    this.creatorMeasurements = [];
  }
  async initialize() {
    const config = this.config;
    ensure(config.capabilityMode !== 'induced', 'Direct taxonomy induction is retired; run Stage 2 analyse/induce/assign and prepare a fixed_tree config');
    const plans = [];
    for (const task of config.capabilityMode === 'fixed_tree' ? [] : config.trainingTasks) {
      const world = await hostVerificationCall('benchmark_loading', () => this.driver.loadBenchmark(clone(task)));
      const plan = await freezeExplorationInstances({driver: this.driver, world, store: this.store, taskId: task.id, trials: config.validationTrials});
      plans.push({task, world, plan});
    }
    if (plans.length) this.store.write('initial-instances.json', {schema: 'trinity-exploration-plan-v1', plans: plans.map(({plan}) => plan)});
    for (const {task, world, plan} of plans) {
      const rows = await runBatch({agent: this.agent, driver: this.driver, store: this.store, world, taskId: task.id, benchmarkId: task.benchmarkId ?? task.id, split: 'train', instances: plan.instances, initialStateHashes: plan.initialStateHashes, instancePlan: plan.event, modules: [], budget: config.actionBudget, phase: 'initial_training_exploration', node: 'root'}, config.validationTrials);
      ensure(!rows.some(row => row.technicalFailure), 'Initial exploration failed; inspect the recorded run');
      this.baseline.push({task: clone(task), rows});
    }
    if (config.capabilityMode === 'fixed_tree') {
      for (const task of [...config.trainingTasks, ...(config.baselineTasks ?? [])]) {
        const rows = config.initialFeedback?.[task.id];
        ensure(Array.isArray(rows) && rows.length > 0, 'Fixed tree requires verified initial feedback for ' + task.id);
        for (const row of rows) {
          ensure(row.taskId === task.id && row.split === 'train' && row.harnessId === snapshot([]).id && row.phase === 'initial_training_exploration', 'Initial feedback must be training H0 evidence');
          verifyTerminalReceipt(row, {episodeId: row.episodeId, decisionId: null, harnessId: snapshot([]).id, worldDigest: row.worldDigest, budget: row.terminalReceipt?.receipt.budget});
        }
        this.baseline.push({task: clone(task), rows: clone(rows)});
      }
    }
    ensure(['fixed_fixture', 'fixed_tree'].includes(config.capabilityMode), 'Unknown capability mode');
    const {taxonomy, assignments} = config;
    this.capabilities = capabilityDefinitions(taxonomy, config.capabilityDefinitions, {required: config.capabilityMode === 'fixed_tree'});
    this.tree = buildTree(taxonomy, assignments, config.trainingTasks.map(task => task.id)).map(node => ({...node,
      ...(this.capabilities ? {capabilityDefinitions: node.requirements.map(id => clone(this.capabilities[id]))} : {})}));
    this.retention = new Map(this.tree.map(node => [node.id, {
      node: node.id, endpointTaskIds: clone(node.endpointTasks),
      retainHarness: node.endpointTasks.length > 0,
      reason: node.endpointTasks.length ? 'direct_training_tasks' : 'no_direct_training_tasks',
      children: this.tree.filter(child => child.parent === node.id).map(child => child.id)
    }]));
    for (const [node, skills] of this.creatorNodeSkills) {
      ensure(this.tree.some(row => row.id === node) && Array.isArray(skills), 'Creator skills require an existing owner node');
      ensure(new Set(skills.map(skill => skill.id)).size === skills.length, 'Duplicate node skill ID');
      for (const skill of skills) ensure(validateArtifact('skill', skill).node === node, 'Creator skill owner mismatch');
    }
    for (const node of this.tree) {
      const feedback = this.baseline.filter(entry => node.tasks.includes(entry.task.id)).flatMap(entry => entry.rows);
      this.nodes.set(node.id, {inherited: [], local: [], initialFeedback: clone(feedback), feedback: clone(feedback),
        ...(this.retention.get(node.id).retainHarness ? {snapshots: []} : {})});
    }
    this.store.write('tree.json', {taxonomy, assignments, capabilityDefinitions: this.capabilities, nodes: this.tree, mode: config.capabilityMode});
    this.store.write('harness-retention.json', {schema: 'trinity-harness-retention-v1',
      policy: 'direct-training-endpoints', nodes: [...this.retention.values()]});
    this.store.record('topology_frozen', {digest: digest(this.tree), nodes: this.tree.length});
  }
  options(world, modules, node, phase) {
    return {agent: this.agent, driver: this.driver, store: this.store, world, modules, budget: this.config.actionBudget, phase, node};
  }
  checkpoint(iteration, summary) {
    const explorerNodes = {}, intermediateNodes = {};
    for (const [id, state] of this.nodes) {
      const target = this.retention.get(id).retainHarness ? explorerNodes : intermediateNodes;
      target[id] = clone(state);
    }
    return {schema: 'trinity-training-checkpoint-v2', iteration, creatorBase: this.creatorBase,
      creatorNodeSkills: Object.fromEntries(this.creatorNodeSkills), explorerNodes, intermediateNodes, summary};
  }
  async inherit(node, iteration) {
    const state = this.nodes.get(node.id);
    if (!node.parent) return;
    const parent = this.nodes.get(node.parent), candidate = compose(parent.inherited, parent.local);
    if (snapshot(candidate).id === snapshot(state.inherited).id) return;
    const oldRows = [], newRows = [];
    for (const taskId of node.tasks) {
      const task = this.config.trainingTasks.find(value => value.id === taskId), world = await hostVerificationCall('benchmark_loading', () => this.driver.loadBenchmark(clone(task)));
      const instances = await matchedInstances(this.driver, world, this.config.validationTrials);
      oldRows.push(...await runBatch({...this.options(world, compose(state.inherited, state.local), node.id, 'inheritance_previous'), taskId, benchmarkId: taskId, split: 'train', instances}, this.config.validationTrials));
      newRows.push(...await runBatch({...this.options(world, compose(candidate, state.local), node.id, 'inheritance_candidate'), taskId, benchmarkId: taskId, split: 'train', instances}, this.config.validationTrials));
    }
    const decision = chooseInheritance(oldRows, newRows);
    this.store.record('inheritance_decision', {iteration, node: node.id, parent: node.parent, previous: snapshot(state.inherited).id, candidate: snapshot(candidate).id, ...decision});
    if (decision.accepted) state.inherited = clone(candidate);
  }
  async prepareWorld(node, iteration, start, creator, allUpdates) {
    const frozenScreening = screeningPolicy(this.config.screening);
    this.store.record('screening_policy_frozen', {node: node.id, iteration, policy: frozenScreening});
    const state = this.nodes.get(node.id);
    const design = await this.agent.ask('evolver_design', {
      node, iteration, feedback: state.feedback,
      publicTaskSpecifications: this.config.trainingTasks.filter(task => node.tasks.includes(task.id)),
      designContract: this.driver.designContract, screening: frozenScreening
    }, this.driver.designContract);
    await hostVerificationCall('design_validation', () => this.driver.validateDesign(clone(design), clone(node)));
    const designDigest = this.store.put(design);
    let feedback = null, previousWorld = null, previousBuildDigest = null;
    const screeningHistory = [];
    for (let attempt = 0; attempt < this.config.maxBuildAttempts; attempt++) {
      const coding = await runCreatorCoding({agent: this.agent, driver: this.driver, store: this.store,
        node, iteration, attempt, design, creator, feedback, previousWorld, previousBuildDigest,
        maxBuildAttempts: this.config.maxBuildAttempts, actionBudget: this.config.actionBudget, screening: frozenScreening, settings: this.config.creatorCoding});
      const {world, buildDigest, inspection} = coding;
      for (const [kind, values] of Object.entries(inspection.measurements)) this.creatorMeasurements.push({kind, current: true, values: clone(values)});
      ensure(inspection.buildDigest === buildDigest && Array.isArray(inspection.checks) && inspection.checks.length > 0 && inspection.checks.every(check => typeof check.passed === 'boolean') && inspection.measurements && typeof inspection.measurements === 'object', 'Invalid host verification report');
      const audits = auditCreator(creator, inspection, buildDigest);
      const failures = [...inspection.checks.filter(check => !check.passed), ...audits.filter(audit => audit.verdict !== 'pass')];
      const report = {node: node.id, iteration, attempt, designDigest, buildDigest, inspection, audits};
      const reportId = this.store.record('world_verified', report);
      if (failures.length) {
        const failureId = this.store.record('verified_world_failure', {reportId, node: node.id, failures});
        const availableChoices = creatorEvolutionChoices.filter(action => !action.startsWith('revise_') || creator[action.endsWith('_module') ? 'modules' : 'skills'].length > 0);
        const choice = await this.agent.ask('creator_evolve', {node, iteration, creator: clone(creator), failures, failureIds: [failureId], buildDigest, measurements: clone(inspection.measurements), measurementKinds: Object.keys(inspection.measurements), availableChoices}, {
          choice: availableChoices, reason: 'Explanation of the selected change', evidenceRefs: ['Verified failure ID'], baseVersion: 'Existing version for revision; null for creation', artifact: 'Exactly one required module or skill artifact'
        });
        this.store.record('creator_proposal_saved', {node: node.id, iteration, proposalDigest: this.store.put(choice)});
        const result = retainCreatorChoice(creator, choice, node.id, [failureId]);
        creator = result.state;
        this.creatorNodeSkills.set(node.id, clone(creator.skills));
        this.store.write('creator-node-skills.json', Object.fromEntries(this.creatorNodeSkills));
        if (result.accepted && result.update.kind === 'module') allUpdates.push(result.update);
        this.store.record(result.accepted ? 'creator_choice_applied' : 'creator_choice_rejected', {node: node.id, iteration, accepted: result.accepted, choice: choice.choice, update: result.update, reason: choice.reason ?? null, diagnostics: result.diagnostics});
        const verificationFailure = {reportId, failures, evolution: {accepted: result.accepted, diagnostics: result.diagnostics}};
        if (feedback?.kind === 'difficulty_adjustment') {
          feedback = {...feedback, verificationFailure};
        } else {
          previousWorld = clone(world);
          previousBuildDigest = buildDigest;
          feedback = {kind: 'verification_failure', ...verificationFailure};
        }
        continue;
      }
      let screenOptions = this.options(world, start.modules, node.id, 'screening');
      if (typeof this.driver.screeningInstanceManifest === 'function') {
        const driver = this.driver;
        const planDriver = {
          instanceManifest: driver.screeningInstanceManifest.bind(driver),
          initialState: driver.initialState.bind(driver), reset: driver.reset.bind(driver),
          fingerprint: driver.fingerprint.bind(driver), ...(driver.close ? {close: driver.close.bind(driver)} : {})
        };
        const plan = await freezeExplorationInstances({driver: planDriver, world, trials: frozenScreening.trials, store: this.store, taskId: node.id});
        this.store.record('screening_instances_frozen', {node: node.id, iteration, buildDigest, planDigest: this.store.put(plan)});
        screenOptions = {...screenOptions, instances: plan.instances, initialStateHashes: plan.initialStateHashes, instancePlan: plan.event};
      }
      const screen = await runBatch(screenOptions, frozenScreening.trials);
      const decision = screeningDecision(screen, frozenScreening);
      screeningHistory.push({attempt, buildDigest, axes: clone(inspection.hostEvidence?.axisValues ?? []), ...decision});
      const screeningId = this.store.record('screening_decision', {node: node.id, iteration, buildDigest, harnessId: start.id, ...decision, episodes: screen.map(row => row.episodeId)});
      ensure(await creatorSourceDigest(coding.workspace) === coding.sourceDigest, 'Creator source changed during screening');
      ensure(digest(await hostVerificationCall('world_fingerprint', () => this.driver.fingerprint(clone(world)))) === buildDigest, 'World mutated during screening');
      if (decision.accepted) return {world: clone(world), design, designDigest, buildDigest, creator, screeningId, workspace: coding.workspace, sourceDigest: coding.sourceDigest};
      if (decision.reason === 'technical_failure') throw Error('Technical screening failure; environment difficulty is not inferred');
      previousWorld = clone(world);
      previousBuildDigest = buildDigest;
      feedback = {kind: 'difficulty_adjustment', ...decision, screeningId, history: clone(screeningHistory)};
    }
    this.store.record('world_admission_exhausted', {node: node.id, iteration, maxBuildAttempts: this.config.maxBuildAttempts, harnessId: start.id});
    throw Error('No world reached the predefined screening band at node ' + node.id);
  }
  async run() {
    await this.initialize();
    const summary = [];
    for (let iteration = 1; iteration <= this.config.iterations; iteration++) {
      const creatorAtNode = new Map(), updates = [];
      for (const node of this.tree) {
        this.agent.scope = {node: node.id, iteration};
        const usageStart = this.agent.calls?.length ?? 0;
        await this.inherit(node, iteration);
        const state = this.nodes.get(node.id), start = snapshot(compose(state.inherited, state.local));
        const retainHarness = this.retention.get(node.id).retainHarness;
        if (retainHarness) this.store.put(start);
        const inheritedCreator = node.parent ? creatorAtNode.get(node.parent) : this.creatorBase;
        const creator = {modules: clone(inheritedCreator.modules), skills: clone(this.creatorNodeSkills.get(node.id) ?? [])};
        const admitted = await this.prepareWorld(node, iteration, start, creator, updates);
        creatorAtNode.set(node.id, {modules: clone(admitted.creator.modules), skills: []});
        this.creatorNodeSkills.set(node.id, clone(admitted.creator.skills));
        ensure(snapshot(compose(state.inherited, state.local)).id === start.id, 'Screening and training Harness snapshots differ');
        this.store.record('training_started', {node: node.id, iteration, harnessId: start.id, screeningId: admitted.screeningId, buildDigest: admitted.buildDigest});
        const instances = await matchedInstances(this.driver, admitted.world, this.config.trainingTrials);
        const trajectories = await runBatch({...this.options(admitted.world, start.modules, node.id, 'local_training'), instances}, this.config.trainingTrials);
        ensure(!trajectories.some(row => row.technicalFailure), 'Local execution failed; no evolution is admitted');
        const context = {
          mode: 'training', node: node.id, capabilityDefinitions: clone(node.capabilityDefinitions ?? []), boundary: trajectories.length, inheritedRegistry: start.modules,
          validationPolicies: clone(this.config.validationPolicies ?? {}),
          feedback: [...new Map([...state.initialFeedback, ...state.feedback].map(row => [row.episodeId, clone(row)])).values()],
          ...(state.moduleValidationFeedback ? {hostValidationFeedback: clone(state.moduleValidationFeedback)} : {}),
          trajectories: trajectories.map((row, index) => ({round: index + 1, events: row.events}))
        };
        const request = buildNodeModuleGenerationRequest(context);
        const proposal = await this.agent.ask('evolver_modules', {...request.packet, iteration, design: admitted.design}, request.schema);
        this.store.record('explorer_proposal_saved', {node: node.id, iteration, proposalDigest: this.store.put(proposal)});
        let hostTests;
        try {hostTests = this.driver.moduleTests ? await this.driver.moduleTests(node.id) : {};}
        catch {throw new Error('Private host test loading failed');}
        const result = await retainNodeModuleGeneration(context, proposal, {hostTests});
        const candidateLocal = result.registry.filter(module => module.targetCapabilityNodeId === node.id);
        const candidate = result.accepted ? snapshot(compose(state.inherited, candidateLocal)) : null, candidateAudit = result.audit;
        let decision;
        if (result.accepted) {
          state.local = clone(candidateLocal);
          this.store.record('explorer_candidate_retained', {node: node.id, iteration, audit: candidateAudit,
            candidateHarnessId: candidate.id, retainedAsHarness: retainHarness,
            candidateDigest: retainHarness ? this.store.put(candidate) : null});
        } else {
          this.store.record('explorer_candidate_rejected', {node: node.id, iteration, audit: candidateAudit, retainedHarnessId: start.id});
        }
        ensure(await creatorSourceDigest(admitted.workspace) === admitted.sourceDigest, 'Creator source changed after submission');
        ensure(digest(await hostVerificationCall('world_fingerprint', () => this.driver.fingerprint(clone(admitted.world)))) === admitted.buildDigest, 'World changed during local training');
        const validationHarness = candidate ?? start;
        ensure(validationHarness.id === snapshot(compose(state.inherited, state.local)).id, 'Retained Harness differs from the active registry');
        const evaluation = await runBatch({...this.options(admitted.world, validationHarness.modules, node.id, 'training_side_evaluation'), instances}, this.config.validationTrials);
        ensure(await creatorSourceDigest(admitted.workspace) === admitted.sourceDigest, 'Creator source changed after submission');
        ensure(digest(await hostVerificationCall('world_fingerprint', () => this.driver.fingerprint(clone(admitted.world)))) === admitted.buildDigest, 'World changed during training-side evaluation');
        {
          decision = performanceDecision(trajectories, evaluation);
          if (!result.accepted) decision = {...decision, accepted: false, reason: 'host_validation_rejected'};
          this.store.record(result.accepted ? 'explorer_update_accepted' : 'explorer_update_rejected', {node: node.id, iteration, ...decision, audit: candidateAudit, candidateHarnessId: candidate?.id ?? null, retainedSnapshot: validationHarness.id});
        }
        const final = validationHarness;
        const reusedSnapshot = final.id === start.id;
        state.feedback = [...trajectories, ...evaluation];
        state.moduleValidationFeedback = {
          node: node.id, iteration, proposalDigest: digest(proposal), priorCandidate: clone(proposal),
          accepted: result.accepted,
          validation: clone(candidateAudit),
          retainedHarnessId: final.id,
          retainedModules: final.modules.map(module => ({moduleId: module.moduleId, version: module.version, targetCapabilityNodeId: module.targetCapabilityNodeId})),
          trainingEpisodeIds: trajectories.map(row => row.episodeId)
        };
        if (retainHarness) {
          state.snapshots.push({iteration, start: start.id, final: final.id, reusedSnapshot, world: admitted.buildDigest});
        }
        const row = {node: node.id, iteration, screeningHarnessId: start.id, trainingStartHarnessId: start.id, validationHarnessId: validationHarness.id, candidateHarnessId: candidate?.id ?? null, finalHarnessId: final.id, updateAccepted: decision.accepted, updateReason: decision.reason, trainingCompletions: completions(trajectories), evaluationCompletions: completions(evaluation), trials: trajectories.length, trainingTrials: trajectories.length, evaluationTrials: evaluation.length, localModules: state.local.length};
        row.trainingScores = scoreSummary(trajectories);
        row.validationScores = scoreSummary(evaluation);
        row.usage = this.agent.usageSince?.(usageStart) ?? null;
        row.retainedAsHarness = retainHarness;
        row.reusedSnapshot = reusedSnapshot;
        row.endpointTaskIds = clone(node.endpointTasks);
        summary.push(row);
        this.store.record('node_exported', {...row, stateKind: retainHarness ? 'harness_node' : 'intermediate_training_state',
          childNodes: clone(this.retention.get(node.id).children), stateDigest: this.store.put(state)});
      }
      this.agent.scope = {iteration, node: null};
      const preliminary = consolidateCreator(this.creatorBase, updates, [], {autoMerge: false, measurements: this.creatorMeasurements});
      const proposal = await this.agent.ask('creator_consolidate', {iteration, registry: preliminary.state, provenance: preliminary.provenance}, {groups: [{kind: 'module', ids: ['Artifact ID'], newId: 'New ID'}]});
      ensure(Array.isArray(proposal.groups), 'Consolidation groups required');
      let consolidated;
      try {
        ensure(proposal.groups.every(group => group.kind === 'module'), 'Shared Creator consolidation accepts modules only');
        consolidated = updates.length ? consolidateCreator(preliminary.state, [], proposal.groups, {measurements: this.creatorMeasurements}) : preliminary;
      }
      catch (error) {
        this.store.record('creator_merge_rejected', {iteration, reason: error.message});
        consolidated = updates.length ? consolidateCreator(preliminary.state, [], [], {measurements: this.creatorMeasurements}) : preliminary;
      }
      this.creatorBase = consolidated.state;
      this.store.record('creator_base_consolidated', {iteration, baseDigest: this.store.put(this.creatorBase), provenance: [...preliminary.provenance, ...consolidated.provenance]});
      this.store.write('checkpoint-' + iteration + '.json', this.checkpoint(iteration, summary));
    }
    const automaticExcluded = [...this.retention.values()].filter(node => !node.retainHarness).map(node => node.node);
    const excluded = [...new Set([...automaticExcluded, ...(this.config.routingExcludedNodes ?? [])])];
    const candidates = mergeRoutingCandidates(this.tree.filter(node => !excluded.includes(node.id)).map(node => {
      const state = this.nodes.get(node.id), final = snapshot(compose(state.inherited, state.local));
      return {node: node.id, snapshotId: final.id, modules: final.modules, endpointTaskIds: clone(node.endpointTasks),
        description: capabilityDescription(node.requirements, this.capabilities)};
    }));
    this.store.write('routing-candidates.json', {schema: 'trinity-routing-candidates-v1', excludedNodes: excluded, candidates});
    const result = {mode: this.config.mode, sourcePaper: 'arXiv:2610.36077v1', screening: this.config.screening, creatorEvolution: [...creatorEvolutionChoices], nodes: this.tree.length, iterations: this.config.iterations, summary, creatorBase: this.creatorBase, creatorNodeSkills: Object.fromEntries(this.creatorNodeSkills), benchmarkPerformanceClaim: false, accounting: usageReport(this.agent.calls ?? [])};
    this.store.write('summary.json', result);
    completeTraining({store: this.store, config: this.config, baseline: this.baseline});
    return result;
  }
}
