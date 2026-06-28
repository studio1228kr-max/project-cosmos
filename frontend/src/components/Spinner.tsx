import React from "react";

// 공통 로딩 스피너 — 로고 이미지 회전. @keyframes spin 은 index.css 전역 정의.
export default function Spinner({
  size = 36,
  label,
  filter = "invert(1)",
  style,
}: {
  size?: number;
  label?: string;
  filter?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: 20, ...style }}>
      <img
        src="/logo.png"
        alt="loading"
        width={size}
        height={size}
        style={{ filter, animation: "spin 1s linear infinite" }}
      />
      {label && <span style={{ fontSize: 12, color: "#94A3B8" }}>{label}</span>}
    </div>
  );
}
