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
      { type: "leaf", id: "dashboard", label: "대시보드", path: "today", icon: "◆" },
    ],
  },
  {
    id: "lifecycle",
    label: "딜 진행 단계",
    items: [
      { type: "leaf", id: "sourcing", label: "딜 소싱", path: "market", icon: "◎" },
      { type: "leaf", id: "pipeline", label: "딜 목록", path: "pipeline", icon: "▦" },
      {
        type: "group", id: "dd", label: "실사", icon: "◈",
        children: [
          { id: "intake", label: "딜 등록", path: "intake" },
          { id: "diagnostic", label: "진단", path: "diagnostic" },
          { id: "evidence", label: "증빙 체크리스트", path: "evidence" },
        ],
      },
      {
        type: "group", id: "ic", label: "투자심의위원회", icon: "◻",
        children: [
          { id: "ic-prep", label: "심의 준비", path: "ic-prep" },
          { id: "ic-minutes", label: "심의록", path: "ic-minutes" },
        ],
      },
      { type: "leaf", id: "closing", label: "클로징·실행", path: "closing", icon: "▶" },
    ],
  },
  {
    id: "portfolio",
    label: "포트폴리오",
    items: [
      { type: "leaf", id: "portfolio-mgmt", label: "포트폴리오 관리", path: "portfolio", icon: "◉" },
      { type: "leaf", id: "risk", label: "리스크 모니터링", path: "riskbook", icon: "⚠" },
    ],
  },
  {
    id: "reporting",
    label: "보고서",
    items: [
      { type: "leaf", id: "reporting", label: "보고서·분석", path: "reporting", icon: "▤" },
      { type: "leaf", id: "investor-reporting", label: "투자자 보고", path: "investor-reporting", icon: "▥" },
    ],
  },
  {
    id: "reference",
    label: "참고자료",
    items: [
      { type: "leaf", id: "documents", label: "문서", path: "documents", icon: "▧" },
    ],
  },
];
