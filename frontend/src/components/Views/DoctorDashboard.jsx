import React, { useContext, useState } from "react";
import { AppContext } from "../../context/AppContext";
import { COLORS } from "../../data/mockData";

export default function DoctorDashboard() {
  const { userData, localPatients, localRecords, setLocalRecords } = useContext(AppContext);
  const [prescribeModal, setPrescribeModal] = useState(null); // stores patient object to prescribe to
  const [prescriptionText, setPrescriptionText] = useState("");

  const handlePrescribeSubmit = (e) => {
    e.preventDefault();
    if (!prescriptionText.trim()) return;
    
    const newRecord = {
      icon: "◫",
      type: `Prescription: ${prescriptionText}`,
      date: new Date().toLocaleDateString("en-GB", { day: 'numeric', month: 'short', year: 'numeric' }),
      doc: userData.name,
      status: "Active",
      sc: "#FAEEDA", 
      tc: "#854F0B"
    };

    setLocalRecords([newRecord, ...localRecords]);
    setPrescribeModal(null);
    setPrescriptionText("");
    
    // Optional: show a quick mock alert
    // alert(`Successfully issued prescription for ${prescribeModal.name}`);
  };

  return (
    <div style={{ position: "relative" }}>
      {prescribeModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ background: "#fff", borderRadius: 20, padding: 24, width: "100%", maxWidth: 400 }}>
            <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 20, color: "#1a2e25", marginBottom: 6 }}>Write Prescription</h3>
            <p style={{ fontSize: 13, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", marginBottom: 18 }}>Issuing medication for <strong>{prescribeModal.name}</strong></p>
            <form onSubmit={handlePrescribeSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <input 
                autoFocus
                className="cinput"
                style={{ width: "100%", padding: "12px", borderRadius: 10 }}
                placeholder="e.g. Paracetamol 500mg, twice a day"
                value={prescriptionText}
                onChange={e => setPrescriptionText(e.target.value)}
              />
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                <button type="button" onClick={() => setPrescribeModal(null)} className="hbtn" style={{ background: "#FEE2E2", color: "#DC2626", border: "none", padding: "10px 16px", borderRadius: 10, cursor: "pointer", fontWeight: 600 }}>Cancel</button>
                <button type="submit" className="hbtn" style={{ background: COLORS.P, color: "#fff", border: "none", padding: "10px 16px", borderRadius: 10, cursor: "pointer", fontWeight: 600 }}>Issue Prescription</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="premium-banner" style={{ marginBottom: 24, color: "#fff" }}>
        <p style={{ fontSize: 13, opacity: .8, fontFamily: "'DM Sans',sans-serif", marginBottom: 4 }}>Welcome back,</p>
        <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, fontWeight: 600, marginBottom: 8 }}>{userData.name}</h2>
        <p style={{ fontSize: 13, opacity: .75, fontFamily: "'DM Sans',sans-serif", maxWidth: 360, marginBottom: 18 }}>You have 8 consultations scheduled for today.</p>
        <button className="hbtn" style={{ background: "#fff", color: COLORS.P, border: "none", padding: "9px 18px", borderRadius: 10, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 600 }}>Start Video Consultation</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(148px,1fr))", gap: 14, marginBottom: 24 }}>
        {[
          { label: "Today's Patients", val: localPatients.length },
          { label: "Pending Reports", val: "3" },
          { label: "Prescriptions to sign", val: "12" },
        ].map(v => (
          <div key={v.label} className="vcard" style={{ background: "#fff", borderRadius: 16, padding: "18px", border: "1px solid #E0EDE7" }}>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 28, fontWeight: 600, color: COLORS.P }}>{v.val}</div>
            <div style={{ fontSize: 13, color: "#3d5a4e", fontFamily: "'DM Sans',sans-serif", marginTop: 5 }}>{v.label}</div>
          </div>
        ))}
      </div>

      <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>My Patients Directory</h3>
      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden" }}>
        {localPatients.map((p, i, arr) => (
          <div key={i} style={{ padding: "15px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
            <div style={{ width: 40, height: 40, background: COLORS.PL, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight:"bold", color: COLORS.P, flexShrink: 0 }}>
              {p.name.split(" ").map(n=>n[0]).join("")}
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{p.name} <span style={{fontSize:11, color:"#888"}}>ID: {p.id}</span></div>
              <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Last Visit: {p.lastVisit}</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <span className="hbtn" style={{ fontSize: 11, background: p.status === "Critical" ? "#FEE2E2" : COLORS.PL, color: p.status === "Critical" ? "#DC2626" : COLORS.P, padding: "5px 12px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif", display:"flex", alignItems:"center" }}>{p.status}</span>
              <button 
                onClick={() => setPrescribeModal(p)}
                className="hbtn" 
                style={{ fontSize: 11, background: COLORS.P, color: "#fff", border:"none", padding: "6px 14px", borderRadius: 20, cursor:"pointer", fontWeight: 600 }}>
                + Prescribe
              </button>
            </div>
          </div>
        ))}
        {localPatients.length === 0 && (
          <div style={{ padding: "20px", textAlign: "center", color: "#888", fontFamily: "'DM Sans',sans-serif", fontSize: 13 }}>No patients currently registered in your directory.</div>
        )}
      </div>
    </div>
  );
}
