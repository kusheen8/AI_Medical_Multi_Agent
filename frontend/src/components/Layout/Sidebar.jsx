import React, { useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AppContext } from "../../context/AppContext";
import { AGENT_KEYS, AGENT_COLORS, AGENT_ICONS, COLORS } from "../../data/mockData";

export default function Sidebar() {
  const { T, activeAgent, setActiveAgent, agentStatus, sidebarOpen, setSidebarOpen, userData, userRole } = useContext(AppContext);
  const location = useLocation();
  const navigate = useNavigate();

  // Route Maps based on role
  const routeMapPatient = { dashboard: "/", chat: "/chat", doctors: "/doctors", records: "/records" };
  const routeMapDoctor = { dashboard: "/", records: "/records", profile: "/profile" };
  const routeMapAdmin = { dashboard: "/", doctors: "/doctors", patients: "/patients", profile: "/profile" };

  let currentRouteMap = routeMapPatient;
  let navLabels = T.nav;
  let navIcons = { dashboard: "⬡", chat: "◫", doctors: "✦", records: "◩", patients: "👥", profile: "⚙️" };

  if (userRole === "doctor") {
    currentRouteMap = routeMapDoctor;
    navLabels = { dashboard: "Clinic Dashboard", records: "Patient Case Files", profile: "My Settings" };
  } else if (userRole === "admin") {
    currentRouteMap = routeMapAdmin;
    navLabels = { dashboard: "System Hub", doctors: "Manage Doctors", patients: "Manage Patients", profile: "Config" };
  }

  const currentTab = Object.keys(currentRouteMap).find(key => currentRouteMap[key] === location.pathname) || "profile";

  return (
    <aside className={`sidebar${sidebarOpen ? " open" : ""}`} style={{
      width: 252,
      minWidth: 252,
      background: "#fff",
      borderRight: "1px solid #E0EDE7",
      display: "flex",
      flexDirection: "column",
      position: "sticky",
      top: 0,
      height: "100vh",
      flexShrink: 0
    }}>
      <div style={{ padding: "24px 16px 18px", borderBottom: "1px solid #E8F2EE" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 38, height: 38, background: COLORS.P, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ color: "#fff", fontSize: 20, fontFamily: "'Playfair Display',serif" }}>+</span>
          </div>
          <div>
            <div style={{ fontFamily: "'Playfair Display',serif", fontWeight: 600, fontSize: 17, color: "#1a2e25" }}>{T.appName}</div>
            <div style={{ fontSize: 10, color: "#7aaa94", letterSpacing: ".5px", textTransform: "uppercase", fontFamily: "'DM Sans',sans-serif" }}>
              {userRole === "patient" ? T.appSub : userRole.toUpperCase() + " PORTAL"}
            </div>
          </div>
        </div>
      </div>

      <nav style={{ padding: "12px 10px", flex: 1, overflowY: "auto" }}>
        {Object.entries(navLabels).map(([id, label]) => {
          const isActive = currentTab === id;
          return (
            <button key={id} className={`tbtn${isActive ? " act" : ""}`}
              onClick={() => { navigate(currentRouteMap[id]); setSidebarOpen(false); }}
              style={{
                padding: "11px 12px", borderRadius: 10, marginBottom: 3, display: "flex", alignItems: "center", gap: 12, fontSize: 14,
                color: isActive ? COLORS.P : "#3d5a4e", fontFamily: "'DM Sans',sans-serif", fontWeight: isActive ? 500 : 400
              }}>
              <span style={{ fontSize: 16, opacity: .75 }}>{navIcons[id]}</span>
              {label}
              {id === "chat" && <span style={{ marginLeft: "auto", background: COLORS.P, color: "#fff", borderRadius: 20, fontSize: 9, padding: "2px 7px" }}>MULTI-AI</span>}
            </button>
          );
        })}

        {userRole === "patient" && (
          <>
            <div style={{ margin: "16px 0 8px", fontSize: 10, letterSpacing: "1px", color: "#9ab8ac", textTransform: "uppercase", padding: "0 8px", fontFamily: "'DM Sans',sans-serif" }}>{T.agentsTitle}</div>
            {AGENT_KEYS.map(key => {
              const ag = T.agents[key];
              const isAct = activeAgent === key && location.pathname === "/chat";
              const st = agentStatus[key];
              return (
                <div key={key} className="agcard"
                  onClick={() => { setActiveAgent(key); navigate("/chat"); setSidebarOpen(false); }}
                  style={{
                    padding: "9px 10px", borderRadius: 10, marginBottom: 4, display: "flex", alignItems: "center", gap: 10,
                    background: isAct ? AGENT_COLORS[key] + "15" : "transparent", border: isAct ? `1px solid ${AGENT_COLORS[key]}40` : "1px solid transparent"
                  }}>
                  <div style={{ width: 28, height: 28, borderRadius: 8, background: AGENT_COLORS[key] + "20", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: AGENT_COLORS[key], flexShrink: 0 }}>
                    {AGENT_ICONS[key]}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ag.name}</div>
                    <div style={{ fontSize: 10, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{ag.role}</div>
                  </div>
                  <div style={{ width: 7, height: 7, borderRadius: "50%", background: st === "processing" ? "#EF9F27" : AGENT_COLORS[key], flexShrink: 0, animation: st === "processing" ? "blink .6s ease infinite" : "none" }} />
                </div>
              );
            })}
          </>
        )}
      </nav>

      <div style={{ padding: "14px 16px 22px", borderTop: "1px solid #E8F2EE" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div className="hbtn" onClick={() => { navigate("/profile"); setSidebarOpen(false); }} style={{ width: 34, height: 34, borderRadius: "50%", background: COLORS.PM, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 500 }}>
            {userData.name.split(" ").map(n=>n[0]).join("")}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{userData.name}</div>
            <div style={{ fontSize: 11, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>ID: {userData.id}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
