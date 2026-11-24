import {readResponseLog} from '../../../vendor/resume-response-log.mjs';
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
const source=process.env.SOON_RESUME_SOURCE;
const lines=p=>fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const requests=source?lines(path.join(source,'api-requests.jsonl')):[];
const responses=new Map(readResponseLog(source,requests).map(r=>[r.captureId,r]));
let cursor=0;
export function resumeElapsedMs(){
 if(!source)return 0;
 const file=fs.readdirSync(path.join(source,'episodes'))[0];const rows=lines(path.join(source,'episodes',file,'record.jsonl'));
 const resultFile=path.join(source,'..','results.json');
 const result=fs.existsSync(resultFile)?JSON.parse(fs.readFileSync(resultFile,'utf8')).results?.find(r=>r.episode===path.basename(source)):null;
 return Math.max(Number(rows.at(-1).observation.publicText.match(/Time used: (\d+) s/)?.[1]??0),result?.seconds??0)*1000;
}
export function replayResponse(request,runDir){
 if(!source)return null;
 if(cursor>=requests.length)return null;
 const previous=requests[cursor];
 assert.deepEqual(request,previous.request,'Restored API request differs at index '+cursor);
 const response=responses.get(previous.captureId);
 const event={index:cursor,captureId:previous.captureId,exactRequestMatch:true,cachedResponse:!!response,requestSha256:crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex')};
 fs.appendFileSync(path.join(runDir,'resume-checks.jsonl'),JSON.stringify(event)+'\n');cursor++;
 if(response)return response;
 if(cursor!==requests.length)throw Error('Missing response inside archived prefix');
 fs.writeFileSync(path.join(runDir,'resume-verified.json'),JSON.stringify({passed:true,source,requests:cursor,replayedResponses:cursor-1,networkCallsBeforeBoundary:0},null,2));
 if(process.env.SOON_RESUME_VERIFY_ONLY==='1')throw Error('OFFLINE_RESUME_VERIFIED_NO_NETWORK');
 return null;
}
