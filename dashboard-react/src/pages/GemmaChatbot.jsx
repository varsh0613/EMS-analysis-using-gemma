import React, { useState, useRef, useEffect } from "react";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem("chatHistory");
    return saved ? JSON.parse(saved) : [];
  });
  const [currentChatId, setCurrentChatId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
  }, [chatHistory]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const startNewChat = () => {
    const newChatId = Date.now();
    setChatHistory((prev) => [
      { id: newChatId, title: "New Chat", timestamp: new Date(), messages: [] },
      ...prev,
    ]);
    setCurrentChatId(newChatId);
    setMessages([]);
  };

  const loadChat = (chatId) => {
    const chat = chatHistory.find((c) => c.id === chatId);
    if (chat) {
      setMessages(chat.messages || []);
      setCurrentChatId(chatId);
    }
  };

  const updateChatHistory = (newMessages, chatId = currentChatId) => {
    setChatHistory((prev) =>
      prev.map((chat) =>
        chat.id === chatId ? { ...chat, messages: newMessages } : chat
      )
    );
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    const text = input.trim();

    // Auto-create chat if none exists
    let chatId = currentChatId;
    if (!chatId) {
      chatId = Date.now();
      setChatHistory((prev) => [
        { id: chatId, title: text.substring(0, 50), timestamp: new Date(), messages: [] },
        ...prev,
      ]);
      setCurrentChatId(chatId);
    }

    const newMessages = [...messages, { sender: "user", text }];
    setMessages(newMessages);
    updateChatHistory(newMessages, chatId);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || "Server error");
      }

      const data = await res.json();
      const answerText = String(data.answer || "No reply from Gemma.").trim();
      const updatedMessages = [
        ...newMessages,
        {
          sender: "bot",
          text: answerText,
          protocols: Array.isArray(data.protocols) ? data.protocols : [],
          patient_summary: Array.isArray(data.patient_summary) ? data.patient_summary : [],
        },
      ];
      setMessages(updatedMessages);
      updateChatHistory(updatedMessages);

      // Update chat title with first user message
      setChatHistory((prev) =>
        prev.map((chat) =>
          chat.id === currentChatId ? { ...chat, title: text.substring(0, 50) } : chat
        )
      );
    } catch (err) {
      const updatedMessages = [
        ...newMessages,
        { sender: "bot", text: "Error connecting to Gemma backend." },
      ];
      setMessages(updatedMessages);
      updateChatHistory(updatedMessages);
    } finally {
      setLoading(false);
    }
  };

  const toggleDetails = (idx) => {
    setMessages((prev) =>
      prev.map((m, i) => (i === idx ? { ...m, open: !m.open } : m))
    );
  };

  const deleteChat = (chatId, e) => {
    e.stopPropagation();
    setChatHistory((prev) => prev.filter((c) => c.id !== chatId));
    if (currentChatId === chatId) {
      setMessages([]);
      setCurrentChatId(null);
    }
  };

  return (
    <div className="chatbot-layout">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <h2>Chat History</h2>
          <button className="new-chat-btn" onClick={startNewChat}>
            ➕ New Chat
          </button>
        </div>

        <div className="chat-list">
          {chatHistory.length === 0 ? (
            <p className="empty-state">No chats yet. Start a new one!</p>
          ) : (
            chatHistory.map((chat) => (
              <div
                key={chat.id}
                className={`chat-item ${currentChatId === chat.id ? "active" : ""}`}
              >
                <span 
                  className="chat-title-item"
                  onClick={() => loadChat(chat.id)}
                >
                  {chat.title || "New Chat"}
                </span>
                <button
                  className="delete-btn"
                  onClick={(e) => deleteChat(chat.id, e)}
                  title="Delete chat"
                >
                  🗑
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="main-container">
        <div className="chat-header">
          <button
            className="toggle-sidebar-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? "←" : "→"}
          </button>
          <h1 className="page-title">Gemma Assistant</h1>
          <div style={{ width: "40px" }}></div>
        </div>

        <div className="chat-window">
          {messages.length === 0 && !loading && (
            <div className="empty-chat">
              <div className="empty-icon">🤖</div>
              <h2>Welcome to Gemma Assistant</h2>
              <p>Ask me about EMS protocols, data analysis, or anything else</p>
              <div className="suggestion-buttons">
                <button onClick={() => setInput("What's the busiest city?")}>
                  Busiest City
                </button>
                <button onClick={() => setInput("Which hour has the most calls?")}>
                  Peak Hour
                </button>
                <button onClick={() => setInput("8-year-old with allergic reaction")}>
                  EMS Protocol
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`bubble ${msg.sender}`}>
              <div className="bubble-text">
                {typeof msg.text === "string" ? msg.text : String(msg.text || "")}
              </div>

              {msg.sender === "bot" &&
              (msg.protocols?.length > 0 || msg.patient_summary?.length > 0) ? (
                <div className="details">
                  <button className="toggle" onClick={() => toggleDetails(idx)}>
                    {msg.open ? "▼ Hide details" : "▶ Show protocols & examples"}
                  </button>

                  {msg.open && (
                    <div className="details-body">
                      {msg.protocols && msg.protocols.length > 0 && (
                        <div className="card-list">
                          <h4>📋 Protocols</h4>
                          {msg.protocols.map((p, i) => (
                            <div key={i} className="card">
                              <div className="card-title">Protocol {i + 1}</div>
                              <div className="card-body">{p}</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {msg.patient_summary && msg.patient_summary.length > 0 && (
                        <div className="card-list">
                          <h4>👥 Patient Examples</h4>
                          {msg.patient_summary.map((r, i) => (
                            <div key={i} className="card">
                              <div className="card-title">
                                {r.Patient_Age || ""} yo — {r.Primary_Impression || ""}
                              </div>
                              <div className="card-body">
                                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                                  {JSON.stringify(r, null, 2)}
                                </pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          ))}

          {loading && (
            <div className="bubble bot loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            type="text"
            placeholder="Ask Gemma... (e.g. '82-year-old with breathing difficulty')"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            className="chat-input"
          />
          <button onClick={sendMessage} className="chat-button" disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>

      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        .chatbot-layout {
          display: flex;
          height: calc(100vh - 40px);
          background: #ffffff;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Sidebar */
        .sidebar {
          width: 280px;
          background: #f5f0fa;
          color: #374151;
          display: flex;
          flex-direction: column;
          transition: all 0.3s ease;
          border-right: 1px solid #e5e7eb;
          overflow-y: auto;
        }

        .sidebar.closed {
          width: 0;
          padding: 0 !important;
          overflow: hidden;
        }

        .sidebar-header {
          padding: 20px;
          border-bottom: 1px solid #e5e7eb;
        }

        .sidebar-header h2 {
          font-size: 1.1rem;
          font-weight: 700;
          margin-bottom: 12px;
          color: #7b5ea3;
        }

        .new-chat-btn {
          width: 100%;
          padding: 10px 14px;
          background: white;
          color: #7b5ea3;
          border: 1.5px solid #d8cfe4;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.9rem;
          font-weight: 600;
          transition: all 0.2s ease;
        }

        .new-chat-btn:hover {
          background: #f5f0fa;
          border-color: #7b5ea3;
          transform: translateY(-2px);
        }

        .chat-list {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }

        .empty-state {
          padding: 20px;
          text-align: center;
          color: #9ca3af;
          font-size: 0.9rem;
        }

        .chat-item {
          padding: 12px 14px;
          margin-bottom: 6px;
          background: white;
          border-radius: 8px;
          cursor: pointer;
          display: flex;
          justify-content: space-between;
          align-items: center;
          transition: all 0.2s ease;
          border-left: 3px solid transparent;
          color: #374151;
          gap: 10px;
        }

        .chat-item:hover {
          background: #ede9fe;
          color: #7b5ea3;
        }

        .chat-item.active {
          background: #7b5ea3;
          color: white;
          border-left-color: #7b5ea3;
          box-shadow: 0px 0px 12px rgba(123, 94, 163, 0.5);
        }

        .chat-title-item {
          font-size: 0.9rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          flex: 1;
          cursor: pointer;
          min-width: 100px;
        }

        .delete-btn {
          background: transparent !important;
          border: none !important;
          color: #6b7280 !important;
          cursor: pointer;
          opacity: 1;
          transition: color 0.2s ease;
          margin-left: 4px;
          padding: 0 !important;
          font-size: 1rem;
          line-height: 1;
        }

        .delete-btn:hover {
          color: #ef4444 !important;
        }

        .chat-item.active .delete-btn {
          color: rgba(255, 255, 255, 0.7) !important;
        }

        .chat-item.active .delete-btn:hover {
          color: #ef4444 !important;
        }

        /* Main Container */
        .main-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          position: relative;
        }

        .chat-header {
          padding: 16px 24px;
          background: white;
          border-bottom: 1px solid #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: space-between;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .toggle-sidebar-btn {
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          color: #7b5ea3;
          padding: 8px;
          transition: transform 0.2s ease;
        }

        .toggle-sidebar-btn:hover {
          transform: scale(1.1);
        }

        .page-title {
          font-size: 1.4rem;
          color: #7b5ea3;
          font-weight: 800;
        }

        .chat-window {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: #ffffff;
        }

        .empty-chat {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          gap: 20px;
          color: #7b5ea3;
        }

        .empty-icon {
          font-size: 4rem;
          opacity: 0.8;
        }

        .empty-chat h2 {
          font-size: 1.8rem;
          color: #7b5ea3;
        }

        .empty-chat p {
          color: #9ca3af;
          font-size: 1rem;
        }

        .suggestion-buttons {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 10px;
          margin-top: 10px;
          width: 100%;
          max-width: 500px;
        }

        .suggestion-buttons button {
          padding: 10px 16px;
          background: #7b5ea3;
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 0.9rem;
          font-weight: 600;
          transition: all 0.2s ease;
        }

        .suggestion-buttons button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(123, 94, 163, 0.3);
        }

        /* Bubbles */
        .bubble {
          max-width: 75%;
          padding: 14px 16px;
          border-radius: 12px;
          line-height: 1.5;
          font-size: 0.95rem;
          animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .bubble.user {
          background: #7b5ea3;
          color: white;
          align-self: flex-end;
          border-bottom-right-radius: 4px;
          box-shadow: 0 4px 12px rgba(123, 94, 163, 0.15);
        }

        .bubble.bot {
          background: #f5f0fa;
          color: #374151;
          align-self: flex-start;
          border-bottom-left-radius: 4px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 2px 8px rgba(123, 94, 163, 0.05);
        }

        .bubble.loading {
          background: #f5f0fa;
          color: #7b5ea3;
          border: 1px solid #e5e7eb;
        }

        .bubble-text {
          white-space: pre-wrap;
          word-break: break-word;
          line-height: 1.6;
        }

        /* Details */
        .details {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid #e5e7eb;
        }

        .toggle {
          background: none;
          border: none;
          color: #7b5ea3;
          font-weight: 600;
          cursor: pointer;
          padding: 4px 0;
          font-size: 0.9rem;
          transition: color 0.2s ease;
        }

        .toggle:hover {
          color: #6c4da5;
        }

        .details-body {
          margin-top: 10px;
          display: flex;
          gap: 10px;
          flex-direction: column;
        }

        .card-list h4 {
          margin: 8px 0 10px 0;
          color: #7b5ea3;
          font-size: 0.9rem;
        }

        .card {
          border-radius: 8px;
          padding: 12px;
          background: #f5f0fa;
          border: 1px solid #e5e7eb;
        }

        .card-title {
          font-weight: 700;
          margin-bottom: 8px;
          color: #7b5ea3;
          font-size: 0.9rem;
        }

        .card-body {
          font-size: 0.85rem;
          color: #374151;
        }

        /* Input Area */
        .chat-input-area {
          display: flex;
          gap: 10px;
          padding: 16px 24px;
          background: white;
          border-top: 1px solid #e5e7eb;
        }

        .chat-input {
          flex: 1;
          padding: 12px 16px;
          border: 1.5px solid #e5e7eb;
          border-radius: 8px;
          outline: none;
          font-size: 0.95rem;
          color: #374151;
          transition: all 0.2s ease;
        }

        .chat-input:focus {
          border-color: #7b5ea3;
          box-shadow: 0 0 0 3px rgba(123, 94, 163, 0.1);
        }

        .chat-input::placeholder {
          color: #d1d5db;
        }

        .chat-button {
          padding: 12px 24px;
          background: #7b5ea3;
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 700;
          font-size: 0.95rem;
          transition: all 0.2s ease;
          min-width: 90px;
        }

        .chat-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(123, 94, 163, 0.3);
        }

        .chat-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        /* Typing Indicator */
        .typing-indicator {
          display: inline-flex;
          gap: 4px;
          align-items: center;
        }

        .typing-indicator span {
          width: 8px;
          height: 8px;
          background: #8b5cf6;
          border-radius: 50%;
          animation: bounce 1.4s infinite;
        }

        .typing-indicator span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-indicator span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes bounce {
          0%, 80%, 100% {
            transform: translateY(0);
            opacity: 0.6;
          }
          40% {
            transform: translateY(-8px);
            opacity: 1;
          }
        }

        /* Scrollbar */
        .chat-window::-webkit-scrollbar,
        .chat-list::-webkit-scrollbar {
          width: 6px;
        }

        .chat-window::-webkit-scrollbar-track,
        .chat-list::-webkit-scrollbar-track {
          background: transparent;
        }

        .chat-window::-webkit-scrollbar-thumb,
        .chat-list::-webkit-scrollbar-thumb {
          background: #ddd7fe;
          border-radius: 3px;
        }

        .chat-window::-webkit-scrollbar-thumb:hover,
        .chat-list::-webkit-scrollbar-thumb:hover {
          background: #c4b5fd;
        }

        /* Responsive */
        @media (max-width: 768px) {
          .sidebar {
            width: 0;
            position: absolute;
            height: 100vh;
            z-index: 100;
          }

          .sidebar.open {
            width: 100%;
            max-width: 280px;
          }

          .bubble {
            max-width: 90%;
          }

          .page-title {
            font-size: 1.2rem;
          }
        }
      `}</style>
    </div>
  );
}
