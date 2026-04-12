import React, { useContext, useState } from "react";
import { AppContext } from "../../context/AppContext";
import { COLORS } from "../../data/mockData";

export default function Profile() {
  const { userData, setUserData } = useContext(AppContext);
  const [formData, setFormData] = useState(userData);
  const [saved, setSaved] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setSaved(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setUserData(formData);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", background: "#fff", borderRadius: 22, border: "1px solid #E0EDE7", padding: "30px" }}>
      <h2 style={{ fontFamily: "'Playfair Display',serif", fontSize: 24, color: "#1a2e25", marginBottom: 20 }}>Edit Profile</h2>
      
      {saved && (
        <div style={{ padding: "12px", background: COLORS.PL, color: COLORS.P, borderRadius: 10, fontSize: 14, marginBottom: 20, fontFamily: "'DM Sans',sans-serif", fontWeight: 500 }}>
          ✓ Profile details updated successfully!
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Full Name</label>
            <input name="name" value={formData.name} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px 14px", borderRadius: 10 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Patient ID</label>
            <input name="id" value={formData.id} disabled className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px 14px", borderRadius: 10, background: "#f0f5f3", color: "#888" }} />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Email Address</label>
            <input name="email" value={formData.email} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px 14px", borderRadius: 10 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Phone Number</label>
            <input name="phone" value={formData.phone} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px 14px", borderRadius: 10 }} />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Age</label>
            <input name="age" type="number" value={formData.age} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px", borderRadius: 10 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Blood</label>
            <input name="bloodGroup" value={formData.bloodGroup} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px", borderRadius: 10 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Weight</label>
            <input name="weight" value={formData.weight} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px", borderRadius: 10 }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 12, color: "#7aaa94", fontFamily: "'DM Sans',sans-serif" }}>Height</label>
            <input name="height" value={formData.height} onChange={handleChange} className="cinput" style={{ width: "100%", minWidth: 0, boxSizing: "border-box", padding: "11px", borderRadius: 10 }} />
          </div>
        </div>

        <button type="submit" className="hbtn" style={{ background: COLORS.P, color: "#fff", border: "none", padding: "14px", borderRadius: 12, fontSize: 14, fontFamily: "'DM Sans',sans-serif", fontWeight: 600, marginTop: 10 }}>
          Save Changes
        </button>
      </form>
    </div>
  );
}
