import { useState } from "react";
import {
  LayoutDashboard, Radar, GitBranch, SearchCheck, Landmark,
  FileSignature, Briefcase, ShieldAlert, BarChart3, Users,
  FolderLock, ChevronRight, TrendingUp,
} from "lucide-react";
import { navConfig, NavGroup, NavLeaf, NavBadge } from "./navConfig";

const ICONS: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  LayoutDashboard, Radar, GitBranch, SearchCheck, Landmark,
  FileSignature, Briefcase, ShieldAlert, BarChart3, Users, FolderLock, TrendingUp,
};

const GOLD = "#C9A84C";
const TEXT = "#e2e2e2";
const TEXT_DIM = "#6a6a6a";
const TEXT_DIMMER = "#555";
const ROW_ACTIVE_BG = "#1a1a1a";
const ROW_HOVER_BG = "#161616";
const FONT = "'ZenSerif', 'Inter', sans-serif";

type SidebarNavProps = {
  activePath: string;
  onNavigate: (path: string) => void;
  badgeOverrides?: Record<string, NavBadge>;
  dotOverrides?: Record<string, boolean>;
};

export default function SidebarNav({
  activePath,
  onNavigate,
  badgeOverrides = {},
  dotOverrides = {},
}: SidebarNavProps) {
  const [openGroupId, setOpenGroupId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);

  const childIsActive = (group: NavGroup) =>
    group.children.some((c) => c.path === activePath);

  return (
    <div style={{ width: 220, background: "#111", display: "flex", flexDirection: "column", fontFamily: FONT, flex: 1, overflow: "hidden" }}>
      <div style={{ padding: "20px 16px 16px" }}>
        <div style={{ fontFamily: "'ZenSerif', serif", fontSize: 16, fontWeight: 700, color: TEXT, letterSpacing: "0.02em" }}>Luska Capital</div>
        <div style={{ fontSize: 11, color: TEXT_DIMMER, marginTop: 2 }}>by COSMOS</div>
      </div>

      <nav style={{ flex: 1, padding: "4px 8px", overflow: "auto" }}>
        {navConfig.map((section) => (
          <div key={section.id}>
            {section.label && (
              <div style={{ padding: "14px 10px 6px", fontSize: 10, color: TEXT_DIMMER, letterSpacing: "0.06em" }}>
                {section.label}
              </div>
            )}

            {section.items.map((item) => {
              if (item.type === "leaf") {
                return (
                  <LeafRow
                    key={item.id}
                    item={item}
                    active={activePath === item.path}
                    hovered={hoverId === item.id}
                    badge={badgeOverrides[item.id] ?? item.badge}
                    onHover={setHoverId}
                    onClick={() => onNavigate(item.path)}
                  />
                );
              }

              const open = openGroupId === item.id;
              return (
                <div key={item.id}>
                  <GroupRow
                    item={item}
                    active={childIsActive(item)}
                    open={open}
                    hovered={hoverId === item.id}
                    badge={badgeOverrides[item.id] ?? item.badge}
                    onHover={setHoverId}
                    onClick={() => setOpenGroupId(open ? null : item.id)}
                  />
                  <div style={{ maxHeight: open ? item.children.length * 32 + 4 : 0, overflow: "hidden", transition: "max-height 0.2s ease" }}>
                    {item.children.map((child) => {
                      const showDot = dotOverrides[child.id] ?? child.dot === "hold";
                      const active = activePath === child.path;
                      const hovered = hoverId === child.id;
                      return (
                        <div
                          key={child.id}
                          onClick={() => onNavigate(child.path)}
                          onMouseEnter={() => setHoverId(child.id)}
                          onMouseLeave={() => setHoverId(null)}
                          style={{
                            display: "flex", alignItems: "center", gap: 8,
                            padding: "6px 10px 6px 34px", fontSize: 12, cursor: "pointer",
                            color: active ? TEXT : hovered ? "#aaa" : TEXT_DIM,
                            fontWeight: active ? 500 : 400,
                          }}
                        >
                          {showDot && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#A32D2D", display: "inline-block" }} />}
                          {child.label}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </nav>
    </div>
  );
}

function Badge({ text, tone }: NavBadge) {
  return (
    <span style={{
      fontSize: 10, padding: "1px 7px", borderRadius: 8, fontWeight: 600,
      background: tone === "hold" ? "#FCEBEB" : "#1e1e1e",
      color: tone === "hold" ? "#A32D2D" : "#888",
    }}>
      {text}
    </span>
  );
}

function LeafRow({
  item, active, hovered, badge, onHover, onClick,
}: { item: NavLeaf; active: boolean; hovered: boolean; badge?: NavBadge; onHover: (id: string | null) => void; onClick: () => void }) {
  const Icon = ICONS[item.icon];
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
        padding: "7px 10px", borderRadius: 6, cursor: "pointer", marginBottom: 1,
        background: active ? ROW_ACTIVE_BG : hovered ? ROW_HOVER_BG : "transparent",
        borderLeft: active ? `2px solid ${GOLD}` : "2px solid transparent",
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 9, fontSize: 13, color: active ? TEXT : hovered ? "#aaa" : TEXT_DIM, fontWeight: active ? 500 : 400 }}>
        <Icon size={15} color={active ? GOLD : TEXT_DIM} />
        {item.label}
      </span>
      {badge && <Badge {...badge} />}
    </div>
  );
}

function GroupRow({
  item, active, open, hovered, badge, onHover, onClick,
}: { item: NavGroup; active: boolean; open: boolean; hovered: boolean; badge?: NavBadge; onHover: (id: string | null) => void; onClick: () => void }) {
  const Icon = ICONS[item.icon];
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
        padding: "7px 10px", borderRadius: 6, cursor: "pointer", marginBottom: 1,
        background: active ? ROW_ACTIVE_BG : hovered ? ROW_HOVER_BG : "transparent",
        borderLeft: active ? `2px solid ${GOLD}` : "2px solid transparent",
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 9, fontSize: 13, color: active ? TEXT : hovered ? "#aaa" : TEXT_DIM, fontWeight: active ? 500 : 400 }}>
        <Icon size={15} color={active ? GOLD : TEXT_DIM} />
        {item.label}
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {badge && <Badge {...badge} />}
        <ChevronRight size={13} color={open ? GOLD : TEXT_DIM} style={{ transform: open ? "rotate(90deg)" : "none", transition: "transform 0.2s" }} />
      </span>
    </div>
  );
}
