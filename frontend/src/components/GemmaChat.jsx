import React, { useState } from "react";

const GemmaChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input) return;
    setMessages([...messages, { text: input, sender: "user" }]);
    // TODO: call backend API /query and append response
    setInput("");
  };

  return (
    <div style={{ border: "1px solid #ccc", padding: "10px", display: "flex", flexDirection: "column", height: "calc(100vh - 100px)" }}>
      <div style={{ flex: 1, overflowY: "auto", marginBottom: "10px" }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ textAlign: msg.sender === "user" ? "right" : "left" }}>
            <b>{msg.sender}:</b> {msg.text}
          </div>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        style={{ width: "80%", marginRight: "10px" }}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
};

export default GemmaChat;
