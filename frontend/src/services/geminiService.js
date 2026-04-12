// Use straight fetch for robust Vite front-end compatibility, 
// bypassing any Node-specific SDK checks in the browser.

export const getGeminiResponse = async (agentKey, userMessage, contextData) => {
  const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
  
  if (!apiKey || apiKey === "your_actual_key") {
    return "API Key is missing or invalid. Please add your VITE_GEMINI_API_KEY to .env.local";
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
    const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + apiKey, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        system_instruction: {
          parts: [{ text: systemInstruction }]
        },
        contents: [{
          parts: [{ text: userMessage }]
        }],
        generationConfig: {
          temperature: 0.3
        }
      })
    });

    const data = await response.json();
    
    if (data.error) {
      console.error("Gemini API Error:", data.error);
      return "Error: " + data.error.message;
    }

    return data.candidates[0].content.parts[0].text;
  } catch (error) {
    console.error("Fetch Error:", error);
    return "I'm currently unable to connect to the medical knowledge base. Please check your network or API key.";
  }
};
