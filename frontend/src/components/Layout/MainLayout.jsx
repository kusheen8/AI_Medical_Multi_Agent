import React, { useContext } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { AppContext } from "../../context/AppContext";
import Sidebar from "./Sidebar";
import Header from "./Header";
import SOSModal from "./SOSModal";
import Dashboard from "../Views/Dashboard";
import DoctorDashboard from "../Views/DoctorDashboard";
import AdminDashboard from "../Views/AdminDashboard";
import ChatArea from "../Views/ChatArea";
import DoctorsList from "../Views/DoctorsList";
import RecordsArea from "../Views/RecordsArea";
import Profile from "../Views/Profile";

export default function MainLayout() {
  const { isRTL, sidebarOpen, setSidebarOpen, userRole } = useContext(AppContext);
  const location = useLocation();

  let DashboardComponent = Dashboard;
  if(userRole === "doctor") DashboardComponent = DoctorDashboard;
  if(userRole === "admin") DashboardComponent = AdminDashboard;

  return (
    <div dir={isRTL ? "rtl" : "ltr"} style={{
      width: "100%", maxWidth: "100vw", overflowX: "hidden", fontFamily: "'DM Sans',sans-serif", background: "#F7FAF8", minHeight: "100vh", display: "flex", position: "relative"
    }}>
      <SOSModal />
      <Sidebar />
      <div className={`overlay${sidebarOpen ? " open" : ""}`} onClick={() => setSidebarOpen(false)} />

      <main className="main-content" style={{ flex: 1, width: "100%", overflow: "auto", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <Header />
        
        <div style={{ padding: "22px 22px 48px", flex: 1 }}>
          <Routes location={location}>
            <Route path="/" element={<DashboardComponent />} />
            {userRole === "patient" && <Route path="/chat" element={<ChatArea />} />}
            {(userRole === "patient" || userRole === "admin") && <Route path="/doctors" element={<DoctorsList />} />}
            {(userRole === "patient" || userRole === "doctor") && <Route path="/records" element={<RecordsArea />} />}
            {userRole === "admin" && <Route path="/patients" element={<AdminDashboard />} />}
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
