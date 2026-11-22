/**
 * Canonical KNITAU RBAC Matrix (Front-End View Mirror of backend/apps/common/permissions.py)
 * NOTE: Backend HasKnitauRole always remains the authoritative security enforcement layer.
 */
export type KnitauRole = 'intern' | 'employer' | 'institution' | 'admin';

export type AdminSubRole =
  | 'executive'
  | 'case_officer'
  | 'finance_officer'
  | 'chapter_rep';

export interface AuthSessionUser {
  id: string;
  fullName: string;
  role: KnitauRole;
  adminSubRole?: AdminSubRole;
}

export interface RouteAccessRule {
  roles: readonly KnitauRole[];
  adminSubRoles?: readonly AdminSubRole[];
}

export function canAccessRoute(
  user: AuthSessionUser | null,
  rule: RouteAccessRule,
): boolean {
  if (!user) return false;
  if (!rule.roles.includes(user.role)) return false;

  if (user.role === 'admin' && rule.adminSubRoles && rule.adminSubRoles.length > 0) {
    return Boolean(user.adminSubRole && rule.adminSubRoles.includes(user.adminSubRole));
  }

  return true;
}

export const MODULE_ACCESS_RULES = {
  globalCorridor: { roles: ['intern', 'admin'] },
  welfareFinanceApproval: {
    roles: ['admin'],
    adminSubRoles: ['executive', 'finance_officer'],
  },
  grievanceCaseDesk: {
    roles: ['admin'],
    adminSubRoles: ['executive', 'case_officer'],
  },
  diasporaMentorOversight: {
    roles: ['admin'],
    adminSubRoles: ['executive', 'chapter_rep'],
  },
  exitManagement: { roles: ['intern', 'employer', 'admin'] },
} as const satisfies Record<string, RouteAccessRule>;
