import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';

export const DEFAULT_BUDGET_PROFILE = Object.freeze({model: 'claude-opus-5', inputTokenLimit: 1000000,
  prices: {input: 5, output: 25, cacheCreationInput: 6.25, cachedInput: 0.5}});
export class SpendCap extends Error {
  constructor(message) {super(message); this.name = 'SpendCap'; this.retryable = false;}
}
const fields = ['input', 'output', 'cacheCreationInput', 'cachedInput'];
export function costOf(usage, prices) {
  if (!usage || usage.partial || !fields.every(k => Number.isSafeInteger(usage[k]) && usage[k] >= 0)) return null;
  return fields.reduce((sum, k) => sum + usage[k] * prices[k], 0) / 1e6;
}
export class SpendingBudget {
  constructor({limitUsd, profile = DEFAULT_BUDGET_PROFILE, file = null, onChange = () => {}}) {
    if (!Number.isFinite(limitUsd) || limitUsd <= 0) throw Error('Positive spending limit required');
    if (!profile || typeof profile.model !== 'string' || !Number.isSafeInteger(profile.inputTokenLimit) || profile.inputTokenLimit <= 0 ||
      !fields.every(k => Number.isFinite(profile.prices?.[k]) && profile.prices[k] >= 0) || profile.prices.input <= 0 || profile.prices.output <= 0) throw Error('Invalid budget profile');
    if (file && fs.existsSync(file)) throw Error('Budget ledger already exists; use a new run directory');
    this.limit = limitUsd; this.profile = structuredClone(profile); this.file = file; this.onChange = onChange;
    this.usd = 0; this.calls = 0; this.uncertain = 0; this.stopped = false; this.active = new Map(); this.waiters = new Set();
    this.save();
  }
  snapshot() {
    return {schema: 'trinity-spending-v2', usd: this.usd, reservedUsd: [...this.active.values()].reduce((a,b)=>a+b,0),
      limitUsd: this.limit, calls: this.calls, uncertainAttempts: this.uncertain, stopped: this.stopped, profile: this.profile,
      pending: [...this.active].map(([attemptId, upperBoundUsd])=>({attemptId, upperBoundUsd}))};
  }
  save() {
    const state = this.snapshot();
    if (this.file) {
      fs.mkdirSync(path.dirname(this.file), {recursive:true});
      const tmp = this.file + '.tmp', fd = fs.openSync(tmp, 'w', 0o600);
      try {fs.writeFileSync(fd, JSON.stringify(state)+'\n');fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
      fs.renameSync(tmp, this.file);
    }
    this.onChange(state);
  }
  wake() {for(const resolve of this.waiters)resolve();this.waiters.clear();}
  async reserve({model, maxTokens, signal}) {
    if (model !== this.profile.model || !Number.isSafeInteger(maxTokens) || maxTokens <= 0) throw new SpendCap('No matching spending profile for this request');
    const p = this.profile.prices;
    const amount = (this.profile.inputTokenLimit * Math.max(p.input, p.cacheCreationInput, p.cachedInput) + maxTokens * p.output) / 1e6;
    for (;;) {
      if (signal?.aborted) throw new SpendCap('Request cancelled before budget reservation');
      if (this.stopped) throw new SpendCap('Spending is stopped; inspect the budget ledger');
      const reserved = this.snapshot().reservedUsd;
      if (this.usd + reserved + amount <= this.limit) {
        const id = randomUUID();this.active.set(id,amount);this.calls++;
        try {this.save();} catch(error) {this.stopped=true;this.wake();throw error;}
        return id;
      }
      if (!this.active.size || this.usd + amount > this.limit) {
        this.stopped=true;this.save();this.wake();
        throw new SpendCap('Remaining budget cannot reserve the full request upper bound ($'+amount.toFixed(2)+')');
      }
      await new Promise(resolve=>{
        const done=()=>{this.waiters.delete(done);signal?.removeEventListener('abort',done);resolve();};
        this.waiters.add(done);signal?.addEventListener('abort',done,{once:true});
        if(signal?.aborted)done();
      });
    }
  }
  settle(id, usage) {
    if(!this.active.has(id))throw Error('Unknown or already settled budget reservation');
    const bound=this.active.get(id), cost=costOf(usage,this.profile.prices);
    this.active.delete(id);
    if(cost===null){this.usd+=bound;this.uncertain++;this.stopped=true;}
    else {this.usd+=cost;if(cost>bound || this.usd+this.snapshot().reservedUsd>this.limit)this.stopped=true;}
    try{this.save();}finally{this.wake();}
    if(cost!==null && cost>bound)throw new SpendCap('Provider usage exceeded the configured token/price bound; spending stopped');
  }
}
