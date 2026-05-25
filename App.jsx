import React, { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  // State Management
  const [messages, setMessages] = useState([
    { sender: "ai", text: "Hello. I am your AI Document Intelligence System. Upload a PDF to begin." }
  ]);
  const [currentInput, setCurrentInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Document Context State
  const [fileName, setFileName] = useState("No file selected");
  const [docStatus, setDocStatus] = useState("Awaiting Upload");
  const [summary, setSummary] = useState("");

  // Auto-scroll reference for the chat
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // --- Handlers ---
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setFileName(file.name);
    setDocStatus("Processing layout & generating vectors...");
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("https://sabari0123-dockerfile.hf.space/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        setDocStatus("Document Active & Vectorized");
        setMessages(prev => [...prev, { sender: "system", text: `Document loaded successfully: ${file.name}` }]);
      } else {
        setDocStatus("Upload Failed");
        alert("Error: " + data.error);
      }
    } catch (error) {
      console.error(error);
      setDocStatus("Connection Error");
      alert("Failed to connect to the backend server.");
    }
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!currentInput.trim()) return;

    const userMessage = currentInput.trim();
    setCurrentInput("");
    setMessages(prev => [...prev, { sender: "user", text: userMessage }]);
    setIsProcessing(true);

    try {
      const response = await fetch("https://sabari0123-dockerfile.hf.space/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage }),
      });

      const data = await response.json();
      if (response.ok) {
        setMessages(prev => [...prev, { sender: "ai", text: data.answer }]);
      } else {
        setMessages(prev => [...prev, { sender: "system", text: "Error: Could not retrieve answer." }]);
      }
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { sender: "system", text: "Network error communicating with the AI." }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGenerateSummary = async () => {
    setSummary("Generating comprehensive summary using BART...");
    try {
      const response = await fetch("https://sabari0123-dockerfile.hf.space/summary");
      const data = await response.json();
      if (data.summary) {
        setSummary(data.summary);
        setMessages(prev => [...prev, { sender: "system", text: "New document summary generated in the context panel." }]);
      }
    } catch (error) {
      setSummary("Failed to generate summary. Ensure a document is loaded.");
    }
  };

  // --- Render ---
  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-container">
          <div className="logo-box">AI</div>
          <h1 className="brand-title">
            Document <span>Intelligence</span> System
          </h1>
       </div>
       <div className="status-indicator">
         <span className="dot"></span> {isProcessing ? "Analyzing..." : "System Active"}
       </div>
      </header>

      {/* Main Split Layout */}
      <main className="main-layout">
        
        {/* Left Pane: Chat Interface */}
        <section className="chat-section">
          <div className="chat-history">
            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper ${msg.sender}`}>
                {msg.sender === 'user' && <div className="avatar user-avatar">U</div>}
                {msg.sender === 'ai' && <div className="avatar ai-avatar">AI</div>}
                
                <div className={`message-bubble ${msg.sender}-bubble`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {isProcessing && (
              <div className="message-wrapper ai">
                 <div className="avatar ai-avatar">AI</div>
                 <div className="message-bubble ai-bubble typing-indicator">Thinking...</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form className="chat-input-area" onSubmit={handleSendMessage}>
            <input
              type="text"
              placeholder="Ask a question about the document..."
              value={currentInput}
              onChange={(e) => setCurrentInput(e.target.value)}
              disabled={isProcessing}
            />
            <button type="submit" disabled={isProcessing || !currentInput.trim()}>
              Send
            </button>
          </form>
        </section>

        {/* Right Pane: Context & Specifications */}
        <section className="context-section">
          <div className="context-header">
            <h3>📄 Document Context</h3>
          </div>

          <div className="spec-card">
            <div className="spec-item">
              <span className="spec-icon">📂</span>
              <div>
                <strong>Active File</strong>
                <p>{fileName}</p>
              </div>
            </div>
            <div className="spec-item">
              <span className="spec-icon">⚡</span>
              <div>
                <strong>Vector Status</strong>
                <p>{docStatus}</p>
              </div>
            </div>
          </div>

          <div className="control-group">
            <label className="upload-btn">
              Upload New PDF
              <input type="file" accept=".pdf" onChange={handleFileUpload} hidden />
            </label>
            <button className="summary-btn" onClick={handleGenerateSummary}>
              Generate Summary
            </button>
          </div>

          {summary && (
            <div className="summary-card">
              <h4>Executive Summary</h4>
              <p>{summary}</p>
            </div>
          )}
        </section>

      </main>
    </div>
  );
}

export default App;