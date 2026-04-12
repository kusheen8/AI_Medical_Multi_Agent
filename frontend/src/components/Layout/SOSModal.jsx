import React, { useContext } from "react";
import { AppContext } from "../../context/AppContext";

export default function SOSModal() {
  const { showSOS, cancelSOS, sosActivated, setSosActivated, sosCountdown, T } = useContext(AppContext);

  if (!showSOS) return null;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.72)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ background: "#fff", borderRadius: 24, padding: "36px 30px", maxWidth: 420, width: "100%", textAlign: "center", border: sosActivated ? "3px solid #E24B4A" : "1.5px solid #E0EDE7", position: "relative" }}>
        {!sosActivated ? (
          <>
            <div style={{ width: 88, height: 88, background: "#FCEBEB", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", fontSize: 42 }}>🚨</div>
            <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 24, color: "#E24B4A", marginBottom: 10 }}>{T.sosTitle}</h2>
            <p style={{ fontSize: 13, color: "#7a6060", fontFamily: "'DM Sans',sans-serif", marginBottom: 24, lineHeight: 1.7 }}>{T.sosWarning}</p>
            <button className="hbtn" onClick={() => setSosActivated(true)}
              style={{ width: "100%", padding: "14px", borderRadius: 14, background: "#E24B4A", color: "#fff", border: "none", fontSize: 15, fontWeight: 700, fontFamily: "'DM Sans',sans-serif", marginBottom: 12, letterSpacing: ".5px", cursor: "pointer" }}>
              {T.sosConfirm}
            </button>
            <button className="hbtn" onClick={cancelSOS}
              style={{ width: "100%", padding: "12px", borderRadius: 14, background: "transparent", color: "#888", border: "1px solid #E0EDE7", fontSize: 14, fontFamily: "'DM Sans',sans-serif", cursor: "pointer" }}>
              {T.sosCancel}
            </button>
          </>
        ) : (
          <>
            <div className="sos-ring" style={{ width: 96, height: 96, background: "#E24B4A", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 22px", fontSize: 40, animation: "sosPulse 1.2s ease-in-out infinite, sosRing 1.5s ease-in-out infinite" }}>🚨</div>
            <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 22, color: "#E24B4A", marginBottom: 12 }}>SOS ACTIVATED</h2>
            <p style={{ fontSize: 13, color: "#3d3030", fontFamily: "'DM Sans',sans-serif", marginBottom: 8, lineHeight: 1.7 }}>{T.sosMsg}</p>
            {sosCountdown > 0
              ? <div style={{ fontSize: 56, fontFamily: "'Playfair Display',serif", color: "#E24B4A", margin: "18px 0", fontWeight: 600 }}>{sosCountdown}</div>
              : <div style={{ fontSize: 14, color: "#1D9E75", fontWeight: 600, fontFamily: "'DM Sans',sans-serif", margin: "18px 0" }}>✓ Emergency services notified</div>
            }
            <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
              {[{ l: "📞 108 Ambulance", c: "#E24B4A" }, { l: "👮 100 Police", c: "#185FA5" }, { l: "🏥 Nearest ER", c: "#3B6D11" }].map(x => (
                <div key={x.l} style={{ flex: 1, padding: "10px 4px", background: x.c + "18", borderRadius: 10, fontSize: 10, color: x.c, fontFamily: "'DM Sans',sans-serif", fontWeight: 600, textAlign: "center", lineHeight: 1.4 }}>{x.l}</div>
              ))}
            </div>
            <button onClick={cancelSOS} style={{ width: "100%", padding: "11px", borderRadius: 12, background: "transparent", color: "#aaa", border: "1px solid #E0EDE7", fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer" }}>Dismiss</button>
          </>
        )}
      </div>
    </div>
  );
}
