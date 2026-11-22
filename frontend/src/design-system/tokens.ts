/**
 * KNITAU x KeNIP Official Design System Tokens (SSOT)
 * Brand rules restrict UI surfaces strictly to these 5 colors.
 */
export const KNITAU_COLORS = {
  charcoal: '#231F20',
  crimson: '#C82128',
  forestGreen: '#0F6B38',
  gold: '#F4C823',
  white: '#FFFFFF',
} as const;

export type KnitauColorToken = keyof typeof KNITAU_COLORS;

export const SIMILARITY_BADGE_TOKENS = {
  'Strong Match': {
    bg: KNITAU_COLORS.forestGreen,
    text: KNITAU_COLORS.white,
  },
  'Partial Match': {
    bg: KNITAU_COLORS.gold,
    text: KNITAU_COLORS.charcoal,
  },
  'General Mentor': {
    bg: KNITAU_COLORS.charcoal,
    text: KNITAU_COLORS.white,
  },
} as const;
