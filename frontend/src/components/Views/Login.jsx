import React, { useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext } from "../../context/AppContext";
import { COLORS } from "../../data/mockData";

export default function Login() {
  const { loginUser, T } = useContext(AppContext);
  const navigate = useNavigate();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleLogin = (role) => {
    loginUser(role);
    navigate("/");
  };

  const roles = [
    { id: "patient", icon: "👤", title: "Patient Access", desc: "View diagnostic reports, AI analysis & active prescriptions in real-time." },
    { id: "doctor", icon: "🩺", title: "Medical Staff", desc: "Manage clinic flows, access patient directories, and issue prescriptions." },
    { id: "admin", icon: "⚙️", title: "System Admin", desc: "Configure global parameters, securely register staff, and monitor flow." },
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#f2f7f5", overflow: "hidden" }}>
      
      {/* Left Panel - Branding & Creative */}
      <div style={{ 
        flex: "1 1 45%", 
        position: "relative", 
        background: `linear-gradient(135deg, ${COLORS.P} 0%, #06402E 100%)`, 
        color: "#fff", 
        display: "flex", 
        flexDirection: "column", 
        justifyContent: "space-between",
        padding: "60px",
        overflow: "hidden"
      }}>
        {/* Abstract Floating Shapes */}
        <div style={{ position: "absolute", top: -100, right: -100, width: 400, height: 400, border: "2px solid rgba(255,255,255,0.05)", borderRadius: "50%", animation: "sosRing 10s infinite linear" }} />
        <div style={{ position: "absolute", bottom: -50, left: -150, width: 600, height: 600, background: "radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 60%)", borderRadius: "50%" }} />
        
        {/* Pill Shapes */}
        <div style={{ position: "absolute", top: "20%", right: "15%", width: 120, height: 50, background: "rgba(255,255,255,0.05)", borderRadius: 40, transform: "rotate(-30deg)", backdropFilter: "blur(5px)" }} />
        <div style={{ position: "absolute", bottom: "30%", left: "10%", width: 80, height: 80, background: "rgba(255,255,255,0.08)", borderRadius: "50%", backdropFilter: "blur(10px)" }} />

        <div style={{ zIndex: 1, opacity: mounted ? 1 : 0, transform: mounted ? "translateX(0)" : "translateX(-40px)", transition: "all 1s cubic-bezier(0.2, 0.8, 0.2, 1)" }}>
          <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 50, height: 50, background: "#fff", borderRadius: 14, color: COLORS.P, fontSize: 24, fontFamily: "'Playfair Display',serif", marginBottom: 20 }}>
            +
          </div>
          <h1 style={{ fontFamily: "'Playfair Display',serif", fontSize: 54, fontWeight: 700, lineHeight: 1.1, letterSpacing: "-1px", marginBottom: 20 }}>
            The Future of <br/><span style={{ color: COLORS.PL }}>Clinical Intelligence.</span>
          </h1>
          <p style={{ fontSize: 16, opacity: 0.8, fontFamily: "'DM Sans',sans-serif", maxWidth: 400, lineHeight: 1.6 }}>
            Empowering patients, doctors, and institutions with instantaneous AI-driven medical analysis and frictionless operational workflows.
          </p>
        </div>

        <div style={{ zIndex: 1, fontFamily: "'DM Sans',sans-serif", fontSize: 13, opacity: 0.5, letterSpacing: "1px", textTransform: "uppercase" }}>
          © 2026 {T.appName} Health Systems
        </div>
      </div>

      {/* Right Panel - Login Options */}
      <div style={{ 
        flex: "1 1 55%", 
        display: "flex", 
        flexDirection: "column", 
        justifyContent: "center", 
        padding: "40px 80px",
        position: "relative"
      }}>
        <div style={{ maxWidth: 600, width: "100%", margin: "0 auto", opacity: mounted ? 1 : 0, transform: mounted ? "translateX(0)" : "translateX(40px)", transition: "all 1s cubic-bezier(0.2, 0.8, 0.2, 1) 0.2s" }}>
          
          <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 32, color: "#1a2e25", marginBottom: 10 }}>Secure Portal Gateway</h2>
          <p style={{ color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", fontSize: 15, marginBottom: 40 }}>Select your authorized role to authenticate into the system.</p>

          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {roles.map((r, i) => (
              <div 
                key={r.id} 
                onClick={() => handleLogin(r.id)} 
                style={{ 
                  background: "#fff", 
                  border: "1px solid #E0EDE7", 
                  borderRadius: 20, 
                  padding: "24px 30px",
                  display: "flex", 
                  alignItems: "center",
                  gap: 20,
                  cursor: "pointer",
                  boxShadow: "0 10px 30px rgba(0, 0, 0, 0.02)",
                  transition: "all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)",
                  transform: mounted ? "translateY(0)" : "translateY(20px)",
                  transitionDelay: `${(i * 0.15) + 0.4}s`
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.boxShadow = "0 20px 40px rgba(11, 110, 79, 0.08)";
                  e.currentTarget.style.borderColor = COLORS.P;
                  e.currentTarget.querySelector('.role-btn').style.background = COLORS.P;
                  e.currentTarget.querySelector('.role-btn').style.color = "#fff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow = "0 10px 30px rgba(0, 0, 0, 0.02)";
                  e.currentTarget.style.borderColor = "#E0EDE7";
                  e.currentTarget.querySelector('.role-btn').style.background = COLORS.PL;
                  e.currentTarget.querySelector('.role-btn').style.color = COLORS.P;
                }}
              >
                <div style={{ 
                  width: 64, height: 64, 
                  background: "linear-gradient(135deg, #f4fbf8 0%, #e6f6ef 100%)", 
                  color: COLORS.P, 
                  borderRadius: 16, 
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center", 
                  fontSize: 28,
                  flexShrink: 0
                }}>
                  {r.icon}
                </div>
                
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 20, color: "#1a2e25", fontWeight: 600, marginBottom: 4 }}>{r.title}</h3>
                  <p style={{ fontSize: 13, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", lineHeight: 1.5 }}>{r.desc}</p>
                </div>

                <div 
                  className="role-btn"
                  style={{ 
                    padding: "10px 16px", 
                    background: COLORS.PL, 
                    color: COLORS.P, 
                    borderRadius: 12, 
                    fontFamily: "'DM Sans',sans-serif",
                    fontWeight: 600,
                    fontSize: 13,
                    transition: "all 0.3s ease"
                  }}
                >
                  Enter →
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 40, justifyContent: "center" }}>
            <span style={{ fontSize: 18, color: COLORS.P }}>⚕</span>
            <span style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 12, color: "#8da89b", textTransform: "uppercase", letterSpacing: "1px" }}>HIPAA & GDPR Compliant Infrastructure</span>
          </div>

        </div>
      </div>
      
      {/* Mobile override logic to stack appropriately if needed */}
      <style>{`
        @media (max-width: 900px) {
          body > div > div { flex-direction: column !important; }
          body > div > div > div:first-child { flex: none !important; padding: 40px !important; }
          body > div > div > div:last-child { padding: 40px 20px !important; }
        }
      `}</style>
    </div>
  );
}
