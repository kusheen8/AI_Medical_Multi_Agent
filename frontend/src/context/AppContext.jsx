import React, { createContext, useState, useEffect } from "react";
import { LANGS, DOCTORS, RECORDS } from "../data/mockData";

export const AppContext = createContext();

const getLS = (key, def) => {
  try {
    const val = localStorage.getItem(key);
    return val ? JSON.parse(val) : def;
  } catch (e) {
    return def;
  }
};

const setLS = (key, val) => {
  localStorage.setItem(key, JSON.stringify(val));
};

export function AppProvider({ children }) {
  const [lang, setLang] = useState("en");

  // Auth State
  const [isAuthenticated, setIsAuthenticated] = useState(() => getLS("auth_stat", false));
  const [userRole, setUserRole] = useState(() => getLS("auth_role", "patient")); // patient, doctor, admin

  // User Data State
  const [userData, setUserData] = useState(() => getLS("auth_user", {
    name: "Rohan Kumar",
    id: "#8821",
    email: "rohan.kumar@email.com",
    phone: "+91 9876543210",
    age: 32,
    bloodGroup: "O+",
    weight: "72kg",
    height: "178cm"
  }));

  // App Master Data (Mock Persistence)
  const [localDoctors, setLocalDoctors] = useState(() => getLS("data_docs", DOCTORS));
  const [localRecords, setLocalRecords] = useState(() => getLS("data_recs", RECORDS));
  const [localPatients, setLocalPatients] = useState(() => getLS("data_pats", [
    { name: "Rohan Kumar", id: "#8821", status: "Stable", lastVisit: "12 Apr 2026" },
    { name: "Anita Sharma", id: "#8822", status: "Critical", lastVisit: "10 Apr 2026" },
    { name: "Vikram Singh", id: "#8823", status: "Monitoring", lastVisit: "05 Apr 2026" },
  ]));

  // SOS State
  const [showSOS, setShowSOS] = useState(false);
  const [sosActivated, setSosActivated] = useState(false);
  const [sosCountdown, setSosCountdown] = useState(5);

  // Chat/AI State
  const [activeAgent, setActiveAgent] = useState("symptom");
  const [agentStatus, setAgentStatus] = useState({
    symptom: "online", cardio: "online", pharma: "online",
    triage: "online", diet: "online", mental: "online"
  });

  // Dashboard state
  const [selSymptoms, setSelSymptoms] = useState([]);

  // Sidebar Layout
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Persistence Effects
  useEffect(() => { setLS("auth_stat", isAuthenticated); }, [isAuthenticated]);
  useEffect(() => { setLS("auth_role", userRole); }, [userRole]);
  useEffect(() => { setLS("auth_user", userData); }, [userData]);
  useEffect(() => { setLS("data_docs", localDoctors); }, [localDoctors]);
  useEffect(() => { setLS("data_recs", localRecords); }, [localRecords]);
  useEffect(() => { setLS("data_pats", localPatients); }, [localPatients]);

  const T = LANGS[lang].t;
  const isRTL = LANGS[lang].rtl;

  const cancelSOS = () => {
    setSosActivated(false);
    setShowSOS(false);
    setSosCountdown(5);
  };

  const loginUser = (role) => {
    setUserRole(role);
    setIsAuthenticated(true);
    if(role === "doctor") setUserData({...userData, name: "Dr. Ayesha Kapoor", id: "DOC-001"});
    if(role === "admin") setUserData({...userData, name: "System Admin", id: "ADM-999"});
    if(role === "patient") setUserData({...userData, name: "Rohan Kumar", id: "#8821"});
  };

  const logoutUser = () => {
    setIsAuthenticated(false);
    setUserRole("patient");
  };

  const contextValue = {
    lang, setLang, T, isRTL,
    isAuthenticated, userRole, loginUser, logoutUser,
    userData, setUserData,
    localDoctors, setLocalDoctors, localRecords, setLocalRecords, localPatients, setLocalPatients,
    showSOS, setShowSOS, sosActivated, setSosActivated, sosCountdown, setSosCountdown, cancelSOS,
    activeAgent, setActiveAgent, agentStatus, setAgentStatus,
    selSymptoms, setSelSymptoms,
    sidebarOpen, setSidebarOpen
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}
