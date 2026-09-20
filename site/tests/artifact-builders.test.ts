import test from 'node:test';
import assert from 'node:assert/strict';
import { builders, buildArtifact } from '../src/lib/artifact-builders.ts';
test('six distinct tools have specific next steps and usable examples',()=>{
 assert.equal(builders.length,6);
 assert.equal(new Set(builders.map(b=>b.slug)).size,6);
 for(const b of builders){
  assert(b.fields.length>=3 && b.fields.length<=4,b.slug);
  assert(b.next.length>20,b.slug);
  for(const field of b.fields) assert(b.example[field.key] && field.hint && field.example,b.slug);
  const draft=buildArtifact(b,b.example,'https://example.org/site/');
  for(const field of b.fields) assert(draft.includes(b.example[field.key]),b.slug);
  assert(draft.includes('https://example.org/site/'),b.slug);
 }
});
test('custom text survives export without substituting example facts',()=>{
 for(const b of builders){
  const text=buildArtifact(b,{[b.fields[0].key]:'My α requirement: never delete originals'},'https://example.org/site/');
  assert(text.includes('My α requirement: never delete originals'));
  assert(!text.includes(b.example[b.fields[0].key]));
  assert(!text.includes('Not specified'));
  assert(text.includes('not the final artifact itself'));
  assert(!text.includes('## '+b.fields[1].label));
 }
});
