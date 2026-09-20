import test from 'node:test';
import assert from 'node:assert/strict';
import cases from '../src/data/concept-walkthroughs.json' with {type:'json'};
import perspectives from '../src/data/walkthrough-perspectives.json' with {type:'json'};
import guides from '../src/data/walkthrough-guides.json' with {type:'json'};
import artifacts from '../src/data/walkthrough-artifacts.json' with {type:'json'};
import taxonomy from '../../content/taxonomy.json' with {type:'json'};
import {approvalKey,canDeliver,audienceLabels} from '../src/lib/walkthrough.ts';

test('priority records belong to real audience cases and cover the whole six-stage demonstration',()=>{
 const available=new Set([...cases,...perspectives].map(e=>`${e.slug}:${e.audience}`));
 assert.deepEqual(Object.keys(artifacts).map(k=>k.split(':')[0]).sort(),['evals','human-in-the-loop','prompt-engineering','rag','single-agent','workflow-graphs']);
 for(const [key,records] of Object.entries(artifacts)){
  assert.ok(available.has(key),`${key}: orphaned teaching records`);
  assert.equal(records.length,6);
  assert.equal(new Set(records.map(r=>r.body)).size,6,`${key}: repeated record instead of progressing work`);
  assert.ok(records.every(r=>r.name&&r.change.length>20));
 }
 const booking=cases.find(c=>c.slug==='single-agent')!;
 assert.match(booking.outcome,/if this request/);
 assert.match(artifacts['single-agent:business'][3].body,/if this request/);
});

test('every concept has distinct overview, choices, recovery and transfer guidance',()=>{
 const slugs=new Set([...cases,...perspectives].map(c=>c.slug));
 assert.deepEqual(Object.keys(guides).sort(),[...slugs].sort());
 for(const field of ['overview','assumptions','choices','recovery','transfer'] as const){
   const entries=Object.values(guides).map(g=>g[field]);
   assert.equal(new Set(entries).size,slugs.size,`${field}: generic duplicated guidance`);
   assert.ok(entries.every(e=>e.trim().length>60),`${field}: missing explanation`);
 }
});

test('every taxonomy concept and thread has an authored walkthrough, or the dedicated DUT lesson',()=>{
 const expected=[...taxonomy.tiers.flatMap(t=>t.pages.map(p=>p.slug)),...taxonomy.tracks.flatMap(t=>[t.id,...(t.pages??[]).map(p=>p.slug)]),...taxonomy.threads.map(t=>t.id)].filter(s=>s!=='agent-harness');
 assert.deepEqual(cases.map(c=>c.slug).sort(),expected.sort());
 for(const c of cases){
   assert.ok(audienceLabels[c.audience]);
   for(const field of ['prompt','inputs','action','outcome','change','changedOutcome','question','correct','wrong','explanation','verify'] as const) assert.ok(c[field].trim().length>10,`${c.slug}: ${field}`);
   assert.notEqual(c.correct,c.wrong);assert.notEqual(c.outcome,c.changedOutcome);
 }
});
test('perspectives are unique, authored, and cover all three audiences on 20 selected concepts',()=>{
 const all=[...cases,...perspectives];
 const keys=all.map(c=>`${c.slug}:${c.audience}`);
 assert.equal(new Set(keys).size,keys.length);
 const groups=new Map<string,Set<string>>();
 groups.set('agent-harness',new Set(['engineering']));
 for(const c of all){
   assert.ok(audienceLabels[c.audience]);
   if(!groups.has(c.slug))groups.set(c.slug,new Set());
   groups.get(c.slug)!.add(c.audience);
 }
 assert.equal([...groups.values()].filter(s=>s.size===3).length,20);
 for(const c of perspectives){
   assert.ok(c.explanation.length>30);assert.ok(c.verify.length>30);
   for(const other of all.filter(e=>e.slug===c.slug&&e.audience!==c.audience)){
     assert.notEqual(c.prompt,other.prompt);assert.notEqual(c.inputs,other.inputs);
     assert.notEqual(c.changedOutcome,other.changedOutcome);assert.notEqual(c.question,other.question);
   }
 }
});
test('delivery requires approval of the exact version, content, and recipients and cannot repeat',()=>{
 const key=approvalKey(1,'Report A','Team');
 assert.equal(canDeliver(key,null,[]),false);
 assert.equal(canDeliver(key,key,[]),true);
 for(const changed of [approvalKey(2,'Report A','Team'),approvalKey(1,'Report B','Team'),approvalKey(1,'Report A','External')]) assert.equal(canDeliver(changed,key,[]),false);
 assert.equal(canDeliver(key,key,[key]),false);
});
