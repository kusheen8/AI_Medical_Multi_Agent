import React, { createContext, useState, useEffect, useRef } from "react";
import { LANGS, AGENT_KEYS } from "../data/mockData";

// eslint-disable-next-line react-refresh/only-export-components
export const AppContext = createContext();

export function AppProvider({ children }) {
  const [lang, setLang] = useState("en");
  // User Data State
  const [userData, setUserData] = useState({
    name: "Rohan Kumar",
    id: "#8821",
    email: "rohan.kumar@email.com",
    phone: "+91 9876543210",
    age: 32,
    bloodGroup: "O+",
    weight: "72kg",
    height: "178cm"
  });
  
  // SOS State
  const [showSOS, setShowSOS] = useState(false);
  const [sosActivated, setSosActivated] = useState(false);
  const [sosCountdown, setSosCountdown] = useState(5);
  const sosRef = useRef(null);

  // Chat/Agent State
  const [activeAgent, setActiveAgent] = useState("symptom");
  const [agentStatus, setAgentStatus] = useState({
    symptom: "active",
    cardio: "active",
    pharma: "idle",
    triage: "idle",
    diet: "active",
    mental: "idle"
  });

  // Symptom Checker State
  const [selSymptoms, setSelSymptoms] = useState([]);

  // Sidebar Layout State
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // SOS Effect
  useEffect(() => {
    if (sosActivated) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSosCountdown(5);
      sosRef.current = setInterval(() => {
        setSosCountdown(c => {
          if (c <= 1) {
            clearInterval(sosRef.current);
            return 0;
          }
          return c - 1;
        });
      }, 1000);
    }
    return () => clearInterval(sosRef.current);
  }, [sosActivated]);

  // Agent Status Randomizer
  useEffect(() => {
    const iv = setInterval(() => {
      const k = AGENT_KEYS[Math.floor(Math.random() * AGENT_KEYS.length)];
      setAgentStatus(p => ({ ...p, [k]: "processing" }));
      setTimeout(() => setAgentStatus(p => ({ ...p, [k]: "active" })), 1400);
    }, 2800);
    return () => clearInterval(iv);
  }, []);

  const cancelSOS = () => {
    setShowSOS(false);
    setSosActivated(false);
    setSosCountdown(5);
    clearInterval(sosRef.current);
  };

  const T = LANGS[lang].t;
  const isRTL = LANGS[lang].rtl;

  const contextValue = {
    lang, setLang, T, isRTL,
    userData, setUserData,
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
