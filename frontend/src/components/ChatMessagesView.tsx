import type React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Copy, CopyCheck, RefreshCw, Sparkles } from "lucide-react";
import { InputForm } from "@/components/InputForm";
import { Button } from "@/components/ui/button";
import { useMemo, useState, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from 'remark-gfm';
import { cn } from "@/utils";
import { Badge } from "@/components/ui/badge";
import { ActivityTimeline } from "@/components/ActivityTimeline";
import { StatusBadge } from "@/components/ui/status-badge";
import { StatPill } from "@/components/ui/stat-pill";

// Markdown component props type from former ReportView
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  [key: string]: any;
};

interface ProcessedEvent {
  title: string;
  data: any;
}

// Markdown components (from former ReportView.tsx)
const mdComponents = {
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <Badge className="text-xs mx-0.5">
      <a
        className={cn("text-blue-400 hover:text-blue-300 text-xs", className)}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    </Badge>
  ),
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul className={cn("list-disc pl-6 mb-3", className)} {...props}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol className={cn("list-decimal pl-6 mb-3", className)} {...props}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li className={cn("mb-1", className)} {...props}>
      {children}
    </li>
  ),
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      className={cn(
        "border-l-4 border-neutral-600 pl-4 italic my-3 text-sm",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      className={cn(
        "bg-neutral-900 rounded px-1 py-0.5 font-mono text-xs",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      className={cn(
        "bg-neutral-900 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr className={cn("border-neutral-600 my-4", className)} {...props} />
  ),
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div className="my-3 overflow-x-auto">
      <table className={cn("border-collapse w-full", className)} {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      className={cn(
        "border border-neutral-600 px-3 py-2 text-left font-bold",
        className
      )}
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      className={cn("border border-neutral-600 px-3 py-2", className)}
      {...props}
    >
      {children}
    </td>
  ),
};

// Props for HumanMessageBubble
interface HumanMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
}

// HumanMessageBubble Component
const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
  mdComponents,
}) => {
  return (
    <div className="max-w-full sm:max-w-[85%]">
      <div className="chat-bubble-scroll overflow-x-auto break-words rounded-3xl border border-border/70 bg-secondary/70 px-5 py-3 pb-4 text-sm leading-relaxed text-foreground/90 shadow-[0_18px_38px_-22px_rgba(10,16,28,0.55)]">
        <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

// Props for AiMessageBubble
interface AiMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
  agent?: string;
  finalReportWithCitations?: boolean;
  processedEvents: ProcessedEvent[];
  websiteCount: number;
  isLoading: boolean;
}

// AiMessageBubble Component
const AiMessageBubble: React.FC<AiMessageBubbleProps> = ({
  message,
  mdComponents,
  handleCopy,
  copiedMessageId,
  agent,
  finalReportWithCitations,
  processedEvents,
  websiteCount,
  isLoading,
}) => {
  // Show ActivityTimeline if we have processedEvents (this will be the first AI message)
  const shouldShowTimeline = processedEvents.length > 0;

  // Condition for DIRECT DISPLAY (interactive_planner_agent OR final report)
  const shouldDisplayDirectly =
    agent === "interactive_planner_agent" ||
    (agent === "report_composer_with_citations" && finalReportWithCitations);

  if (shouldDisplayDirectly) {
    // Direct display - show content with copy button, and timeline if available
    return (
      <div className="relative flex w-full flex-col gap-3">
        {/* Show timeline for interactive_planner_agent if available */}
        {shouldShowTimeline && agent === "interactive_planner_agent" && (
          <div className="w-full rounded-2xl border border-border/60 bg-muted/50 p-4">
            <ActivityTimeline
              processedEvents={processedEvents}
              isLoading={isLoading}
              websiteCount={websiteCount}
            />
          </div>
        )}
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="chat-bubble-scroll overflow-x-auto break-words rounded-3xl border border-border/60 bg-secondary/80 px-5 py-4 pb-5 text-sm leading-relaxed text-foreground/90 shadow-[0_18px_42px_-24px_rgba(10,16,28,0.65)]">
              <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
          <button
            onClick={() => handleCopy(message.content, message.id)}
            className="rounded-full border border-border/60 bg-muted/60 p-2 text-muted-foreground transition hover:border-border hover:bg-muted/70"
          >
            {copiedMessageId === message.id ? (
              <CopyCheck className="h-4 w-4 text-emerald-400" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    );
  } else if (shouldShowTimeline) {
    // First AI message with timeline only (no direct content display)
    return (
      <div className="relative flex w-full flex-col gap-3">
        <div className="w-full rounded-2xl border border-border/60 bg-muted/50 p-4">
          <ActivityTimeline
            processedEvents={processedEvents}
            isLoading={isLoading}
            websiteCount={websiteCount}
          />
        </div>
        {/* Only show accumulated content if it's not empty and not from research agents */}
        {message.content && message.content.trim() && agent !== "interactive_planner_agent" && (
          <div className="mt-1 flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="chat-bubble-scroll overflow-x-auto break-words rounded-3xl border border-border/60 bg-secondary/80 px-5 py-4 pb-5 text-sm leading-relaxed text-foreground/90 shadow-[0_18px_42px_-24px_rgba(10,16,28,0.65)]">
                <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
            <button
              onClick={() => handleCopy(message.content, message.id)}
              className="rounded-full border border-border/60 bg-muted/60 p-2 text-muted-foreground transition hover:border-border hover:bg-muted/70"
            >
              {copiedMessageId === message.id ? (
                <CopyCheck className="h-4 w-4 text-emerald-400" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </button>
          </div>
        )}
      </div>
    );
  } else {
    // Fallback for other messages - just show content
    return (
      <div className="relative flex w-full flex-col">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="chat-bubble-scroll overflow-x-auto break-words rounded-3xl border border-border/60 bg-secondary/80 px-5 py-4 pb-5 text-sm leading-relaxed text-foreground/90 shadow-[0_18px_42px_-24px_rgba(10,16,28,0.65)]">
              <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
          <button
            onClick={() => handleCopy(message.content, message.id)}
            className="rounded-full border border-border/60 bg-muted/60 p-2 text-muted-foreground transition hover:border-border hover:bg-muted/70"
          >
            {copiedMessageId === message.id ? (
              <CopyCheck className="h-4 w-4 text-emerald-400" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    );
  }
};

interface ChatMessagesViewProps {
  messages: { type: "human" | "ai"; content: string; id: string; agent?: string; finalReportWithCitations?: boolean }[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (query: string) => void;
  onCancel: () => void;
  displayData: string | null;
  messageEvents: Map<string, ProcessedEvent[]>;
  websiteCount: number;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  messageEvents,
  websiteCount,
}: ChatMessagesViewProps) {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  const handleNewChat = () => {
    window.location.reload();
  };

  const firstHumanIndex = useMemo(
    () => messages.findIndex((m) => m.type === "human"),
    [messages]
  );

  const displayMessages = useMemo(() => {
    if (firstHumanIndex < 0) {
      return messages;
    }
    return messages.filter((message, idx) => !(message.type === "human" && idx === firstHumanIndex));
  }, [messages, firstHumanIndex]);

  const lastAiMessage = displayMessages.slice().reverse().find(m => m.type === "ai");
  const lastAiMessageId = lastAiMessage?.id;
  const lastMessage = displayMessages.length > 0 ? displayMessages[displayMessages.length - 1] : null;

  const aiMessagesCount = messages.filter((m) => m.type === "ai").length;
  const humanMessagesCount = messages.filter((m) => m.type === "human").length;
  const statusInfo = isLoading
    ? { variant: "warning" as const, label: "Gerando anúncios" }
    : aiMessagesCount > 0
      ? { variant: "success" as const, label: "Sessão ativa" }
      : { variant: "neutral" as const, label: "Aguardando briefing" };

  return (
    <div className="flex h-full w-full">
      <div className="flex h-full w-full flex-col rounded-[28px] border border-border/60 bg-surface/70 backdrop-blur-xl shadow-[0_40px_120px_-40px_rgba(8,12,24,0.65)]">
        <div className="sticky top-[52px] z-30 border-b border-border/60 bg-surface/90 px-6 py-2 backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground/80">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                Orquestração de agentes
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-xl font-semibold text-foreground/95">Sessão de criação</h1>
                <StatusBadge variant={statusInfo.variant}>{statusInfo.label}</StatusBadge>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <StatPill label="Mensagens IA" value={aiMessagesCount} muted />
              <StatPill label="Mensagens humanas" value={humanMessagesCount} muted />
              {websiteCount > 0 && (
                <StatPill label="Fontes analisadas" value={websiteCount} muted />
              )}
              <Button
                onClick={handleNewChat}
                variant="outline"
                className="gap-2 border-border/70 bg-secondary hover:bg-secondary/80"
              >
                <RefreshCw className="h-4 w-4" />
                Nova sessão
              </Button>
            </div>
          </div>
        </div>
        <div className="flex-1">
          <ScrollArea ref={scrollAreaRef} className="h-full">
            <div className="mx-auto flex min-h-[calc(100vh-200px)] max-w-screen-2xl flex-col justify-center gap-4 px-6 py-8">
              {displayMessages.map((message) => {
                const eventsForMessage = message.type === "ai" ? (messageEvents.get(message.id) || []) : [];

                // Determine if the current AI message is the last one
                const isCurrentMessageTheLastAiMessage = message.type === "ai" && message.id === lastAiMessageId;

                return (
                  <div
                    key={message.id}
                    className={cn(
                      "flex",
                      message.type === "human" ? "justify-end" : "justify-start"
                    )}
                  >
                    {message.type === "human" ? (
                      <HumanMessageBubble
                        message={message}
                        mdComponents={mdComponents}
                      />
                    ) : (
                      <AiMessageBubble
                        message={message}
                        mdComponents={mdComponents}
                        handleCopy={handleCopy}
                        copiedMessageId={copiedMessageId}
                        agent={message.agent}
                        finalReportWithCitations={message.finalReportWithCitations}
                        processedEvents={eventsForMessage}
                        websiteCount={isCurrentMessageTheLastAiMessage ? websiteCount : 0}
                        isLoading={isCurrentMessageTheLastAiMessage && isLoading}
                      />
                    )}
                  </div>
                );
              })}
              {isLoading && !lastAiMessage && messages.some(m => m.type === 'human') && (
                <div className="flex justify-start pl-2">
                  <div className="flex items-center gap-2 rounded-full border border-border/60 bg-muted/50 px-3 py-1 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <span>Gerando...</span>
                  </div>
                </div>
              )}
              {isLoading && lastMessage && lastMessage.type === 'human' && (
                <div className="flex justify-start pl-10 pt-2">
                  <div className="flex items-center gap-2 rounded-full border border-border/60 bg-muted/50 px-3 py-1 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <span>Gerando...</span>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
        <div className="border-t border-border/60 bg-surface/80 px-6 py-5">
          <div className="mx-auto max-w-3xl">
            <InputForm onSubmit={onSubmit} isLoading={isLoading} context="chat" />
            {isLoading && (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="ghost"
                  onClick={onCancel}
                  className="gap-2 text-destructive hover:text-destructive/80"
                >
                  Cancelar geração
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
