import React, { useState, useEffect, useRef } from "react";
import { sendChatMessage, sendApprovalDecision, getSystemHealth } from "../services/api";

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      sender: "assistant",
      text: "Hello! I am DesktopPilot AI. What desktop task would you like me to perform?",
      tool: null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [systemOnline, setSystemOnline] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Health check on load
    getSystemHealth().then(res => {
      setSystemOnline(res.backend === "online");
    });
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingApproval]);

  const handleSend = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || isLoading) return;

    const userMessage = {
      sender: "user",
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!textToSend) setInput("");
    setIsLoading(true);

    try {
      const data = await sendChatMessage(text);

      const botMessage = {
        sender: "assistant",
        text: data.response,
        tool: data.tool_executed,
        toolResult: data.tool_result,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, botMessage]);

      if (data.requires_approval) {
        setPendingApproval({
          token: data.approval_token,
          prompt: data.approval_prompt
        });
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "assistant",
          text: `Connection error: Ensure FastAPI is running on http://127.0.0.1:8000. (${err.message})`,
          isError: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproval = async (approved) => {
    if (!pendingApproval) return;
    const token = pendingApproval.token;
    setPendingApproval(null);

    try {
      const data = await sendApprovalDecision(token, approved);
      setMessages((prev) => [
        ...prev,
        {
          sender: "assistant",
          text: data.response,
          tool: data.tool_executed,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err) {
      alert("Failed to submit approval: " + err.message);
    }
  };

  const samplePrompts = [
    "Open Notepad and type Welcome to DesktopPilot",
    "Open Calculator and calculate 25*4",
    "Search Python tutorials on YouTube",
    "Open Chrome",
    "Clean temporary files",
    "Launch VS Code"
  ];

  return (
    <div className="chat-container">
      {/* Top Header */}
      <div className="chat-header">
        <div className="title-group">
          <h2>DesktopPilot AI</h2>
          <span className={`status-pill ${systemOnline ? "online" : "offline"}`}>
            {systemOnline ? "FastAPI Online" : "Backend Offline"}
          </span>
        </div>
      </div>

      {/* Suggested Quick Buttons */}
      <div className="quick-prompts">
        <span className="quick-label">Try:</span>
        {samplePrompts.map((prompt, idx) => (
          <button
            key={idx}
            className="quick-chip"
            onClick={() => handleSend(prompt)}
            disabled={isLoading}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Messages Stream */}
      <div className="messages-area">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.sender}`}>
            <div className={`message-bubble ${msg.isError ? "error" : ""}`}>
              <div className="message-text">{msg.text}</div>

              {msg.tool && (
                <div className="tool-badge">
                  <span className="tool-icon">⚙️</span>
                  <span>Tool executed: <code>{msg.tool}</code></span>
                </div>
              )}

              <span className="timestamp">{msg.timestamp}</span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-row assistant">
            <div className="message-bubble loading">
              <span className="dot-pulse"></span>
              <span className="dot-pulse"></span>
              <span className="dot-pulse"></span>
              <span style={{ marginLeft: "8px", fontSize: "13px" }}>
                Analyzing request & preparing desktop tools...
              </span>
            </div>
          </div>
        )}

        {/* Human-in-the-Loop Approval Card */}
        {pendingApproval && (
          <div className="approval-card">
            <div className="approval-header">
              <span className="alert-icon">⚠️</span>
              <strong>Human Confirmation Required</strong>
            </div>
            <p className="approval-prompt">{pendingApproval.prompt}</p>
            <div className="approval-actions">
              <button
                className="btn-reject"
                onClick={() => handleApproval(false)}
              >
                Reject
              </button>
              <button
                className="btn-approve"
                onClick={() => handleApproval(true)}
              >
                Approve & Execute
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form
        className="chat-input-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          type="text"
          placeholder="Ask DesktopPilot to control your PC..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

