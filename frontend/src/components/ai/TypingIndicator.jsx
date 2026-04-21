import React from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 max-w-[70%]">
      <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10">
        <Sparkles className="h-3 w-3 text-cyan-300" />
      </span>
      <div className="rounded-2xl bg-white/10 px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-2 w-2 rounded-full bg-cyan-400/60"
            animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 1,
              repeat: Infinity,
              delay: i * 0.2,
              ease: "easeInOut",
            }}
          />
        ))}
        <span className="ml-2 text-xs text-slate-500">Tora is thinking...</span>
      </div>
    </div>
  );
}
