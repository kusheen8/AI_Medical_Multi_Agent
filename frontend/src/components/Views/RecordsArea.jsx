import React, { useContext, useRef } from "react";
import { AppContext } from "../../context/AppContext";
import { COLORS } from "../../data/mockData";

export default function RecordsArea() {
  const { T, localRecords, setLocalRecords, userRole } = useContext(AppContext);
  const fileInputRef = useRef(null);

  const handleUpload = (e) => {
    const file = e.target.files[0];
    if(file) {
      const newRecord = {
        icon: "📄",
        type: file.name,
        date: new Date().toLocaleDateString("en-GB", { day: 'numeric', month: 'short', year: 'numeric' }),
        doc: "Self Uploaded",
        status: "Processing",
        sc: "#FFF3CD",
        tc: "#856404"
      };
      setLocalRecords([newRecord, ...localRecords]);
    }
  };

  const handleDownload = (recordName) => {
    // Generate a dummy blob to simulate downloading a PDF report natively via browser
    const blob = new Blob(["Simulated PDF Content for " + recordName], { type: 'application/pdf' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = recordName.replace(/\s+/g, '_') + '.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 14, marginBottom: 26 }}>
        {[{ label: "Total Visits", val: "24", sub: "Since 2022" }, { label: "Prescriptions", val: "8", sub: "Active: 2" }, { label: "Lab Reports", val: localRecords.length, sub: "Updated now" }, { label: "Vaccinations", val: "6", sub: "Up to date" }].map(s => (
          <div key={s.label} style={{ background: "#fff", borderRadius: 14, padding: "18px 16px", border: "1px solid #E0EDE7" }}>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, fontWeight: 600, color: COLORS.P, marginBottom: 2 }}>{s.val}</div>
            <div style={{ fontSize: 13, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif", fontWeight: 500 }}>{s.label}</div>
            <div style={{ fontSize: 11, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", marginTop: 2 }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h3 style={{ fontFamily: "'Playfair Display',serif", fontSize: 18, color: "#1a2e25" }}>{userRole === "doctor" ? "Patient Case Files" : T.recordsTitle}</h3>
        {userRole === "patient" && (
          <div>
            <input type="file" accept=".pdf,.jpg,.png" ref={fileInputRef} onChange={handleUpload} style={{ display: 'none' }} />
            <button className="hbtn" onClick={() => fileInputRef.current.click()} style={{ background: COLORS.P, color: "#fff", border: "none", padding: "8px 16px", borderRadius: 10, fontSize: 13, cursor: "pointer", fontWeight: 600 }}>+ Upload Report</button>
          </div>
        )}
      </div>

      <div style={{ background: "#fff", borderRadius: 16, border: "1px solid #E0EDE7", overflow: "hidden" }}>
        {localRecords.map((r, i, arr) => (
          <div key={i} style={{ padding: "15px 20px", borderBottom: i < arr.length - 1 ? "1px solid #E8F2EE" : "none", display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 40, height: 40, background: COLORS.PL, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, color: COLORS.P, flexShrink: 0 }}>{r.icon}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.type}</div>
              <div style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.date} · {r.doc}</div>
            </div>
            <span style={{ fontSize: 11, background: r.sc, color: r.tc, padding: "4px 10px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif", flexShrink: 0 }}>{r.status}</span>
            <button className="hbtn" onClick={() => handleDownload(r.type)} style={{ background: "#F0F5F3", border: "1px solid #D5E8E0", color: COLORS.P, padding: "5px 12px", borderRadius: 20, fontSize: 12, cursor: "pointer", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
              <span>↓</span> <span className="hide-mobile">Download (.pdf)</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
