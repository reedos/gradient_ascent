import test from 'node:test';
import assert from 'node:assert/strict';
import { architectures, edgeGeometry } from '../src/lib/architecture-models.ts';
import cases from '../../examples/practical_labs/cases.json' with {type:'json'};

test('architecture connections resolve and every node participates in the explanation',()=>{
 for(const [slug,d] of Object.entries(architectures)){
  const seen=new Set<number>();
  for(const edge of d.edges){
   assert.ok(d.nodes[edge.from]&&d.nodes[edge.to],slug);
   assert.ok(edge.label.trim());seen.add(edge.from);seen.add(edge.to);
   assert.doesNotMatch(edgeGeometry(d.nodes[edge.from],d.nodes[edge.to],edge).path,/NaN|undefined/);
  }
  assert.equal(seen.size,d.nodes.length,slug);
 }
});
test('agent architecture distinguishes a finishing path from executing or refusing a tool',()=>{
 const d=architectures['single-agent'];
 assert.ok(d.edges.some(e=>d.nodes[e.from].kind==='model'&&d.nodes[e.to].kind==='end'));
 assert.ok(d.edges.some(e=>d.nodes[e.from].kind==='control'&&d.nodes[e.to].title==='Run allowed tool'));
 assert.ok(d.edges.some(e=>d.nodes[e.from].kind==='control'&&d.nodes[e.to].title==='Pause or refuse'));
});
test('knowledge graph arrows represent relationships rather than workflow control',()=>{
 assert.ok(architectures['knowledge-graphs'].edges.every(e=>e.kind==='data'));
 assert.ok(architectures['knowledge-graphs'].edges.some(e=>e.label==='fits'));
});
test('practical cases have distinct evidence, explicit boundaries, review criteria, and adaptation',()=>{
 assert.equal(new Set(cases.map(c=>c.id)).size,6);
 for(const c of cases){assert.equal(c.steps.length,4);assert.ok(c.data.length);assert.ok(c.rubric.length>=3);assert.ok(c.failure.length>60);assert.ok(c.limits.length>50);assert.ok(c.adapt.length>80);}
});
test('invoice task brief gives output types, not the reference answer values',()=>{
 const c=cases.find(c=>c.id==='invoice-extraction')!;
 assert.doesNotMatch(c.prompt,/54000|55000|30000/);
 assert.match(c.prompt,/integer cents/);
});
