"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  useState, useRef, useEffect, useCallback, KeyboardEvent,
} from "react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { postChatStream } from "@/lib/api";
import { ChatMessage } from "@/types";
import {
  MessageSquare, X, Send, Loader2, RotateCcw,
  Bot, User, ChevronDown, Sparkles,
} from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  loadingState?: "typing";
}

interface Props {
  comparisonId: string;
  doc1Name: string;
  doc2Name: string;
}

const STARTERS = [
  "What are the highest-risk changes in this comparison?",
  "Which changes require immediate legal review?",
  "Summarise the regulatory compliance impact.",
  "Are there any data privacy concerns I should flag?",
  "What recommendations should I prioritise?",
];

let _msgCounter = 0;
function newId() { return `msg_${++_msgCounter}`; }

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const content = msg.content.replace(/\\n/g, "\n");

  return (
    <div className={cn("flex items-start gap-2", isUser ? "flex-row-reverse" : "flex-row")}>
      <div className={cn(
        "w-6 h-6 sm:w-7 sm:h-7 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5",
        isUser
          ? "bg-amber-500/20 border border-amber-500/30"
          : "bg-sapphire-500/10 border border-sapphire-500/20",
      )}>
        {isUser
          ? <User className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-amber-400" />
          : <Bot className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-sapphire-400" />}
      </div>

      <div className={cn(
        "max-w-[85%] rounded-2xl px-3 sm:px-4 py-2 sm:py-2.5 text-sm leading-relaxed",
        isUser
          ? "bg-amber-500/10 border border-amber-500/20 text-ink-100 rounded-tr-sm"
          : "bg-ink-800 border border-ink-700 text-ink-200 rounded-tl-sm",
      )}>
        {msg.loadingState === "typing" ? (
          <span className="flex items-center gap-2 text-ink-500">
            <span className="text-xs italic">Typing…</span>
          </span>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="text-sm leading-relaxed whitespace-pre-wrap m-0">{children}</p>
              ),
              li: ({ children }) => (
                <li className="ml-4 list-disc text-sm leading-relaxed">{children}</li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold">{children}</strong>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}


export default function ComparisonChat({ comparisonId, doc1Name, doc2Name }: Props) {
  const { token } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  const send = useCallback(async (content: string) => {
    const text = content.trim();
    if (!text || streaming) return;

    const userMsg: Message = { id: newId(), role: "user", content: text };
    const loadingMsg: Message = { id: newId(), role: "assistant", content: "", loadingState: "typing" };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setDraft("");
    setError(null);
    setStreaming(true);

    const history: ChatMessage[] = [
      ...messages.map(m => ({ role: m.role, content: m.content })),
      { role: "user", content: text },
    ];

    let assembled = "";

    try {
      const res = await postChatStream(comparisonId, history, token);

      if (!res.ok) {
        throw new Error(`${res.status} ${res.statusText}`);
      }
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        const lines = raw.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const chunk = line.slice(6);
          if (chunk === "[DONE]") break;
          assembled += chunk;
          setMessages(prev =>
            prev.map(m => {
              if (m.id !== loadingMsg.id) return m;
              const next: Message = { ...m, content: assembled };
              if (m.loadingState === "typing") {
                delete next.loadingState;
              }
              return next;
            })
          );
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setError(msg);
      setMessages(prev =>
        prev.map(m => {
          if (m.id !== loadingMsg.id) return m;
          const next: Message = { ...m, content: `⚠ ${msg}` };
          if (next.loadingState === "typing") {
            delete next.loadingState;
          }
          return next;
        })
      );
    } finally {
      setStreaming(false);
    }
  }, [comparisonId, messages, streaming, token]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(draft);
    }
  };

  const reset = () => {
    setMessages([]);
    setError(null);
    setDraft("");
  };

  const unread = !open && messages.filter(m => m.role === "assistant" && !m.loadingState).length > 0;

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(!open)}
        title="Chat about this comparison"
        className={cn(
          "fixed bottom-4 sm:bottom-6 right-4 sm:right-6 z-50",
          "w-12 h-12 sm:w-14 sm:h-14 rounded-2xl shadow-2xl",
          "flex items-center justify-center",
          "transition-all duration-200",
          open
            ? "bg-ink-800 border border-ink-600 text-ink-300"
            : "bg-amber-500 hover:bg-amber-400 text-ink-950",
        )}
      >
        {open
          ? <ChevronDown className="w-5 h-5" />
          : <MessageSquare className="w-5 h-5" />}

        {unread && (
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-jade-500 border-2 border-ink-950" />
        )}
      </button>

      {/* Chat panel */}
      <div className={cn(
        "fixed z-40",
        // Mobile: full screen bottom sheet; Desktop: floating panel
        "bottom-0 right-0 left-0 sm:bottom-24 sm:right-6 sm:left-auto",
        "w-full sm:w-[420px] sm:max-w-[calc(100vw-3rem)]",
        "flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden",
        "border border-ink-700 shadow-2xl shadow-ink-950/80",
        "transition-all duration-300 origin-bottom sm:origin-bottom-right",
        open
          ? "opacity-100 scale-100 pointer-events-auto"
          : "opacity-0 scale-95 pointer-events-none",
      )}>

        {/* Header */}
        <div className="flex items-center gap-2.5 px-4 py-3 bg-ink-900 border-b border-ink-800">
          <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-ink-200">Comparison Assistant</p>
            <p className="text-xs text-ink-600 truncate">
              {doc1Name} ↔ {doc2Name}
            </p>
          </div>
          <button
            onClick={reset}
            disabled={messages.length === 0}
            title="Clear conversation"
            className="p-1.5 rounded-lg text-ink-600 hover:text-ink-300 hover:bg-ink-800 disabled:opacity-30 transition-all"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setOpen(false)}
            className="p-1.5 rounded-lg text-ink-600 hover:text-ink-300 hover:bg-ink-800 transition-all"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-ink-950 px-3 sm:px-4 py-4 space-y-3 sm:space-y-4 min-h-[280px] sm:min-h-[320px] max-h-[50vh] sm:max-h-[420px]">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 sm:gap-5 py-4 sm:py-6">
              <div className="text-center">
                <Bot className="w-8 h-8 text-ink-700 mx-auto mb-2" />
                <p className="text-sm text-ink-500 font-medium">Ask anything about this comparison</p>
                <p className="text-xs text-ink-700 mt-1">
                  Conversation is session-only and not stored
                </p>
              </div>

              <div className="w-full space-y-2">
                {STARTERS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    disabled={streaming}
                    className="w-full text-left px-3 py-2 rounded-xl border border-ink-800 bg-ink-900 text-xs text-ink-400 hover:border-amber-500/30 hover:text-ink-200 hover:bg-ink-800 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Error bar */}
        {error && (
          <div className="px-4 py-2 bg-crimson-950/60 border-t border-crimson-800/50 text-xs text-crimson-400">
            {error}
          </div>
        )}

        {/* Input */}
        <div className="px-3 py-3 bg-ink-900 border-t border-ink-800 flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about this comparison… (↵ send)"
            rows={1}
            disabled={streaming}
            className={cn(
              "flex-1 bg-ink-950 border border-ink-800 rounded-xl px-3 py-2.5",
              "text-sm text-ink-200 placeholder-ink-700 resize-none",
              "focus:outline-none focus:border-amber-500/40 transition-colors",
              "max-h-28 overflow-y-auto",
              "disabled:opacity-50",
            )}
            style={{ height: "auto" }}
            onInput={e => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 112)}px`;
            }}
          />
          <button
            onClick={() => send(draft)}
            disabled={!draft.trim() || streaming}
            className={cn(
              "flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center",
              "transition-all",
              draft.trim() && !streaming
                ? "bg-amber-500 hover:bg-amber-400 text-ink-950"
                : "bg-ink-800 text-ink-600 cursor-not-allowed",
            )}
          >
            {streaming
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </>
  );
}
