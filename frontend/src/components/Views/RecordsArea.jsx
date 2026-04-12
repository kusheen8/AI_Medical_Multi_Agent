import React, { useContext } from "react";
import { AppContext } from "../../context/AppContext";
import { RECORDS, COLORS } from "../../data/mockData";

export default function RecordsArea() {
  const { T } = useContext(AppContext);

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 14, marginBottom: 26 }}>
        {[{ label: "Total Visits", val: "24", sub: "Since 2022" }, { label: "Prescriptions", val: "8", sub: "Active: 2" }, { label: "Lab Reports", val: "12", sub: "Last: Mar 28" }, { label: "Vaccinations", val: "6", sub: "Up to date" }].map(s => (
          <div key={s.label} style={{ background: "#fff", borderRadius: 14, padding: "18px 16px", border: "1px solid #E0EDE7" }}>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, fontWeight: 600, color: COLORS.P, marginBottom: 2 }}>{s.val}</div>
            <div style={{ fontSize: 13, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif", fontWeight: 500 }}>{s.label}</div>
            <div style={{ fontSize: 11, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>
      <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>{T.recordsTitle}</h3>
      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden" }}>
        {RECORDS.map((r, i, arr) => (
          <div key={i} style={{ padding: "15px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14, cursor: "pointer" }} className="hbtn">
            <div style={{ width: 40, height: 40, background: COLORS.PL, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, color: COLORS.P, flexShrink: 0 }}>{r.icon}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{r.type}</div>
              <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.date} · {r.doc}</div>
            </div>
            <span style={{ fontSize: 11, background: r.sc, color: r.tc, padding: "4px 10px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif", flexShrink: 0 }}>{r.status}</span>
            <span style={{ color: "#7aaa94", fontSize: 16 }}>›</span>
          </div>
        ))}
      </div>
    </div>
  );
}
