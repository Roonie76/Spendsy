import React, { useMemo, useState } from "react";
import { buildAuthHeader } from "../../../../../../packages/shared/utils/helpers";
import { apiFetch } from "../../api"; // Centralized wrapper
import FloatingAIButton from "./FloatingAIButton";
import AIChatPanel from "./AIChatPanel";

export default function AICopilot({ authToken, aiBaseUrl, userId }) {

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! I can summarize your spending, budgets, and next steps. Ask me anything.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const authHeader = useMemo(() => buildAuthHeader(authToken || ""), [authToken]);
  const authMissing = !authHeader;
  const endpoint = `${aiBaseUrl.replace(/\/$/, "")}/chat`;

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || authMissing) return;

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      // Use local spendsy-ai port 8005 for Ask Tora
      const toraEndpoint = "http://localhost:8005/ask-tora";

      const response = await apiFetch(toraEndpoint, {
        method: "POST",
        body: JSON.stringify({
          question: trimmed,
          user_id: userId || 1
        }),
      });

      const data = response; // apiFetch returns JSON directly
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer || "I couldn't generate a response." },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I couldn't reach Tora (Local AI). Please ensure Ollama and the AI service are running.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <>
      <FloatingAIButton isOpen={isOpen} onClick={() => setIsOpen(true)} />
      <AIChatPanel
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        messages={messages}
        input={input}
        setInput={setInput}
        onSend={handleSend}
        isLoading={isLoading}
        authMissing={authMissing}
      />
    </>
  );
}
