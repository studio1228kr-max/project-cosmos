import { useState } from "react";
import { navConfig, NavGroup, NavLeaf, NavBadge } from "./navConfig";

const GOLD = "#C9A84C";
const TEXT = "#e2e2e2";
const TEXT_DIM = "#5a5a5a";
const TEXT_DIMMER = "#3a3a3a";
const ROW_ACTIVE_BG = "#1e1e1e";
const ROW_HOVER_BG = "#1a1a1a";
const SECTION_LABEL = "#3a3a3a";
const FONT = "'ZenSerif', 'Inter', sans-serif";

type SidebarNavProps = {
  activePath: string;
  onNavigate: (path: string) => void;
  collapsed?: boolean;
  badgeOverrides?: Record<string, NavBadge>;
  dotOverrides?: Record<string, boolean>;
};

export default function SidebarNav({
  activePath,
  onNavigate,
  collapsed = false,
  badgeOverrides = {},
  dotOverrides = {},
}: SidebarNavProps) {
  const [openGroupId, setOpenGroupId] = useState<string | null>(null);
  const [hoverId, setHoverId] = useState<string | null>(null);

  const childIsActive = (group: NavGroup) =>
    group.children.some((c) => c.path === activePath);

  return (
    <nav style={{ flex: 1, padding: collapsed ? "4px 4px" : "4px 8px", overflow: "auto", fontFamily: FONT }}>
      {navConfig.map((section) => (
        <div key={section.id}>
          {section.label && !collapsed && (
            <div style={{ padding: "14px 10px 6px", fontSize: 9, color: SECTION_LABEL, letterSpacing: "0.1em" }}>
              {section.label}
            </div>
          )}

          {section.items.map((item) => {
            if (item.type === "leaf") {
              return (
                <LeafRow
                  key={item.id}
                  item={item}
                  collapsed={collapsed}
                  active={activePath === item.path}
                  hovered={hoverId === item.id}
                  badge={badgeOverrides[item.id] ?? item.badge}
                  onHover={setHoverId}
                  onClick={() => onNavigate(item.path)}
                />
              );
            }

            const open = !collapsed && openGroupId === item.id;
            return (
              <div key={item.id}>
                <GroupRow
                  item={item}
                  collapsed={collapsed}
                  active={childIsActive(item)}
                  open={open}
                  hovered={hoverId === item.id}
                  badge={badgeOverrides[item.id] ?? item.badge}
                  onHover={setHoverId}
                  onClick={() => {
                    if (collapsed) return;
                    setOpenGroupId(open ? null : item.id);
                  }}
                />
                {!collapsed && (
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
                            padding: "6px 10px 6px 30px", fontSize: 12, cursor: "pointer",
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
                )}
              </div>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

function Badge({ text, tone }: NavBadge) {
  return (
    <span style={{
      fontSize: 9, padding: "1px 6px", borderRadius: 8, fontWeight: 600,
      background: tone === "hold" ? "#FCEBEB" : "#1e1e1e",
      color: tone === "hold" ? "#A32D2D" : TEXT_DIMMER,
    }}>
      {text}
    </span>
  );
}

function LeafRow({
  item, collapsed, active, hovered, badge, onHover, onClick,
}: { item: NavLeaf; collapsed: boolean; active: boolean; hovered: boolean; badge?: NavBadge; onHover: (id: string | null) => void; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
      style={{
        width: "100%", display: "flex", alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between", gap: 8,
        padding: collapsed ? "8px 0" : "7px 10px", borderRadius: 6,
        border: "none", cursor: "pointer", marginBottom: 1,
        background: active ? ROW_ACTIVE_BG : hovered ? ROW_HOVER_BG : "transparent",
        fontFamily: FONT,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: collapsed ? 0 : 9, fontSize: collapsed ? 16 : 13, color: active ? TEXT : hovered ? "#aaa" : TEXT_DIM, fontWeight: active ? 500 : 400 }}>
        <span style={{ fontSize: collapsed ? 14 : 11, opacity: 0.7 }}>{item.icon}</span>
        {!collapsed && item.label}
      </span>
      {!collapsed && badge && <Badge {...badge} />}
    </button>
  );
}

function GroupRow({
  item, collapsed, active, open, hovered, badge, onHover, onClick,
}: { item: NavGroup; collapsed: boolean; active: boolean; open: boolean; hovered: boolean; badge?: NavBadge; onHover: (id: string | null) => void; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
      style={{
        width: "100%", display: "flex", alignItems: "center",
        justifyContent: collapsed ? "center" : "space-between", gap: 8,
        padding: collapsed ? "8px 0" : "7px 10px", borderRadius: 6,
        border: "none", cursor: "pointer", marginBottom: 1,
        background: active ? ROW_ACTIVE_BG : hovered ? ROW_HOVER_BG : "transparent",
        fontFamily: FONT,
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: collapsed ? 0 : 9, fontSize: collapsed ? 16 : 13, color: active ? TEXT : hovered ? "#aaa" : TEXT_DIM, fontWeight: active ? 500 : 400 }}>
        <span style={{ fontSize: collapsed ? 14 : 11, opacity: 0.7 }}>{item.icon}</span>
        {!collapsed && item.label}
      </span>
      {!collapsed && (
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {badge && <Badge {...badge} />}
          <span style={{ fontSize: 10, color: open ? GOLD : TEXT_DIM, transform: open ? "rotate(90deg)" : "none", transition: "transform 0.2s", display: "inline-block" }}>›</span>
        </span>
      )}
    </button>
  );
}
