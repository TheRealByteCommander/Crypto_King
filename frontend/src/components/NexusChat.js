import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Bot, Send, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${BACKEND_URL}/api`;

const NexusChat = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // Initialize with welcome message
    setMessages([{
      id: "welcome",
      type: "agent",
      message: "Hallo! Ich bin NexusChat, dein Kommunikations-Hub für Project CypherTrade. Wie kann ich dir helfen?",
      timestamp: new Date().toISOString()
    }]);

    // Connect to WebSocket for real-time updates
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const connectWebSocket = () => {
    const wsUrl = BACKEND_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/ws';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected for NexusChat");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "chat_message") {
          // Handle real-time chat messages if needed
          const chatData = data.data;
          if (chatData && chatData.response) {
            // Add incoming chat message if it's not already in messages
            setMessages(prev => {
              const exists = prev.some(msg => 
                msg.message === chatData.response && 
                msg.timestamp === chatData.timestamp
              );
              if (!exists) {
                return [...prev, {
                  id: Date.now().toString(),
                  type: "agent",
                  message: chatData.response,
                  timestamp: chatData.timestamp
                }];
              }
              return prev;
            });
          }
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected for NexusChat");
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };

    wsRef.current = ws;
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage("");
    setIsLoading(true);

    // Add user message to chat
    const userMsg = {
      id: Date.now().toString(),
      type: "user",
      message: userMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const response = await axios.post(`${API}/chat`, {
        message: userMessage
      });

      if (response.data.success) {
        // Add agent response to chat
        const agentMsg = {
          id: (Date.now() + 1).toString(),
          type: "agent",
          message: response.data.response,
          timestamp: response.data.timestamp
        };
        setMessages(prev => [...prev, agentMsg]);
      } else {
        toast.error("Fehler beim Senden der Nachricht");
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          type: "error",
          message: response.data.response || "Fehler beim Kommunizieren mit NexusChat",
          timestamp: new Date().toISOString()
        }]);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Fehler beim Senden der Nachricht");
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        type: "error",
        message: "Fehler beim Kommunizieren mit NexusChat. Bitte versuche es erneut.",
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString("de-DE", { 
        hour: "2-digit", 
        minute: "2-digit" 
      });
    } catch {
      return "";
    }
  };

  return (
    <div className="flex flex-col h-full" data-testid="nexus-chat">
      {/* Chat Header */}
      <div className="flex items-center space-x-2 p-4 border-b border-indigo-500/20">
        <Bot className="w-5 h-5 text-indigo-400" />
        <h2 className="text-lg font-semibold text-white">NexusChat</h2>
        <span className="text-xs text-slate-400 ml-auto">
          User Interface Agent
        </span>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900/50">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.type === "user"
                  ? "bg-indigo-600 text-white"
                  : msg.type === "error"
                  ? "bg-red-500/20 text-red-400 border border-red-500/30"
                  : "bg-slate-800 text-slate-200 border border-indigo-500/30"
              }`}
            >
              {msg.type === "agent" && (
                <div className="flex items-center space-x-2 mb-1">
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-indigo-400">NexusChat</span>
                </div>
              )}
              <p className="text-sm whitespace-pre-wrap break-words">{msg.message}</p>
              <span className="text-xs opacity-70 mt-1 block">
                {formatTime(msg.timestamp)}
              </span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 text-slate-200 border border-indigo-500/30 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                <span className="text-sm">NexusChat denkt nach...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-indigo-500/20">
        <div className="flex space-x-2">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Schreibe eine Nachricht an NexusChat..."
            className="flex-1 bg-slate-800 border border-indigo-500/30 rounded-lg px-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 resize-none"
            rows="1"
            disabled={isLoading}
            style={{ minHeight: "44px", maxHeight: "120px" }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2 transition-colors touch-manipulation flex items-center justify-center"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Drücke Enter zum Senden, Shift+Enter für neue Zeile
        </p>
      </div>
    </div>
  );
};

export default NexusChat;

