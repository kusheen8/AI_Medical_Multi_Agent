import React, { useContext, useState } from "react";
import { AppContext } from "../../context/AppContext";
import { DOCTORS, COLORS } from "../../data/mockData";

export default function DoctorsList() {
  const { T } = useContext(AppContext);
  const [searchTerm, setSearchTerm] = useState("");
  const [specialty, setSpecialty] = useState(T.allSpecialties);
  const [toastMessage, setToastMessage] = useState("");

  const allSpecialties = Array.from(new Set(DOCTORS.map(d => d.spec)));

  const filteredDoctors = DOCTORS.filter(d => {
    const matchesSearch = d.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSpecialty = specialty === T.allSpecialties || d.spec === specialty;
    return matchesSearch && matchesSpecialty;
  });

  const handleBook = (name) => {
    setToastMessage(`Appointment requested for ${name}`);
    setTimeout(() => setToastMessage(""), 3000);
  };

  return (
    <div>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{ position: "fixed", bottom: 20, right: 20, background: "#1a2e25", color: "#fff", padding: "12px 20px", borderRadius: 8, fontSize: 14, zIndex: 1000, fontFamily: "'DM Sans',sans-serif", animation: "fadeUp 0.3s ease", boxShadow: "0 4px 12px rgba(0,0,0,0.15)" }}>
          {toastMessage}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <input 
          placeholder={T.searchDoctors} 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ flex: 1, minWidth: 180, padding: "11px 14px", borderRadius: 12, border: "1.5px solid #D5E8E0", background: "#fff", fontSize: 14, fontFamily: "'DM Sans',sans-serif", outline: "none", color: "#1a2e25" }}
        />
        <select 
          value={specialty}
          onChange={(e) => setSpecialty(e.target.value)}
          style={{ padding: "11px 14px", borderRadius: 12, border: "1.5px solid #D5E8E0", background: "#fff", fontSize: 14, fontFamily: "'DM Sans',sans-serif", color: "#3d5a4e", outline: "none" }}
        >
          <option value={T.allSpecialties}>{T.allSpecialties}</option>
          {allSpecialties.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {filteredDoctors.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px", color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>
          No doctors found.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(230px,1fr))", gap: 16 }}>
          {filteredDoctors.map(d => (
            <div key={d.name} className="dcard" style={{ background: "#fff", borderRadius: 20, padding: "22px 20px", border: "1px solid #E0EDE7" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <div style={{ width: 50, height: 50, borderRadius: 15, background: d.color + "22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, fontWeight: 600, color: d.color, fontFamily: "'DM Sans',sans-serif" }}>{d.img}</div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{d.name}</div>
                  <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>{d.spec}</div>
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ color: "#EF9F27" }}>★</span>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{d.rating}</span>
                </div>
                <span style={{ fontSize: 11, background: d.avail === T.availNow ? "#EAF3DE" : COLORS.PL, color: d.avail === T.availNow ? "#3B6D11" : COLORS.P, padding: "4px 10px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif" }}>
                  {d.avail === T.availNow ? "● " + T.availNow : "⏰ " + d.avail}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="hbtn" style={{ flex: 1, padding: "9px 0", borderRadius: 10, border: `1.5px solid ${COLORS.P}`, background: "#fff", color: COLORS.P, fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 500 }}>{T.message}</button>
                <button className="hbtn" onClick={() => handleBook(d.name)} style={{ flex: 1, padding: "9px 0", borderRadius: 10, border: "none", background: COLORS.P, color: "#fff", fontSize: 13, fontFamily: "'DM Sans',sans-serif", cursor: "pointer", fontWeight: 500 }}>{T.book}</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
