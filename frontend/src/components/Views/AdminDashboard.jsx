import React, { useContext, useState } from "react";
import { AppContext } from "../../context/AppContext";
import { COLORS } from "../../data/mockData";

export default function AdminDashboard() {
  const { localDoctors, setLocalDoctors, localPatients, setLocalPatients, userData } = useContext(AppContext);
  const [showAddDoc, setShowAddDoc] = useState(false);
  const [newDoc, setNewDoc] = useState({ name: "", spec: "", avail: "Available" });

  const handleAddDoctor = (e) => {
    e.preventDefault();
    if (!newDoc.name || !newDoc.spec) return;
    const added = {
      name: "Dr. " + newDoc.name,
      spec: newDoc.spec,
      rating: 5.0,
      avail: newDoc.avail,
      img: newDoc.name.substring(0, 2).toUpperCase(),
      color: COLORS.P
    };
    setLocalDoctors([...localDoctors, added]);
    setShowAddDoc(false);
    setNewDoc({ name: "", spec: "", avail: "Available" });
  };

  const revokeDoctor = (index) => {
    if(window.confirm("Are you sure you want to revoke access for this Doctor?")) {
      setLocalDoctors(localDoctors.filter((_, i) => i !== index));
    }
  };

  const revokePatient = (index) => {
    if(window.confirm("Are you sure you want to delete this Patient from the system?")) {
      setLocalPatients(localPatients.filter((_, i) => i !== index));
    }
  };

  return (
    <div>
      <div className="premium-banner" style={{ marginBottom: 24, color: "#fff", background: "linear-gradient(135deg, #1f2937 0%, #374151 100%)", padding: "26px 30px", borderRadius: 22 }}>
        <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, fontWeight: 600, marginBottom: 8 }}>Admin Operation Center</h2>
        <p style={{ fontSize: 13, opacity: .75, fontFamily: "'DM Sans',sans-serif", maxWidth: 360, marginBottom: 18 }}>System Overview. Welcome, {userData.name}.</p>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="hbtn" onClick={() => setShowAddDoc(true)} style={{ background: "#fff", color: "#1f2937", border: "none", padding: "9px 18px", borderRadius: 10, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 600 }}>+ Add Doctor</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(148px,1fr))", gap: 14, marginBottom: 24 }}>
        {[
          { label: "Total Doctors", val: localDoctors.length },
          { label: "Active Patients", val: localPatients.length },
          { label: "System Health", val: "99.9%" },
        ].map(v => (
          <div key={v.label} className="vcard" style={{ background: "#fff", borderRadius: 16, padding: "18px", border: "1px solid #E0EDE7" }}>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 28, fontWeight: 600, color: "#1f2937" }}>{v.val}</div>
            <div style={{ fontSize: 13, color: "#3d5a4e", fontFamily: "'DM Sans',sans-serif", marginTop: 5 }}>{v.label}</div>
          </div>
        ))}
      </div>

      {showAddDoc && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "24px", border: "1px solid #E0EDE7", marginBottom: 24 }}>
          <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>Register New Doctor</h3>
          <form onSubmit={handleAddDoctor} style={{ display: "flex", gap: 14, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 200 }}>
              <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Full Name (without Dr.)</label>
              <input autoFocus value={newDoc.name} onChange={e => setNewDoc({...newDoc, name: e.target.value})} className="cinput" style={{ width: "100%", padding: "11px 14px", borderRadius: 10 }} placeholder="e.g. Ayesha Kapoor" />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 200 }}>
              <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Specialization</label>
              <input value={newDoc.spec} onChange={e => setNewDoc({...newDoc, spec: e.target.value})} className="cinput" style={{ width: "100%", padding: "11px 14px", borderRadius: 10 }} placeholder="e.g. Cardiologist" />
            </div>
            <button type="submit" className="hbtn" style={{ background: COLORS.P, color: "#fff", border: "none", padding: "12.5px 24px", borderRadius: 10, fontSize: 14, cursor: "pointer", fontWeight: 600 }}>Submit</button>
            <button type="button" onClick={() => setShowAddDoc(false)} className="hbtn" style={{ background: "#FEE2E2", color: "#DC2626", border: "none", padding: "12.5px 24px", borderRadius: 10, fontSize: 14, cursor: "pointer", fontWeight: 600 }}>Cancel</button>
          </form>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
        {/* Doctors List */}
        <div>
          <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>System Doctors</h3>
          <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden", marginBottom: 30 }}>
            {localDoctors.map((d, i, arr) => (
              <div key={i} style={{ padding: "15px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ width: 40, height: 40, background: d.color + "20", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight:"bold", color: d.color, flexShrink: 0 }}>
                  {d.img}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{d.name}</div>
                  <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>{d.spec}</div>
                </div>
                <button 
                  onClick={() => revokeDoctor(i)}
                  className="hbtn" 
                  style={{ fontSize: 11, background: "#FEE2E2", color: "#DC2626", border:"none", padding: "5px 12px", borderRadius: 20, cursor:"pointer", fontWeight: 500 }}>
                  Revoke Access
                </button>
              </div>
            ))}
            {localDoctors.length === 0 && <div style={{ padding: 20, textAlign: "center", color: "#888", fontSize: 13, fontFamily: "'DM Sans',sans-serif" }}>No Doctors Found</div>}
          </div>
        </div>

        {/* Patients List */}
        <div>
          <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25", marginBottom: 14 }}>System Patients</h3>
          <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden", marginBottom: 30 }}>
            {localPatients.map((p, i, arr) => (
              <div key={i} style={{ padding: "15px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ width: 40, height: 40, background: COLORS.PL, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight:"bold", color: COLORS.P, flexShrink: 0 }}>
                  {p.name.split(" ").map(n=>n[0]).join("")}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{p.name}</div>
                  <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>ID: {p.id} · Status: {p.status}</div>
                </div>
                <button 
                  onClick={() => revokePatient(i)}
                  className="hbtn" 
                  style={{ fontSize: 11, background: "#FEE2E2", color: "#DC2626", border:"none", padding: "5px 12px", borderRadius: 20, cursor:"pointer", fontWeight: 500 }}>
                  Delete Account
                </button>
              </div>
            ))}
            {localPatients.length === 0 && <div style={{ padding: 20, textAlign: "center", color: "#888", fontSize: 13, fontFamily: "'DM Sans',sans-serif" }}>No Patients Found</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
