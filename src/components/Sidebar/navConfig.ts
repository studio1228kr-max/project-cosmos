// COSMOS sidebar navigation contract.
// This file is the single source of truth for menu tree, route paths, and
// icon mapping. Badge counts here are placeholders — wire real numbers via
// SidebarNav's `badgeOverrides` / `dotOverrides` props once the
// Intake Guardrail / Risk Book endpoints exist.

export type NavBadge = { text: string; tone: 'default' | 'hold' };

export type NavLeaf = {
  type: 'leaf';
  id: string;
  label: string;
  path: string;
  icon: string; // resolved against the ICONS map in SidebarNav.tsx
  badge?: NavBadge;
};

export type NavChild = {
  id: string;
  label: string;
  path: string;
  dot?: 'hold';
};

export type NavGroup = {
  type: 'group';
  id: string;
  label: string;
  icon: string;
  badge?: NavBadge;
  children: NavChild[];
};

export type NavItem = NavLeaf | NavGroup;

export type NavSection = {
  id: string;
  label?: string; // omitted for the standalone Dashboard row
  items: NavItem[];
};

export const navConfig: NavSection[] = [
  {
    id: 'root',
    items: [
      { type: 'leaf', id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: 'LayoutDashboard' },
    ],
  },
  {
    id: 'origination',
    label: 'Origination & execution',
    items: [
      { type: 'leaf', id: 'sourcing', label: 'Sourcing', path: '/sourcing', icon: 'Radar' },
      {
        type: 'leaf', id: 'pipeline', label: 'Pipeline', path: '/pipeline', icon: 'GitBranch',
        badge: { text: '12', tone: 'default' },
      },
      {
        type: 'group', id: 'due-diligence', label: 'Due diligence', icon: 'SearchCheck',
        badge: { text: '2 hold', tone: 'hold' },
        children: [
          { id: 'intake', label: 'Intake', path: '/due-diligence/intake', dot: 'hold' },
          { id: 'diagnostic', label: 'Diagnostic', path: '/due-diligence/diagnostic' },
        ],
      },
      {
        type: 'group', id: 'investment-committee', label: 'Investment committee', icon: 'Landmark',
        children: [
          { id: 'ic-prep', label: 'IC prep', path: '/ic/prep' },
          { id: 'ic-minutes', label: 'IC minutes / conditions', path: '/ic/minutes' },
        ],
      },
      { type: 'leaf', id: 'closing', label: 'Closing & execution', path: '/closing', icon: 'FileSignature' },
    ],
  },
  {
    id: 'portfolio-risk',
    label: 'Portfolio & risk',
    items: [
      {
        type: 'group', id: 'portfolio-management', label: 'Portfolio management', icon: 'Briefcase',
        children: [
          { id: 'positions', label: 'Positions', path: '/portfolio/positions' },
          { id: 'watchlist', label: 'Watchlist / workout', path: '/portfolio/watchlist' },
        ],
      },
      // Flat, not nested under Portfolio Management: the Risk Book (Merton DTD,
      // DSCR scenarios, HHI) is referenced from Diagnostic and IC as well, not
      // only post-close monitoring — so it gets equal nav weight, not a sub-slot.
      { type: 'leaf', id: 'risk-monitoring', label: 'Risk & monitoring', path: '/risk-monitoring', icon: 'ShieldAlert' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      {
        type: 'group', id: 'reporting-analytics', label: 'Reporting & analytics', icon: 'BarChart3',
        children: [
          { id: 'deal-analytics', label: 'Deal-level analytics', path: '/analytics/deal' },
          { id: 'portfolio-analytics', label: 'Portfolio-level analytics', path: '/analytics/portfolio' },
        ],
      },
      {
        type: 'group', id: 'investor-reporting', label: 'Investor reporting', icon: 'Users',
        children: [
          { id: 'fund-overview', label: 'Fund overview', path: '/investor-reporting/fund-overview' },
          { id: 'lp-pipeline', label: 'LP pipeline / IR', path: '/investor-reporting/lp-pipeline' },
          { id: 'lp-reports', label: 'LP reports', path: '/investor-reporting/lp-reports' },
        ],
      },
    ],
  },
  {
    id: 'reference',
    label: 'Reference',
    items: [
      { type: 'leaf', id: 'data-room', label: 'Data room', path: '/data-room', icon: 'FolderLock' },
    ],
  },
];
