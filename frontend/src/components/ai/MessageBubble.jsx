import React, { useState } from "react";
import { ChevronDown, ChevronRight, TrendingUp, Target, Lightbulb, BarChart3, ThumbsUp, ThumbsDown, ArrowRight, CheckCircle2, AlertCircle } from "lucide-react";

const SECTION_CONFIG = {
  "Financial Overview": { icon: BarChart3, color: "text-cyan-400", bg: "bg-cyan-500/10" },
  "Current Position": { icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  "Recommended Strategy": { icon: Lightbulb, color: "text-amber-400", bg: "bg-amber-500/10" },
  "Expected Outcome": { icon: Target, color: "text-purple-400", bg: "bg-purple-500/10" },
};

function renderInlineMarkdown(text) {
  if (!text || typeof text !== "string") return text;

  // Split by bold markers **...**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function renderMarkdown(text) {
  if (!text || typeof text !== "string") return null;

  const lines = text.split("\n");
  const elements = [];
  let listItems = [];
  let tableRows = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="ml-4 my-2 space-y-1">
          {listItems.map((item, i) => (
            <li key={i} className="flex gap-2 text-slate-300">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400/60" />
              <span>{renderInlineMarkdown(item)}</span>
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  const flushTable = () => {
    if (tableRows.length > 0) {
      // Basic table detection/rendering
      const headers = tableRows[0].split("|").filter(Boolean).map(s => s.trim());
      const body = tableRows.slice(2).map(row => row.split("|").filter(Boolean).map(s => s.trim()));

      elements.push(
        <div key={`table-${elements.length}`} className="my-3 overflow-x-auto rounded-xl border border-white/10 bg-white/5">
          <table className="w-full text-left text-[11px] border-collapse">
            <thead>
              <tr className="bg-white/10">
                {headers.map((h, i) => (
                  <th key={i} className="px-3 py-2 font-bold text-cyan-300 border-b border-white/10">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row, i) => (
                <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                  {row.map((cell, j) => (
                    <td key={j} className="px-3 py-2 text-slate-300">{renderInlineMarkdown(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      tableRows = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (!line) {
      flushList();
      flushTable();
      continue;
    }

    // Table rows detection (| col1 | col2 |)
    if (line.startsWith("|") && line.endsWith("|")) {
      flushList();
      tableRows.push(line);
      continue;
    }

    // Headings (### Heading)
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/);
    if (headingMatch) {
      flushList();
      flushTable();
      const level = headingMatch[1].length;
      elements.push(
        <h4 key={`h-${i}`} className={`mt-3 mb-1 font-bold text-slate-100 ${level === 1 ? 'text-lg' : 'text-sm'}`}>
          {renderInlineMarkdown(headingMatch[2])}
        </h4>
      );
      continue;
    }

    // Horizontal Rule (---)
    if (line === "---" || line === "***") {
      flushList();
      flushTable();
      elements.push(<hr key={`hr-${i}`} className="my-4 border-white/10" />);
      continue;
    }

    // Bullet list items
    const bulletMatch = line.match(/^[-*+]\s+(.+)/);
    if (bulletMatch) {
      flushTable();
      listItems.push(bulletMatch[1]);
      continue;
    }

    // Numbered list items
    const numberedMatch = line.match(/^\d+[.)]\s+(.+)/);
    if (numberedMatch) {
      flushTable();
      listItems.push(numberedMatch[1]);
      continue;
    }

    flushList();
    flushTable();
    elements.push(
      <p key={`p-${i}`} className="text-slate-300 leading-relaxed mb-2">
        {renderInlineMarkdown(line)}
      </p>
    );
  }

  flushList();
  flushTable();
  return elements;
}

function RichUIBlock({ data }) {
  if (!data) return null;

  const { type, payload } = data;

  if (type === "mini_chart") {
    const max = Math.max(...payload.values);
    return (
      <div className="my-4 p-4 rounded-2xl bg-white/5 border border-white/10">
        <h5 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">{payload.title}</h5>
        <div className="flex items-end gap-2 h-24">
          {payload.values.map((v, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
              <div 
                className="w-full bg-cyan-500/30 rounded-t-md group-hover:bg-cyan-500 transition-all"
                style={{ height: `${(v / max) * 100}%` }}
              />
              <span className="text-[8px] text-slate-500 font-bold uppercase truncate w-full text-center">{payload.labels[i]}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "action_button") {
    return (
      <div className="my-3 flex flex-wrap gap-2">
        {payload.actions.map((action, i) => (
          <button
            key={i}
            onClick={() => window.dispatchEvent(new CustomEvent('TORA_ACTION', { detail: action }))}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-[11px] font-bold transition-all shadow-lg active:scale-95 ${
              action.intent === "danger" 
                ? "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/20" 
                : "bg-white/10 hover:bg-white/20 text-white border border-white/10"
            }`}
          >
            {action.intent === "fix" ? <AlertCircle size={14} className="text-amber-400" /> : <ArrowRight size={14} />}
            {action.label}
          </button>
        ))}
      </div>
    );
  }

  return null;
}

function parseRichContent(content) {
  if (typeof content !== "string") return { text: content, blocks: [] };
  
  const blocks = [];
  let cleanText = content;

  // Pattern for JSON blocks: [UI_BLOCK:{"type": "...", "payload": {...}}]
  const blockRegex = /\[UI_BLOCK:(\{.*?\})\]/g;
  let match;
  while ((match = blockRegex.exec(content)) !== null) {
    try {
      const data = JSON.parse(match[1]);
      blocks.push(data);
      cleanText = cleanText.replace(match[0], "");
    } catch (e) {
      console.error("Failed to parse UI_BLOCK", e);
    }
  }

  return { text: cleanText.trim(), blocks };
}

function SectionCard({ title, content }) {
  const [isOpen, setIsOpen] = useState(true);
  const config = SECTION_CONFIG[title] || SECTION_CONFIG["Financial Overview"];
  const Icon = config.icon;

  if (!content || content === "N/A") return null;

  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.03] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left hover:bg-white/[0.03] transition-colors"
      >
        <span className={`flex h-6 w-6 items-center justify-center rounded-lg ${config.bg}`}>
          <Icon className={`h-3.5 w-3.5 ${config.color}`} />
        </span>
        <span className={`text-[11px] font-bold uppercase tracking-wider ${config.color} flex-1`}>{title}</span>
        {isOpen ? (
          <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
        )}
      </button>
      {isOpen && (
        <div className="px-3 pb-3 space-y-1 text-[13px] leading-relaxed border-t border-white/[0.02] pt-2">
          {renderMarkdown(content)}
        </div>
      )}
    </div>
  );
}

export default function MessageBubble({ message }) {
  const { role, content, structured, toolCalls, onConfirmTool, onFeedback, rating } = message;

  if (role === "user") {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[85%] rounded-2xl rounded-tr-none bg-gradient-to-br from-cyan-600/30 to-blue-600/30 border border-cyan-500/20 px-4 py-3 text-[13px] leading-relaxed text-cyan-50 shadow-lg backdrop-blur-sm">
          {content}
        </div>
      </div>
    );
  }

  // Assistant message — check if it has structured sections or if it was returned as a content object
  const hasSections = (typeof content === "object" && content !== null && !message.mode) || 
                      (structured && Object.keys(SECTION_CONFIG).some(k => structured[k] && structured[k] !== "N/A"));

  const sectionData = structured || content;
  const rich = parseRichContent(typeof content === "string" ? content : (content?.content || ""));

  return (
    <div className="max-w-[92%] space-y-3 mb-6">
      {hasSections ? (
        <div className="space-y-2">
          {Object.keys(SECTION_CONFIG).map((key) => (
            <SectionCard key={key} title={key} content={sectionData[key]} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-2xl bg-[#1e293b]/50 border border-white/5 px-4 py-4 text-[14px] leading-relaxed text-slate-200 shadow-xl backdrop-blur-md">
            {renderMarkdown(rich.text)}
          </div>
          {rich.blocks.map((block, i) => <RichUIBlock key={i} data={block} />)}
        </div>
      )}

      {/* Thumbs up/down feedback — shown on all assistant messages except welcome */}
      {onFeedback && (
        <FeedbackBar rating={rating} onFeedback={onFeedback} />
      )}

      {/* Tool call confirmation cards */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="space-y-1.5">
          {toolCalls.map((tool, idx) => (
            <ToolCallConfirmCard
              key={idx}
              tool={tool}
              onConfirm={() => onConfirmTool?.(tool, idx)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function FeedbackBar({ rating, onFeedback }) {
  return (
    <div className="flex items-center gap-1 pl-1">
      <button
        type="button"
        onClick={() => onFeedback("up")}
        aria-label="Helpful"
        className={`group flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-all ${
          rating === "up"
            ? "bg-emerald-500/15 text-emerald-400"
            : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
        }`}
      >
        <ThumbsUp className={`h-3 w-3 ${rating === "up" ? "fill-emerald-400" : ""}`} />
      </button>
      <button
        type="button"
        onClick={() => onFeedback("down")}
        aria-label="Not helpful"
        className={`group flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] transition-all ${
          rating === "down"
            ? "bg-rose-500/15 text-rose-400"
            : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
        }`}
      >
        <ThumbsDown className={`h-3 w-3 ${rating === "down" ? "fill-rose-400" : ""}`} />
      </button>
    </div>
  );
}

function ToolCallConfirmCard({ tool, onConfirm }) {
  const [confirmed, setConfirmed] = useState(false);
  const isPending = tool.status === "pending_confirmation";
  const name = tool.name || "Unknown Action";
  const params = tool.parameters || {};

  // Build a human-readable summary
  const summary = params.title
    ? `"${params.title}"`
    : params.reasoning
      ? params.reasoning.slice(0, 80)
      : name.replace(/_/g, " ");

  const handleConfirm = () => {
    setConfirmed(true);
    onConfirm?.();
  };

  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2.5">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-amber-500/20">
          <Target className="h-3 w-3 text-amber-400" />
        </span>
        <span className="text-xs font-semibold text-amber-300">
          {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </span>
      </div>
      <p className="text-[12px] text-slate-400 mb-2">{summary}</p>

      {isPending && !confirmed ? (
        <button
          onClick={handleConfirm}
          className="rounded-lg bg-amber-500/20 px-3 py-1.5 text-[11px] font-semibold text-amber-300 hover:bg-amber-500/30 transition-colors"
        >
          Confirm Action
        </button>
      ) : (
        <span className="text-[11px] text-emerald-400 font-medium">
          {confirmed ? "Confirmed" : "Executed"}
        </span>
      )}
    </div>
  );
}
