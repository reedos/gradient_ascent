import { test } from 'node:test';
import assert from 'node:assert/strict';
import { lessons } from '../src/lib/learning.ts';
import { conversations, initialConversation, restoreConversation, conversationFiles } from '../src/lib/learning-conversations.ts';

test('every lesson has an English opening, a reply to review, and a corrective follow-up', () => {
  assert.deepEqual(Object.keys(conversations).sort(), lessons.map(l => l.id).sort());
  for (const [id, c] of Object.entries(conversations)) {
    assert.ok(c.starter.length > 30 && !c.starter.startsWith('{'), id);
    assert.ok(c.firstReply && c.review && c.choices[0].example && c.choices[0].feedback, id);
    assert.notEqual(c.firstReply, c.choices[0].reply, `${id} needs a revised reply`);
    const draft = initialConversation(id);
    assert.equal(draft.opening, c.starter);
    assert.equal(draft.sentOpening, null);
    assert.deepEqual(draft.attempts, []);
  }
});
test('edited English messages and notes survive storage and export without being interpreted', () => {
  const id = 'agent-and-harness';
  const draft = { ...initialConversation(id), opening: 'My own phrasing → café', sentOpening: 'My own phrasing → café', followUp: 'Please stop after three searches.', notes: '<script>not executable</script>', attempts: [{ message: 'Please stop after three searches.', branch: 0 }] };
  const restored = restoreConversation(id, JSON.stringify(draft));
  assert.deepEqual(restored, draft);
  const files = conversationFiles(id, restored, 'Fictional source');
  assert.match(files['conversation.md'], /My own phrasing → café/);
  assert.match(files['conversation.md'], /Stopped at three searches/);
  assert.equal(files['notes.md'], draft.notes);
  assert.match(files['README.md'], /No model calls/);
  assert.match(files['README.md'], /not interpreted or graded/);
  assert.ok(Object.keys(files).every(f => !f.endsWith('.json')));
});
test('malformed saved conversations cannot inject unavailable replies or unbounded history', () => {
  const id = 'models-and-context', initial = initialConversation(id);
  for (const raw of ['{', 'null', '[]', JSON.stringify({ ...initial, opening: 1 }), JSON.stringify({ ...initial, sentOpening: 'Start', attempts: [{ message: 'Hello', branch: 99 }] }), JSON.stringify({ ...initial, attempts: [{ message: 'Hello', branch: 0 }] }), JSON.stringify({ ...initial, notes: 'x'.repeat(10001) })]) {
    assert.throws(() => restoreConversation(id, raw));
  }
  assert.deepEqual(restoreConversation(id, null), initial);
  assert.throws(() => initialConversation('unknown'));
});
