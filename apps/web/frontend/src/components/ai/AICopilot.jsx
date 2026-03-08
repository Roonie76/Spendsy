import React, { useMemo, useState } from "react";
import { buildAuthHeader } from "../../../../../../packages/shared/utils/helpers";
import FloatingAIButton from "./FloatingAIButton";
import AIChatPanel from "./AIChatPanel";

export default function AICopilot({ authToken, aiBaseUrl }) {
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
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: authHeader,
        },
        body: JSON.stringify({ message: trimmed }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || "AI service error");
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply || "I couldn't generate a response." },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I couldn't reach the AI service. Please try again in a moment.",
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
