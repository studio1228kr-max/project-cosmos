export type NavBadge = { text: string; tone?: "default" | "hold" };

export type NavLeaf = {
  type: "leaf";
  id: string;
  label: string;
  path: string;
  icon: string;
  badge?: NavBadge;
};

export type NavChild = {
  id: string;
  label: string;
  path: string;
  dot?: "hold";
};

export type NavGroup = {
  type: "group";
  id: string;
  label: string;
  icon: string;
  children: NavChild[];
  badge?: NavBadge;
};

export type NavItem = NavLeaf | NavGroup;

export type NavSection = {
  id: string;
  label?: string;
  items: NavItem[];
};

export const navConfig: NavSection[] = [
  {
    id: "top",
    items: [
      { type: "leaf", id: "dashboard", label: "Dashboard", path: "today", icon: "◆" },
    ],
  },
  {
    id: "lifecycle",
    label: "DEAL LIFECYCLE",
    items: [
      { type: "leaf", id: "sourcing", label: "Sourcing", path: "market", icon: "◎" },
      { type: "leaf", id: "pipeline", label: "Pipeline", path: "pipeline", icon: "▦" },
      {
        type: "group", id: "dd", label: "Due Diligence", icon: "◈",
        children: [
          { id: "intake", label: "Intake", path: "intake" },
          { id: "diagnostic", label: "Diagnostic", path: "diagnostic" },
          { id: "evidence", label: "Evidence Checklist", path: "evidence" },
        ],
      },
      {
        type: "group", id: "ic", label: "Investment Committee", icon: "◻",
        children: [
          { id: "ic-prep", label: "IC Prep", path: "ic-prep" },
          { id: "ic-minutes", label: "IC Minutes", path: "ic-minutes" },
        ],
      },
      { type: "leaf", id: "closing", label: "Closing & Execution", path: "closing", icon: "▶" },
    ],
  },
  {
    id: "portfolio",
    label: "PORTFOLIO",
    items: [
      { type: "leaf", id: "portfolio-mgmt", label: "Portfolio Management", path: "portfolio", icon: "◉" },
      { type: "leaf", id: "risk", label: "Risk & Monitoring", path: "riskbook", icon: "⚠" },
    ],
  },
  {
    id: "reporting",
    label: "REPORTING",
    items: [
      { type: "leaf", id: "reporting", label: "Reporting & Analytics", path: "reporting", icon: "▤" },
      { type: "leaf", id: "investor-reporting", label: "Investor Reporting", path: "investor-reporting", icon: "▥" },
    ],
  },
  {
    id: "reference",
    label: "REFERENCE",
    items: [
      { type: "leaf", id: "documents", label: "Documents", path: "documents", icon: "▧" },
    ],
  },
];
