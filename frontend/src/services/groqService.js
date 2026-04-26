// Use straight fetch for robust Vite front-end compatibility, 
// bypassing any Node-specific SDK checks in the browser.

export const getGroqResponse = async (agentKey, userMessage, contextData) => {
  const apiKey = import.meta.env.VITE_GROQ_API_KEY;
  
  if (!apiKey || apiKey === "your_actual_key") {
    return "API Key is missing or invalid. Please add your VITE_GROQ_API_KEY to .env.local";
  }

  const roles = {
    symptom: "You are SymptomBot, an AI specialized in analyzing patient symptoms quickly entirely based on the provided inputs.",
    cardio: "You are CardioAgent, an AI specialized in heart health, ECGs, and blood pressure analysis.",
    pharma: "You are PharmaBot, an AI specialized in medication scheduling and interactions.",
    triage: "You are TriageAgent, an AI specialized in emergency prioritization. Reassure the user.",
    diet: "You are NutriBot, an AI specialized in diets and hydration.",
    mental: "You are MindAgent, an AI specialized in mental wellness and sleep tracking."
  };

  const systemInstruction = `
    ${roles[agentKey] || roles.symptom}
    You are speaking to ${contextData.name}, age ${contextData.age}, Weight: ${contextData.weight}. 
    Keep your responses extremely concise, under 3 sentences. Emulate a professional, warm medical assistant. 
    Do not use complex markdown, just direct text. Always clarify you are an AI assistant and they should consult a doctor if severe.
  `;

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "llama3-8b-8192",
        messages: [
          { role: "system", content: systemInstruction },
          { role: "user", content: userMessage }
        ],
        temperature: 0.3
      })
    });

    const data = await response.json();
    
    if (data.error) {
      console.error("Groq API Error:", data.error);
      return "Error: " + data.error.message;
    }

    return data.choices[0].message.content;
  } catch (error) {
    console.error("Fetch Error:", error);
    return "I'm currently unable to connect to the medical knowledge base. Please check your network or API key.";
  }
};
