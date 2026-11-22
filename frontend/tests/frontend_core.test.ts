import assert from 'node:assert/strict';
import test from 'node:test';
import { KNITAU_COLORS } from '../src/design-system/tokens.ts';
import { MODULE_ACCESS_RULES, canAccessRoute } from '../src/lib/auth/rbac.ts';
import { buildQueuedAction, createIdempotencyKey } from '../src/lib/offline/idempotency.ts';

test('RBAC matrix isolates admin sub-roles strictly', () => {
  const financeAdmin = {
    id: 'u-1',
    fullName: 'Finance Officer',
    role: 'admin' as const,
    adminSubRole: 'finance_officer' as const,
  };
  const intern = {
    id: 'u-2',
    fullName: 'Intern User',
    role: 'intern' as const,
  };

  assert.equal(canAccessRoute(financeAdmin, MODULE_ACCESS_RULES.welfareFinanceApproval), true);
  assert.equal(canAccessRoute(financeAdmin, MODULE_ACCESS_RULES.grievanceCaseDesk), false);
  assert.equal(canAccessRoute(intern, MODULE_ACCESS_RULES.globalCorridor), true);
  assert.equal(canAccessRoute(intern, MODULE_ACCESS_RULES.welfareFinanceApproval), false);
});

test('Offline queued actions attach unique idempotency keys', () => {
  const k1 = createIdempotencyKey();
  const k2 = createIdempotencyKey();
  assert.notEqual(k1, k2);

  const queued = buildQueuedAction('/welfare/claims/', 'POST', { amount: 1500 });
  assert.ok(queued.idempotencyKey.length > 10);
  assert.equal(queued.method, 'POST');
});

test('Design tokens strictly match the 5 KNITAU brand colors', () => {
  assert.deepEqual(Object.values(KNITAU_COLORS).sort(), [
    '#0F6B38',
    '#231F20',
    '#C82128',
    '#F4C823',
    '#FFFFFF',
  ]);
});
