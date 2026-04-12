import React, { useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext } from "../../context/AppContext";
import { AGENT_KEYS, AGENT_COLORS, AGENT_ICONS, VITALS, SYMPTOMS, APPOINTMENTS, COLORS } from "../../data/mockData";

export default function Dashboard() {
  const { T, setShowSOS, setActiveAgent, agentStatus, selSymptoms, setSelSymptoms, userData } = useContext(AppContext);
  const navigate = useNavigate();

  const handleSymptomAnalyze = () => {
    setActiveAgent("symptom");
    navigate("/chat");
  };

  return (
    <div>
      <div className="premium-banner" style={{ marginBottom: 24, color: "#fff" }}>
        <p style={{ fontSize: 13, opacity: .8, fontFamily: "'DM Sans',sans-serif", marginBottom: 4 }}>{T.greeting}</p>
        <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, fontWeight: 600, marginBottom: 8 }}>{userData.name}</h2>
        <p style={{ fontSize: 13, opacity: .75, fontFamily: "'DM Sans',sans-serif", maxWidth: 360, marginBottom: 18 }}>{T.greetSub}</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="hbtn" onClick={() => navigate("/chat")}
            style={{ background: "rgba(255,255,255,.18)", color: "#fff", border: "1px solid rgba(255,255,255,.35)", padding: "9px 18px", borderRadius: 10, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer" }}>
            {T.chatWithAI}
          </button>
          <button className="hbtn" onClick={() => setShowSOS(true)}
            style={{ background: "#E24B4A", color: "#fff", border: "none", padding: "9px 18px", borderRadius: 10, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
            🆘 {T.sosTitle}
          </button>
        </div>
      </div>

      {/* Live agent strip */}
      <div style={{ display: "flex", gap: 10, overflowX: "auto", paddingBottom: 8, marginBottom: 24 }}>
        {AGENT_KEYS.map(key => {
          const ag = T.agents[key], st = agentStatus[key];
          return (
            <div key={key} className="agcard"
              onClick={() => { setActiveAgent(key); navigate("/chat"); }}
              style={{ background: "#fff", border: `1px solid ${AGENT_COLORS[key]}30`, borderRadius: 16, padding: "14px 16px", flexShrink: 0, minWidth: 128, textAlign: "center" }}>
              <div style={{ fontSize: 24, color: AGENT_COLORS[key], marginBottom: 6 }}>{AGENT_ICONS[key]}</div>
              <div style={{ fontSize: 12, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif", marginBottom: 4 }}>{ag.name}</div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: st === "processing" ? "#EF9F27" : AGENT_COLORS[key], display: "inline-block", animation: st === "processing" ? "blink .6s infinite" : "none" }} />
                <span style={{ fontSize: 10, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>{st === "processing" ? "Processing…" : T.online}</span>
              </div>
            </div>
          );
        })}
      </div>

      <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>{T.vitalsTitle}</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(148px,1fr))", gap: 14, marginBottom: 24 }}>
        {VITALS.map(v => (
          <div key={v.label} className="vcard" style={{ background: "#fff", borderRadius: 16, padding: "18px", border: "1px solid #E0EDE7" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 20, color: COLORS.P }}>{v.icon}</span>
              <span style={{ fontSize: 10, background: COLORS.PL, color: COLORS.P, padding: "3px 8px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif" }}>Normal</span>
            </div>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, fontWeight: 600, color: "#1a2e25" }}>{v.value}</div>
            <div style={{ fontSize: 11, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", marginTop: 2 }}>{v.unit}</div>
            <div style={{ fontSize: 12, color: "#3d5a4e", fontFamily: "'DM Sans',sans-serif", marginTop: 5 }}>{v.label}</div>
          </div>
        ))}
      </div>

      <div style={{ background: "#fff", borderRadius: 20, padding: "22px", border: "1px solid #E0EDE7", marginBottom: 24 }}>
        <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 4 }}>{T.symptomTitle}</h3>
        <p style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", marginBottom: 14 }}>{T.symptomSub}</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
          {SYMPTOMS.map(s => (
            <div key={s} className="chip"
              onClick={() => setSelSymptoms(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])}
              style={{
                padding: "7px 14px", borderRadius: 30, fontSize: 13, fontFamily: "'DM Sans',sans-serif",
                border: `1.5px solid ${selSymptoms.includes(s) ? COLORS.P : "#D5E8E0"}`,
                background: selSymptoms.includes(s) ? COLORS.PL : "#FAFDFB",
                color: selSymptoms.includes(s) ? COLORS.P : "#3d5a4e",
                fontWeight: selSymptoms.includes(s) ? 500 : 400
              }}>
              {s}
            </div>
          ))}
        </div>
        {selSymptoms.length > 0 && (
          <button className="hbtn" onClick={handleSymptomAnalyze}
            style={{ background: COLORS.P, color: "#fff", border: "none", padding: "10px 22px", borderRadius: 10, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 500 }}>
            {T.analyzeBtn}
          </button>
        )}
      </div>

      <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>{T.appointmentsTitle}</h3>
      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden" }}>
        {APPOINTMENTS.map((a, i, arr) => (
          <div key={i} style={{ padding: "16px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 46, height: 46, background: COLORS.PL, borderRadius: 12, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ fontSize: 9, color: COLORS.P, fontFamily: "'DM Sans',sans-serif", textTransform: "uppercase" }}>{a.date.split(" ")[0]}</span>
              <span style={{ fontSize: 16, fontWeight: 600, color: COLORS.P, fontFamily: "'Playfair Display',serif" }}>{a.date.split(" ")[1]}</span>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{a.doctor}</div>
              <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>{a.spec} · {a.time}</div>
            </div>
            <span style={{ fontSize: 11, background: a.type === "Video" ? "#E6F1FB" : COLORS.PL, color: a.type === "Video" ? "#185FA5" : COLORS.P, padding: "4px 10px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif" }}>{a.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
