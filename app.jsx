import { useEffect, useRef, useState } from "react";
const OLLAMA_API_URL =
  import.meta.env.VITE_OLLAMA_API_URL || "http://localhost:11434/api/generate";
const OLLAMA_MODEL = import.meta.env.VITE_OLLAMA_MODEL || "mistral";
const STARTER_PROMPTS = [
  "What is a healthy BMI for my age?",
  "How many calories should I eat daily?",
  "What does my blood pressure reading mean?",
  "How can I improve my resting heart rate?",
  "What foods reduce inflammation?",
  "Summarize my report",
];
function createAssistantWelcomeMessage() {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content: "Hi! I am your local Mistral assistant. Ask me anything.",
  };
}
function createNewChat(title = "New Conversation") {
  return {
    id: crypto.randomUUID(),
    title,
    messages: [createAssistantWelcomeMessage()],
    updatedAt: Date.now(),
  };
}
function buildPrompt(history, userInput) {
  const transcript = history
    .map((msg) => `${msg.role === "user" ? "User" : "Assistant"}: ${msg.content}`)
    .join("\n");
  return `${transcript}\nUser: ${userInput}\nAssistant:`;
}
export default function App() {
  const [chats, setChats] = useState([createNewChat()]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [controller, setController] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historySearch, setHistorySearch] = useState("");
  const [editingChatId, setEditingChatId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [searchEnabled, setSearchEnabled] = useState(false);
  const [privateMode, setPrivateMode] = useState(true);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const editingInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const selectedChatId = activeChatId ?? chats[0]?.id;
  const activeChat = chats.find((chat) => chat.id === selectedChatId) ?? chats[0];
  const messages = activeChat?.messages ?? [];
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [selectedChatId, messages, isLoading]);
  useEffect(() => {
    return () => controller?.abort();
  }, [controller]);
  useEffect(() => {
    if (!activeChatId && chats.length > 0) {
      setActiveChatId(chats[0].id);
    }
  }, [activeChatId, chats]);
  useEffect(() => {
    if (editingChatId) {
      editingInputRef.current?.focus();
      editingInputRef.current?.select();
    }
  }, [editingChatId]);
  const updateChat = (chatId, updater) => {
    setChats((current) =>
      current.map((chat) => (chat.id === chatId ? { ...chat, ...updater(chat) } : chat))
    );
  };
  const autoTitleFromPrompt = (prompt) => {
    const compact = prompt.replace(/\s+/g, " ").trim();
    return compact.length > 40 ? `${compact.slice(0, 40)}...` : compact;
  };
  const startNewConversation = () => {
    const freshChat = createNewChat();
    setChats((current) => [freshChat, ...current]);
    setActiveChatId(freshChat.id);
    setError("");
    setInput("");
    setSidebarOpen(false);
    textareaRef.current?.focus();
  };
  const deleteChat = (chatId) => {
    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== chatId);
      if (remaining.length > 0) return remaining;
      return [createNewChat()];
    });
    if (selectedChatId === chatId) {
      setActiveChatId(null);
    }
  };
  const deleteAllHistory = () => {
    const freshChat = createNewChat();
    setChats([freshChat]);
    setActiveChatId(freshChat.id);
    setError("");
    setInput("");
    setEditingChatId(null);
    setSidebarOpen(false);
  };
  const startEditingChat = (chat) => {
    setEditingChatId(chat.id);
    setEditingTitle(chat.title);
  };
  const saveEditingChat = () => {
    if (!editingChatId) return;
    const nextTitle = editingTitle.trim() || "Untitled Chat";
    updateChat(editingChatId, () => ({ title: nextTitle, updatedAt: Date.now() }));
    setEditingChatId(null);
    setEditingTitle("");
  };
  const visibleChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(historySearch.toLowerCase())
  );
  const handleAttachFiles = (event) => {
    const selected = Array.from(event.target.files || []);
    if (selected.length === 0) return;
    setAttachedFiles((current) => {
      const existingKeys = new Set(current.map((file) => `${file.name}-${file.size}`));
      const unique = selected.filter(
        (file) => !existingKeys.has(`${file.name}-${file.size}`)
      );
      return [...current, ...unique];
    });
    event.target.value = "";
  };
  const removeAttachedFile = (indexToRemove) => {
    setAttachedFiles((current) =>
      current.filter((_, index) => index !== indexToRemove)
    );
  };
  const submitPrompt = async (text) => {
    const rawInput = text.trim();
    const attachmentSuffix =
      attachedFiles.length > 0
        ? `\n\nAttached files: ${attachedFiles.map((file) => file.name).join(", ")}`
        : "";
    const userInput = `${rawInput}${attachmentSuffix}`.trim();
    if (!userInput || isLoading || !activeChat) return;
    setError("");
    setInput("");
    setAttachedFiles([]);
    const targetChatId = activeChat.id;
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: userInput,
    };
    const shouldRename = activeChat.title === "New Conversation" && messages.length <= 1;
    updateChat(targetChatId, (chat) => ({
      messages: [...chat.messages, userMessage],
      title: shouldRename ? autoTitleFromPrompt(userInput) : chat.title,
      updatedAt: Date.now(),
    }));
    setIsLoading(true);
    const abortController = new AbortController();
    setController(abortController);
    try {
      const response = await fetch(OLLAMA_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        signal: abortController.signal,
        body: JSON.stringify({
          model: OLLAMA_MODEL,
          prompt: buildPrompt(messages, userInput),
          stream: false,
        }),
      });
      if (!response.ok) {
        throw new Error(`Ollama request failed with status ${response.status}`);
      }
      const data = await response.json();
      const aiText = data.response?.trim() || "No response from model.";
      updateChat(targetChatId, (chat) => ({
        messages: [
          ...chat.messages,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: aiText,
          },
        ],
        updatedAt: Date.now(),
      }));
    } catch (requestError) {
      if (requestError.name !== "AbortError") {
        setError(
          "Unable to reach Ollama. Make sure Ollama is running and model 'mistral' is available."
        );
      }
    } finally {
      setIsLoading(false);
      setController(null);
      textareaRef.current?.focus();
    }
  };
  const handleSubmit = async (event) => {
    event.preventDefault();
    await submitPrompt(input);
  };
  const sendPrompt = async (promptText) => {
    await submitPrompt(promptText);
  };
  const hasConversation = messages.length > 1;
  return (
    <div className="page-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark">◎</div>
          <span className="brand-name">BodyMatrix</span>
        </div>
        <input
          className="history-search"
          type="text"
          placeholder="Search chats..."
          value={historySearch}
          onChange={(event) => setHistorySearch(event.target.value)}
        />
        <button className="new-chat-btn" type="button" onClick={startNewConversation}>
          + New chat
        </button>
        <div className="history-header">
          <span className="history-label">History</span>
          <button className="delete-all-btn" type="button" onClick={deleteAllHistory}>
            Delete all
          </button>
        </div>
        <div className="history-list">
          {visibleChats.map((chat) => {
            const isEditing = editingChatId === chat.id;
            return (
              <div
                key={chat.id}
                className={`history-item ${chat.id === selectedChatId ? "active" : ""}`}
              >
                {isEditing ? (
                  <input
                    ref={editingInputRef}
                    className="history-edit-input"
                    value={editingTitle}
                    onChange={(event) => setEditingTitle(event.target.value)}
                    onBlur={saveEditingChat}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") saveEditingChat();
                      if (event.key === "Escape") setEditingChatId(null);
                    }}
                  />
                ) : (
                  <button
                    type="button"
                    className="history-title-btn"
                    onClick={() => {
                      setActiveChatId(chat.id);
                      setSidebarOpen(false);
                      setError("");
                    }}
                  >
                    {chat.title}
                  </button>
                )}
                <div className="history-actions">
                  <button
                    type="button"
                    className="history-action-btn"
                    aria-label="Edit chat title"
                    onClick={() => startEditingChat(chat)}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    className="history-action-btn"
                    aria-label="Delete chat"
                    onClick={() => deleteChat(chat.id)}
                  >
                    🗑
                  </button>
                </div>
              </div>
            );
          })}
          {visibleChats.length === 0 && (
            <p className="empty-history">No chat history found.</p>
          )}
        </div>
        <div className="sidebar-footer">Private • BodyMatrix AI</div>
      </aside>
      <div className="app-shell">
        <header className="app-header">
          <button
            className="icon-btn mobile-only"
            type="button"
            aria-label="Open menu"
            onClick={() => setSidebarOpen((value) => !value)}
          >
            ☰
          </button>
          <div className="header-switches">
            <button
              type="button"
              className={`switch-pill ${searchEnabled ? "on" : ""}`}
              onClick={() => setSearchEnabled((value) => !value)}
            >
              <span>Search</span>
              <span className="switch-knob" />
            </button>
            <button
              type="button"
              className={`switch-pill ${privateMode ? "on" : ""}`}
              onClick={() => setPrivateMode((value) => !value)}
            >
              <span>Private</span>
              <span className="switch-knob" />
            </button>
          </div>
        </header>
        {sidebarOpen && (
          <div className="mobile-sidebar-overlay" onClick={() => setSidebarOpen(false)}>
            <div
              className="mobile-sidebar-sheet"
              onClick={(event) => event.stopPropagation()}
              role="dialog"
              aria-modal="true"
            >
              <div className="brand-row">
                <div className="brand-mark">◎</div>
                <span className="brand-name">BodyMatrix</span>
              </div>
              <input
                className="history-search"
                type="text"
                placeholder="Search chats..."
                value={historySearch}
                onChange={(event) => setHistorySearch(event.target.value)}
              />
              <button className="new-chat-btn" type="button" onClick={startNewConversation}>
                + New chat
              </button>
              <div className="history-header">
                <span className="history-label">History</span>
                <button className="delete-all-btn" type="button" onClick={deleteAllHistory}>
                  Delete all
                </button>
              </div>
              <div className="history-list">
                {visibleChats.map((chat) => (
                  <div
                    key={`mobile-${chat.id}`}
                    className={`history-item ${chat.id === selectedChatId ? "active" : ""}`}
                  >
                    <button
                      type="button"
                      className="history-title-btn"
                      onClick={() => {
                        setActiveChatId(chat.id);
                        setSidebarOpen(false);
                      }}
                    >
                      {chat.title}
                    </button>
                    <div className="history-actions">
                      <button
                        type="button"
                        className="history-action-btn"
                        aria-label="Edit chat title"
                        onClick={() => startEditingChat(chat)}
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        className="history-action-btn"
                        aria-label="Delete chat"
                        onClick={() => deleteChat(chat.id)}
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        <main className="chat-feed">
          {!hasConversation && (
            <section className="welcome-panel">
              <h1>How can I help you today?</h1>
              <p>
                Ask me about your health data, BMI, nutrition, fitness goals, or
                anything health-related.
              </p>
              <div className="starter-grid">
                {STARTER_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="prompt-pill"
                    onClick={async () => sendPrompt(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </section>
          )}
          {hasConversation && (
            <section className="messages-panel">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`message-row ${message.role === "user" ? "user" : "assistant"}`}
                >
                  <div className="message-bubble">
                    <p>{message.content}</p>
                  </div>
                </article>
              ))}
              {isLoading && (
                <article className="message-row assistant">
                  <div
                    className="message-bubble typing-indicator"
                    aria-label="Assistant is typing"
                  >
                    <span />
                    <span />
                    <span />
                    <small>Analyzing data...</small>
                  </div>
                </article>
              )}
            </section>
          )}
          {error && <p className="error-text">{error}</p>}
          <div ref={messagesEndRef} />
        </main>
        <form className="chat-input-wrap" onSubmit={handleSubmit}>
          {attachedFiles.length > 0 && (
            <div className="attachment-list">
              {attachedFiles.map((file, index) => (
                <div key={`${file.name}-${file.size}-${index}`} className="attachment-chip">
                  <span>{file.name}</span>
                  <button
                    type="button"
                    className="attachment-remove-btn"
                    aria-label={`Remove ${file.name}`}
                    onClick={() => removeAttachedFile(index)}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          <textarea
            ref={textareaRef}
            className="chat-input"
            rows={1}
            placeholder="Ask anything..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event);
              }
            }}
          />
          <div className="input-actions">
            <input
              ref={fileInputRef}
              className="hidden-file-input"
              type="file"
              multiple
              onChange={handleAttachFiles}
            />
            <button
              className="tool-btn clip-btn"
              type="button"
              aria-label="Attach file"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M7 12.5 13.4 6.1a3.5 3.5 0 1 1 5 5L10 19.5a5 5 0 1 1-7-7L12 3.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            {isLoading && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => controller?.abort()}
              >
                Stop
              </button>
            )}
            <button type="submit" className="btn" disabled={isLoading || !input.trim()}>
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}