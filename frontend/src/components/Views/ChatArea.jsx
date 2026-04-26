import React, { useContext, useState, useRef, useEffect, useCallback } from "react";
import { AppContext } from "../../context/AppContext";
import { AGENT_KEYS, AGENT_COLORS, AGENT_ICONS, AGENT_RESPONSES, COLORS } from "../../data/mockData";
import { getGroqResponse } from "../../services/groqService";

export default function ChatArea() {
  const { lang, T, activeAgent, setActiveAgent, selSymptoms, setSelSymptoms, userData } = useContext(AppContext);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [typingAgent, setTypingAgent] = useState(null);
  
  const chatEndRef = useRef(null);

  // Initial message / language change effect
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessages([{ role: "ai", agent: "symptom", text: "Hello! I'm " + T.agents.symptom.name + ". " + AGENT_RESPONSES.symptom[0] }]);
  }, [lang, T]);

  // Handle selected symptoms from dashboard
  useEffect(() => {
    if (selSymptoms.length > 0) {
      const sympText = selSymptoms.join(", ");
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMessages(m => [
        ...m, 
        { role: "user", text: `I am experiencing: ${sympText}. Can you analyze this?` }
      ]);
      setSelSymptoms([]); // Clear them so it doesn't loop
      
      setTyping(true);
      setTypingAgent("symptom");
      
      // Call Groq for symptom check instead of mock
      getGroqResponse("symptom", `I am experiencing: ${sympText}. Can you analyze this?`, userData)
        .then(aiResponse => {
          setMessages(m => [...m, { role: "ai", agent: "symptom", text: aiResponse }]);
          setTyping(false);
          setTypingAgent(null);
        });
    }
  }, [selSymptoms, setSelSymptoms, userData]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const sendMessage = useCallback(async () => {
    if (!input.trim()) return;
    
    const userMsg = input;
    setMessages(m => [...m, { role: "user", text: userMsg }]);
    setInput("");
    setTyping(true);
    setTypingAgent(activeAgent);
    
    // Call Groq API dynamically using the active agent persona
    const aiResponse = await getGroqResponse(activeAgent, userMsg, userData);
    
    setMessages(m => [...m, { role: "ai", agent: activeAgent, text: aiResponse }]);
    setTyping(false); 
    setTypingAgent(null);
  }, [input, activeAgent, userData]);

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 10, marginBottom: 14 }}>
        {AGENT_KEYS.map(key => {
          const ag = T.agents[key], isA = activeAgent === key;
          return (
            <button key={key} className="hbtn" onClick={() => setActiveAgent(key)}
              style={{ flexShrink: 0, padding: "8px 14px", borderRadius: 20, border: `1.5px solid ${isA ? AGENT_COLORS[key] : "#E0EDE7"}`, background: isA ? AGENT_COLORS[key] + "18" : "#fff", color: isA ? AGENT_COLORS[key] : "#3d5a4e", fontSize: 12, fontFamily: "'DM Sans',sans-serif", fontWeight: isA ? 600 : 400, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
              <span style={{ fontSize: 14 }}>{AGENT_ICONS[key]}</span>
              {ag.name}
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: AGENT_COLORS[key], display: "inline-block" }} />
            </button>
          );
        })}
      </div>
      
      <div style={{ background: "#fff", borderRadius: 22, border: "1px solid #E0EDE7", overflow: "hidden", display: "flex", flexDirection: "column", height: "calc(100vh - 255px)", minHeight: 460 }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #E8F2EE", display: "flex", alignItems: "center", gap: 12, background: "#FAFDFB" }}>
          <div style={{ width: 38, height: 38, borderRadius: 12, background: AGENT_COLORS[activeAgent] + "22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, color: AGENT_COLORS[activeAgent] }}>{AGENT_ICONS[activeAgent]}</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#1a2e25", fontFamily: "'DM Sans',sans-serif" }}>{T.agents[activeAgent].name}</div>
            <div style={{ fontSize: 11, color: AGENT_COLORS[activeAgent], fontFamily: "'DM Sans',sans-serif", display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 5, height: 5, background: AGENT_COLORS[activeAgent], borderRadius: "50%", display: "inline-block" }} />
              {T.agents[activeAgent].role}
            </div>
          </div>
          <span style={{ marginLeft: "auto", fontSize: 10, background: AGENT_COLORS[activeAgent] + "18", color: AGENT_COLORS[activeAgent], padding: "3px 10px", borderRadius: 20, fontFamily: "'DM Sans',sans-serif", fontWeight: 600 }}>{T.aiPowered}</span>
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 13 }}>
          {messages.map((msg, i) => (
            <div key={i} className="msg-in" style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", gap: 8, alignItems: "flex-end" }}>
              {msg.role === "ai" && (
                <div style={{ width: 28, height: 28, borderRadius: 8, background: AGENT_COLORS[msg.agent || "symptom"] + "22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: AGENT_COLORS[msg.agent || "symptom"], flexShrink: 0 }}>
                  {AGENT_ICONS[msg.agent || "symptom"]}
                </div>
              )}
              <div style={{ maxWidth: "76%", padding: "11px 15px", borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px", background: msg.role === "user" ? COLORS.P : "#F4FAF7", color: msg.role === "user" ? "#fff" : "#1a2e25", fontSize: 14, lineHeight: 1.65, fontFamily: "'DM Sans',sans-serif", border: msg.role === "ai" ? "1px solid #E0EDE7" : "none" }}>
                {msg.role === "ai" && msg.agent && (
                  <div style={{ fontSize: 10, color: AGENT_COLORS[msg.agent], fontWeight: 700, marginBottom: 4, letterSpacing: ".3px" }}>{T.agents[msg.agent]?.name}</div>
                )}
                {msg.text}
              </div>
            </div>
          ))}
          {typing && (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: AGENT_COLORS[typingAgent || "symptom"] + "22", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: AGENT_COLORS[typingAgent || "symptom"] }}>
                {AGENT_ICONS[typingAgent || "symptom"]}
              </div>
              <div style={{ padding: "11px 16px", borderRadius: "18px 18px 18px 4px", background: "#F4FAF7", border: "1px solid #E0EDE7", display: "flex", gap: 5, alignItems: "center" }}>
                {[0, .2, .4].map((d, j) => (
                  <span key={j} style={{ width: 7, height: 7, background: AGENT_COLORS[typingAgent || "symptom"], borderRadius: "50%", display: "inline-block", animation: `dotPulse 1s ease-in-out ${d}s infinite` }} />
                ))}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div style={{ padding: "8px 20px 4px", display: "flex", gap: 7, flexWrap: "wrap" }}>
          {T.quickReplies.map(q => (
            <button key={q} className="hbtn" onClick={() => setInput(q)}
              style={{ fontSize: 11, padding: "5px 11px", borderRadius: 20, border: "1px solid #D5E8E0", background: "#FAFDFB", color: "#3d5a4e", cursor: "pointer", fontFamily: "'DM Sans',sans-serif" }}>{q}</button>
          ))}
        </div>
        <div style={{ padding: "12px 16px 16px", borderTop: "1px solid #E8F2EE", display: "flex", gap: 10, alignItems: "flex-end" }}>
          <textarea className="cinput" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder={T.agentChat} rows={1}
            style={{ flex: 1, padding: "11px 14px", borderRadius: 12, background: "#FAFDFB", fontSize: 14, color: "#1a2e25", lineHeight: 1.5, maxHeight: 100 }} />
          <button className="hbtn" onClick={sendMessage}
            style={{ width: 44, height: 44, background: AGENT_COLORS[activeAgent], color: "#fff", border: "none", borderRadius: 12, fontSize: 18, flexShrink: 0, cursor: "pointer" }}>↑</button>
        </div>
      </div>
    </div>
  );
}
