// Unit tests for src/lib/dates.ts: the one place an ISO date becomes what a reader sees.
import test from 'node:test';
import assert from 'node:assert/strict';
import { usDate } from '../src/lib/dates.ts';

test('a full ISO date prints month first, zero padded', () => {
  assert.equal(usDate('2026-09-18'), '09/18/2026');
  assert.equal(usDate('2023-02-07'), '02/07/2023');
});

test('a month or a year alone keeps the precision it has', () => {
  assert.equal(usDate('2026-09'), '09/2026');
  assert.equal(usDate('1966'), '1966');
});

test('prose, empty and missing values pass through without invention', () => {
  assert.equal(usDate('September 2026'), 'September 2026');
  assert.equal(usDate(''), '');
  assert.equal(usDate(undefined), '');
});
