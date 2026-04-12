import React, { useContext, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AppContext } from "../../context/AppContext";
import { LANGS, COLORS } from "../../data/mockData";

export default function Header() {
  const { lang, setLang, T, setShowSOS, sidebarOpen, setSidebarOpen, userData } = useContext(AppContext);
  const [langOpen, setLangOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Format today's date
  const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  const todayStr = new Date().toLocaleDateString(lang, dateOptions);

  const routeMap = {
    "/": "dashboard",
    "/chat": "chat",
    "/doctors": "doctors",
    "/records": "records"
  };
  
  const currentTabName = T.nav[routeMap[location.pathname]] || "Profile";

  return (
    <header style={{ background: "#fff", borderBottom: "1px solid #E0EDE7", padding: "14px 22px", display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, zIndex: 50 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button className="menu-toggle hbtn" onClick={() => setSidebarOpen(!sidebarOpen)}
          style={{ width: 36, height: 36, border: "1px solid #E0EDE7", borderRadius: 8, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 16 }}>☰</span>
        </button>
        <div>
          <h1 style={{ fontFamily: "'Playfair Display',serif", fontWeight: 600, fontSize: 20, color: "#1a2e25", letterSpacing: "-.3px", textTransform: "capitalize" }}>
            {currentTabName}
          </h1>
          <p style={{ fontSize: 11, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>{todayStr}</p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* SOS Button */}
        <button className="hbtn" onClick={() => setShowSOS(true)}
          style={{ padding: "9px 18px", background: "#E24B4A", color: "#fff", border: "none", borderRadius: 22, fontSize: 13, fontWeight: 700, fontFamily: "'DM Sans',sans-serif", letterSpacing: ".8px", cursor: "pointer", display: "flex", alignItems: "center", gap: 7, animation: "sosPulse 2s ease-in-out infinite" }}>
          <span style={{ fontSize: 15 }}>🆘</span><span className="hide-mobile">SOS</span>
        </button>

        {/* Language */}
        <div style={{ position: "relative" }}>
          <button className="hbtn" onClick={() => setLangOpen(!langOpen)}
            style={{ padding: "8px 12px", border: "1px solid #E0EDE7", borderRadius: 10, background: "#fff", fontSize: 13, fontFamily: "'DM Sans',sans-serif", color: "#3d5a4e", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 16 }}>{LANGS[lang].flag}</span>
            <span style={{ fontSize: 12, display: "none" }} className="lang-label">{LANGS[lang].label}</span>
            <span style={{ fontSize: 10, opacity: .5 }}>▾</span>
          </button>
          
          {langOpen && (
            <div className="langmenu">
              {Object.values(LANGS).map(l => (
                <div key={l.code} className="lopt"
                  onClick={() => { setLang(l.code); setLangOpen(false); }}
                  style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: lang === l.code ? COLORS.P : "#3d5a4e", fontFamily: "'DM Sans',sans-serif", fontWeight: lang === l.code ? 500 : 400, background: lang === l.code ? COLORS.PL : "transparent" }}>
                  <span style={{ fontSize: 18 }}>{l.flag}</span>{l.label}
                  {lang === l.code && <span style={{ marginLeft: "auto", color: COLORS.P }}>✓</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Profile Avatar */}
        <div className="hbtn" onClick={() => navigate("/profile")} style={{ width: 34, height: 34, background: COLORS.P, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 500, cursor: "pointer" }}>
          {userData.name.split(" ").map(n=>n[0]).join("")}
        </div>
      </div>
    </header>
  );
}
