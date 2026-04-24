import React, { useMemo, useState, useCallback } from "react";
import { buildAuthHeader } from "@shared/utils/helpers";
import { aiApi, apiFetch } from "../../api"; // Centralized wrapper
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
  const [model, setModel] = useState("tora");

  const authHeader = useMemo(() => buildAuthHeader(authToken || ""), [authToken]);
  const authMissing = !authHeader;
  const gatewayUrl = import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";
  const toraBaseUrl = import.meta.env.VITE_TORA_URL || aiBaseUrl || `${gatewayUrl}/ai`;

  // Handle tool call confirmation from the chat UI
  const handleConfirmTool = useCallback(async (messageIndex, tool) => {
    try {
      const toraEndpoint = `${toraBaseUrl.replace(/\/$/, "")}/ask-tora`;

      // Send a follow-up message that triggers the tool execution
      const confirmQuestion = `Please execute the ${tool.name} action with these parameters: ${JSON.stringify(tool.parameters)}`;

      const response = await apiFetch(toraEndpoint, {
        method: "POST",
        body: JSON.stringify({
          question: confirmQuestion,
          user_id: userId || 1,
          model: model,
        }),
      });

      const data = response;

      // Update the tool status in the original message
      setMessages((prev) => {
        const updated = [...prev];
        const msg = updated[messageIndex];
        if (msg?.toolCalls) {
          const toolIdx = msg.toolCalls.findIndex((t) => t.name === tool.name);
          if (toolIdx !== -1) {
            msg.toolCalls[toolIdx] = { ...msg.toolCalls[toolIdx], status: "executed" };
          }
        }
        return updated;
      });

      // Add a confirmation message
      const resultContent = data.answer && typeof data.answer === "object"
        ? data.answer["Financial Overview"] || "Action completed successfully."
        : data.answer || "Action completed.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resultContent,
          structured: typeof data.answer === "object" ? data.answer : null,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to execute the action. Please try again." },
      ]);
    }
  }, [toraBaseUrl, userId, model]);

  // Thumbs up/down feedback on an assistant bubble. Optimistic update,
  // silent failure — we don't want a flaky feedback call to disrupt chat.
  const handleFeedback = useCallback(async (msgIndex, rating) => {
    setMessages((prev) => {
      const next = [...prev];
      const m = next[msgIndex];
      if (!m || m.role !== "assistant") return prev;
      // If the user clicks the same rating again, clear it (toggle off).
      next[msgIndex] = { ...m, rating: m.rating === rating ? null : rating };
      return next;
    });

    try {
      const target = messages[msgIndex];
      if (!target) return;
      const preview = typeof target.content === "string"
        ? target.content.slice(0, 500)
        : JSON.stringify(target.content || target.structured || "").slice(0, 500);
      await aiApi.sendFeedback({
        user_id: userId || 1,
        rating,
        client_message_id: target.clientMessageId || null,
        prompt: target.prompt ? String(target.prompt).slice(0, 500) : null,
        response_preview: preview,
      });
    } catch (err) {
      console.warn("Feedback submit failed:", err);
    }
  }, [messages, userId]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || authMissing) return;

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const toraEndpoint = `${toraBaseUrl.replace(/\/$/, "")}/ask-tora`;

      const response = await apiFetch(toraEndpoint, {
        method: "POST",
        body: JSON.stringify({
          question: trimmed,
          user_id: userId || 1,
          model: model
        }),
      });

      const data = response; // apiFetch returns JSON directly

      // Build the message object. TORA returns either:
      //   - Simple mode: { mode: "simple", content: "...markdown..." }
      //   - Structured mode: { "Financial Overview": ..., "Current Position": ..., ... }
      // Stable id for this assistant bubble. Used as the feedback key so
      // re-clicks update the same row instead of creating duplicates.
      const clientMessageId =
        (typeof crypto !== "undefined" && crypto.randomUUID)
          ? `msg-${crypto.randomUUID()}`
          : `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const assistantMsg = {
        role: "assistant",
        content: "",
        clientMessageId,
        prompt: trimmed,
      };

      if (data.answer && typeof data.answer === "object") {
        const a = data.answer;

        if (a.error) {
          assistantMsg.content = `Error: ${a.error}`;
        } else if (a.mode === "simple" || typeof a.content === "string") {
          // SIMPLE MODE — conversational markdown reply, no section cards
          assistantMsg.mode = "simple";
          assistantMsg.content = a.content || "";
        } else {
          // STRUCTURED MODE — only attach sections that actually have content
          const sections = {};
          let hasAnySection = false;
          for (const key of ["Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"]) {
            const v = a[key];
            if (v && v !== "N/A") {
              sections[key] = v;
              hasAnySection = true;
            }
          }

          if (hasAnySection) {
            assistantMsg.structured = sections;
            assistantMsg.content = sections["Financial Overview"] || "Here's what I found.";
          } else {
            // No real structured content — fall back to simple mode
            assistantMsg.mode = "simple";
            assistantMsg.content = typeof a === "string" ? a : JSON.stringify(a);
          }
        }

        // Extract tool calls that need user confirmation
        if (a.tool_calls || data.tool_calls) {
          const tools = a.tool_calls || data.tool_calls || [];
          const pendingTools = tools.filter(
            (t) => t.status === "pending_confirmation"
          );
          if (pendingTools.length > 0) {
            assistantMsg.toolCalls = pendingTools;
          }
        }
      } else {
        assistantMsg.mode = "simple";
        assistantMsg.content = data.answer || "I couldn't generate a response.";
      }

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I couldn't reach TORA. Please ensure the AI service is running.",
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
        model={model}
        setModel={setModel}
        onConfirmTool={handleConfirmTool}
        onFeedback={handleFeedback}
      />
    </>
  );
}
