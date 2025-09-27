import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { v4 as uuidv4 } from "uuid";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { AdsPreview } from "@/components/AdsPreview";
import { Button } from "@/components/ui/button";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { isPreviewEnabled } from "@/utils/featureFlags";

type DisplayData = string | null;

interface MessageWithAgent {
  type: "human" | "ai";
  content: string;
  id: string;
  agent?: string;
  finalReportWithCitations?: boolean;
}

type FunctionCallPayload = {
  name: string;
  args?: Record<string, unknown>;
  id?: string;
};

type FunctionResponsePayload = {
  name: string;
  response?: unknown;
  id?: string;
};

type TimelineData =
  | { type: "text"; content: string }
  | { type: "functionCall"; name: string; args?: Record<string, unknown>; id?: string }
  | { type: "functionResponse"; name: string; response?: unknown; id?: string }
  | { type: "sources"; content: unknown };

interface ProcessedEvent {
  title: string;
  data: TimelineData;
}

type DeliveryMeta = {
  ok: boolean;
  signed_url?: string;
  [key: string]: unknown;
};

type SessionResponse = {
  userId: string;
  id: string;
  appName: string;
};

type PreflightResult = {
  initial_state?: Record<string, unknown>;
  plan_summary?: Record<string, unknown>;
  blocked?: boolean;
};

type ParsedPart = {
  text?: string;
  functionCall?: FunctionCallPayload;
  functionResponse?: FunctionResponsePayload;
};

type SseParseResult = {
  textParts: string[];
  agent: string;
  finalReportWithCitations?: string;
  functionCall: FunctionCallPayload | null;
  functionResponse: FunctionResponsePayload | null;
  sourceCount: number;
  sources: unknown;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isParsedPart = (value: unknown): value is ParsedPart => {
  if (!isRecord(value)) {
    return false;
  }
  if (value.text && typeof value.text !== "string") {
    return false;
  }
  return true;
};

async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 10,
  maxDuration: number = 120000 // 2 minutes
): Promise<T> {
  const startTime = Date.now();
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    if (Date.now() - startTime > maxDuration) {
      throw new Error(`Retry timeout after ${maxDuration}ms`);
    }

    try {
      return await fn();
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      lastError = err;
      const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
      console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms...`, err);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError ?? new Error("Retry attempts exhausted");
}

export default function App() {
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [appName, setAppName] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageWithAgent[]>([]);
  const [displayData, setDisplayData] = useState<DisplayData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messageEvents, setMessageEvents] = useState<Map<string, ProcessedEvent[]>>(new Map());
  const [websiteCount, setWebsiteCount] = useState<number>(0);
  const [isBackendReady, setIsBackendReady] = useState(false);
  const [isCheckingBackend, setIsCheckingBackend] = useState(true);
  const [preflightEnabled, setPreflightEnabled] = useState<boolean>(true);
  const [deliveryMeta, setDeliveryMeta] = useState<DeliveryMeta | null>(null);
  const [deliveryChecking, setDeliveryChecking] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState(false);
  const currentAgentRef = useRef('');
  const accumulatedTextRef = useRef("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const previewEnabled = useMemo(() => isPreviewEnabled(), []);
  const handleClosePreview = useCallback(() => setShowPreview(false), []);
  const openPreview = useCallback(() => {
    if (!previewEnabled || !deliveryMeta?.ok || !userId || !sessionId) {
      return;
    }
    setShowPreview(true);
  }, [deliveryMeta, previewEnabled, sessionId, userId]);
  const canOpenPreview = Boolean(previewEnabled && deliveryMeta?.ok && userId && sessionId);

  // Initialize preflight from env (default ON)
  useEffect(() => {
    const env = import.meta.env?.VITE_ENABLE_PREFLIGHT;
    if (env === 'false') {
      setPreflightEnabled(false);
    }
  }, []);

  useEffect(() => {
    if (!deliveryMeta?.ok) {
      setShowPreview(false);
    }
  }, [deliveryMeta]);

  const createSession = useCallback(async (initialState?: Record<string, unknown>): Promise<{ userId: string; sessionId: string; appName: string }> => {
    const generatedSessionId = uuidv4();
    const response = await fetch(`/api/apps/app/users/u_999/sessions/${generatedSessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(initialState || {})
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status} ${response.statusText}`);
    }

    const data: SessionResponse = await response.json();
    return {
      userId: data.userId,
      sessionId: data.id,
      appName: data.appName
    };
  }, []);

  const runPreflight = useCallback(async (text: string): Promise<PreflightResult | null> => {
    try {
      const resp = await fetch(`/api/run_preflight`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      if (resp.status === 422) {
        const detail = (await resp.json()) as { detail?: { message?: string; errors?: unknown } };
        const msg = detail?.detail?.message ?? "Preflight inválido.";
        const errs = detail?.detail?.errors ? JSON.stringify(detail.detail.errors) : "";
        setMessages(prev => [...prev, { type: "ai", content: `${msg}\n${errs}`, id: Date.now().toString(), agent: "preflight" }]);
        return { blocked: true };
      }
      if (!resp.ok) {
        console.warn("/run_preflight falhou, seguindo sem preflight.");
        return null;
      }
      const data = (await resp.json()) as { initial_state?: Record<string, unknown>; plan_summary?: Record<string, unknown> };
      return { initial_state: data.initial_state, plan_summary: data.plan_summary };
    } catch (error) {
      console.warn("Erro no preflight, seguindo sem preflight.", error);
      return null;
    }
  }, []);

  const checkDeliveryMeta = useCallback(async () => {
    if (!userId || !sessionId) return;
    try {
      setDeliveryChecking(true);
      const resp = await fetch(`/api/delivery/final/meta?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`);
      if (resp.ok) {
        const data = (await resp.json()) as DeliveryMeta;
        if (data && data.ok) {
          setDeliveryMeta(data);
        }
      }
    } catch {
      // ignore
    } finally {
      setDeliveryChecking(false);
    }
  }, [userId, sessionId]);

  const handleDownloadFinal = useCallback(async () => {
    if (!userId || !sessionId) return;
    try {
      const url = `/api/delivery/final/download?user_id=${encodeURIComponent(userId)}&session_id=${encodeURIComponent(sessionId)}`;
      // Try to get a signed URL first
      const resp = await fetch(url);
      const ct = resp.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        const data = (await resp.json()) as DeliveryMeta;
        if (data?.signed_url) {
          window.open(String(data.signed_url), '_blank');
          return;
        }
      }
      // Fallback: open endpoint directly (local stream case)
      window.open(url, '_blank');
    } catch (error) {
      console.warn('Download failed', error);
    }
  }, [userId, sessionId]);

  const checkBackendHealth = async (): Promise<boolean> => {
    try {
      // Use the docs endpoint or root endpoint to check if backend is ready
      const response = await fetch("/api/docs", {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });
      return response.ok;
    } catch (error) {
      console.log("Backend not ready yet:", error);
      return false;
    }
  };

  // Function to extract text and metadata from SSE data
  const extractDataFromSSE = (data: string): SseParseResult => {
    try {
      const parsedRaw = JSON.parse(data) as unknown;
      console.log('[SSE PARSED EVENT]:', JSON.stringify(parsedRaw, null, 2)); // DEBUG: Log parsed event

      if (!isRecord(parsedRaw)) {
        return { textParts: [], agent: '', finalReportWithCitations: undefined, functionCall: null, functionResponse: null, sourceCount: 0, sources: null };
      }

      const content = isRecord(parsedRaw.content) ? parsedRaw.content : undefined;
      const partsRaw = content && Array.isArray(content.parts) ? content.parts : [];

      const filteredParts = partsRaw.filter(isParsedPart);
      const textParts = filteredParts
        .map(part => part.text)
        .filter((text): text is string => typeof text === "string" && text.length > 0);

      const functionCallPart = filteredParts.find(part => part.functionCall?.name);
      const functionResponsePart = filteredParts.find(part => part.functionResponse?.name);

      const agent = typeof parsedRaw.author === "string" ? parsedRaw.author : "";
      if (agent) {
        console.log('[SSE EXTRACT] Agent:', agent); // DEBUG: Log agent
      }

      const actions = isRecord(parsedRaw.actions) ? parsedRaw.actions : undefined;
      const stateDelta = actions && isRecord(actions.stateDelta) ? actions.stateDelta : undefined;
      const finalReportWithCitations = typeof stateDelta?.final_report_with_citations === "string"
        ? stateDelta.final_report_with_citations
        : undefined;

      let sourceCount = 0;
      if (agent === 'section_researcher' || agent === 'enhanced_search_executor') {
        const urlMap = stateDelta && isRecord(stateDelta.url_to_short_id) ? stateDelta.url_to_short_id : undefined;
        if (urlMap) {
          sourceCount = Object.keys(urlMap).length;
        }
      }

      const sources = stateDelta?.sources ?? null;

      return {
        textParts,
        agent,
        finalReportWithCitations,
        functionCall: functionCallPart?.functionCall ?? null,
        functionResponse: functionResponsePart?.functionResponse ?? null,
        sourceCount,
        sources
      };
    } catch (error) {
      const truncatedData = data.length > 200 ? data.substring(0, 200) + "..." : data;
      console.error('Error parsing SSE data. Raw data (truncated): "', truncatedData, '". Error details:', error);
      return { textParts: [], agent: '', finalReportWithCitations: undefined, functionCall: null, functionResponse: null, sourceCount: 0, sources: null };
    }
  };

  // Define getEventTitle here or ensure it's in scope from where it's used
  const getEventTitle = (agentName: string): string => {
    switch (agentName) {
      case "plan_generator":
        return "Planning Research Strategy";
      case "section_planner":
        return "Structuring Report Outline";
      case "section_researcher":
        return "Initial Web Research";
      case "research_evaluator":
        return "Evaluating Research Quality";
      case "EscalationChecker":
        return "Quality Assessment";
      case "enhanced_search_executor":
        return "Enhanced Web Research";
      case "research_pipeline":
        return "Executing Research Pipeline";
      case "iterative_refinement_loop":
        return "Refining Research";
      case "interactive_planner_agent":
      case "root_agent":
        return "Interactive Planning";
      default:
        return `Processing (${agentName || 'Unknown Agent'})`;
    }
  };

  const processSseEventData = useCallback((jsonData: string, aiMessageId: string) => {
    const { textParts, agent, finalReportWithCitations, functionCall, functionResponse, sourceCount, sources } = extractDataFromSSE(jsonData);

    if (sourceCount > 0) {
      console.log('[SSE HANDLER] Updating websiteCount. Current sourceCount:', sourceCount);
      setWebsiteCount(prev => Math.max(prev, sourceCount));
    }

    if (agent && agent !== currentAgentRef.current) {
      currentAgentRef.current = agent;
    }

    if (functionCall) {
      const functionCallTitle = `Function Call: ${functionCall.name}`;
      console.log('[SSE HANDLER] Adding Function Call timeline event:', functionCallTitle);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: functionCallTitle,
        data: { type: 'functionCall', name: functionCall.name, args: functionCall.args, id: functionCall.id }
      }]));
    }

    if (functionResponse) {
      const functionResponseTitle = `Function Response: ${functionResponse.name}`;
      console.log('[SSE HANDLER] Adding Function Response timeline event:', functionResponseTitle);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: functionResponseTitle,
        data: { type: 'functionResponse', name: functionResponse.name, response: functionResponse.response, id: functionResponse.id }
      }]));
    }

    if (textParts.length > 0 && agent !== "report_composer_with_citations") {
      if (agent !== "interactive_planner_agent") {
        const eventTitle = getEventTitle(agent);
        console.log('[SSE HANDLER] Adding Text timeline event for agent:', agent, 'Title:', eventTitle, 'Data:', textParts.join(" "));
        setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
          title: eventTitle,
          data: { type: 'text', content: textParts.join(" ") }
        }]));
      } else { // interactive_planner_agent text updates the main AI message
        for (const text of textParts) {
          accumulatedTextRef.current += text + " ";
          setMessages(prev => prev.map(msg =>
            msg.id === aiMessageId ? { ...msg, content: accumulatedTextRef.current.trim(), agent: currentAgentRef.current || msg.agent } : msg
          ));
          setDisplayData(accumulatedTextRef.current.trim());
        }
      }
    }

    if (sources) {
      console.log('[SSE HANDLER] Adding Retrieved Sources timeline event:', sources);
      setMessageEvents(prev => new Map(prev).set(aiMessageId, [...(prev.get(aiMessageId) || []), {
        title: "Retrieved Sources", data: { type: 'sources', content: sources }
      }]));
    }

    if (agent === "report_composer_with_citations" && finalReportWithCitations) {
      const finalReportMessageId = Date.now().toString() + "_final";
      setMessages(prev => [...prev, { type: "ai", content: finalReportWithCitations, id: finalReportMessageId, agent: currentAgentRef.current, finalReportWithCitations: true }]);
      setDisplayData(finalReportWithCitations);
    }
  }, []);

  const handleSubmit = useCallback(async (query: string) => {
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      // Create session if it doesn't exist
      let currentUserId = userId;
      let currentSessionId = sessionId;
      let currentAppName = appName;

      if (!currentSessionId || !currentUserId || !currentAppName) {
        console.log('Creating new session...');
        // Tentar preflight para preparar estado inicial (plano fixo + specs por formato)
        let initialState: Record<string, unknown> = {};
        if (preflightEnabled) {
          const preflight = await runPreflight(query);
          if (preflight?.blocked) {
            setIsLoading(false);
            return; // Não segue para o ADK quando preflight inválido
          }
          initialState = preflight?.initial_state || {};
        }
        const sessionData = await retryWithBackoff(() => createSession(initialState));
        currentUserId = sessionData.userId;
        currentSessionId = sessionData.sessionId;
        currentAppName = sessionData.appName;

        setUserId(currentUserId);
        setSessionId(currentSessionId);
        setAppName(currentAppName);
        console.log('Session created successfully:', { currentUserId, currentSessionId, currentAppName });
      }

      // Add user message to chat
      const userMessageId = Date.now().toString();
      setMessages(prev => [...prev, { type: "human", content: query, id: userMessageId }]);

      // Create AI message placeholder
      const aiMessageId = Date.now().toString() + "_ai";
      currentAgentRef.current = ''; // Reset current agent
      accumulatedTextRef.current = ''; // Reset accumulated text

      setMessages(prev => [...prev, {
        type: "ai",
        content: "",
        id: aiMessageId,
        agent: '',
      }]);

      // Send the message with retry logic
      const sendMessage = async () => {
        const response = await fetch("/api/run_sse", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            appName: currentAppName,
            userId: currentUserId,
            sessionId: currentSessionId,
            newMessage: {
              parts: [{ text: query }],
              role: "user"
            },
            streaming: false
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
        }

        return response;
      };

      const response = await retryWithBackoff(sendMessage);

      // Handle SSE streaming
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let lineBuffer = "";
      let eventDataBuffer = "";

      if (reader) {
        for (; ;) {
          const { done, value } = await reader.read();

          if (value) {
            lineBuffer += decoder.decode(value, { stream: true });
          }

          let eolIndex;
          // Process all complete lines in the buffer, or the remaining buffer if 'done'
          while ((eolIndex = lineBuffer.indexOf('\n')) >= 0 || (done && lineBuffer.length > 0)) {
            let line: string;
            if (eolIndex >= 0) {
              line = lineBuffer.substring(0, eolIndex);
              lineBuffer = lineBuffer.substring(eolIndex + 1);
            } else { // Only if done and lineBuffer has content without a trailing newline
              line = lineBuffer;
              lineBuffer = "";
            }

            if (line.trim() === "") { // Empty line: dispatch event
              if (eventDataBuffer.length > 0) {
                // Remove trailing newline before parsing
                const jsonDataToParse = eventDataBuffer.endsWith('\n') ? eventDataBuffer.slice(0, -1) : eventDataBuffer;
                console.log('[SSE DISPATCH EVENT]:', jsonDataToParse.substring(0, 200) + "..."); // DEBUG
                processSseEventData(jsonDataToParse, aiMessageId);
                eventDataBuffer = ""; // Reset for next event
              }
            } else if (line.startsWith('data:')) {
              eventDataBuffer += line.substring(5).trimStart() + '\n'; // Add newline as per spec for multi-line data
            } else if (line.startsWith(':')) {
              // Comment line, ignore
            } // Other SSE fields (event, id, retry) can be handled here if needed
          }

          if (done) {
            // If the loop exited due to 'done', and there's still data in eventDataBuffer
            // (e.g., stream ended after data lines but before an empty line delimiter)
            if (eventDataBuffer.length > 0) {
              const jsonDataToParse = eventDataBuffer.endsWith('\n') ? eventDataBuffer.slice(0, -1) : eventDataBuffer;
              console.log('[SSE DISPATCH FINAL EVENT]:', jsonDataToParse.substring(0, 200) + "..."); // DEBUG
              processSseEventData(jsonDataToParse, aiMessageId);
              eventDataBuffer = ""; // Clear buffer
            }
            break; // Exit the while(true) loop
          }
        }
      }

      setIsLoading(false);

    } catch (error) {
      console.error("Error:", error);
      // Update the AI message placeholder with an error message
      const aiMessageId = Date.now().toString() + "_ai_error";
      setMessages(prev => [...prev, {
        type: "ai",
        content: `Sorry, there was an error processing your request: ${error instanceof Error ? error.message : 'Unknown error'}`,
        id: aiMessageId
      }]);
      setIsLoading(false);
    }
  }, [appName, preflightEnabled, processSseEventData, runPreflight, sessionId, userId, createSession]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [messages]);

  useEffect(() => {
    const checkBackend = async () => {
      setIsCheckingBackend(true);

      // Check if backend is ready with retry logic
      const maxAttempts = 60; // 2 minutes with 2-second intervals
      let attempts = 0;

      while (attempts < maxAttempts) {
        const isReady = await checkBackendHealth();
        if (isReady) {
          setIsBackendReady(true);
          setIsCheckingBackend(false);
          return;
        }

        attempts++;
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds between checks
      }

      // If we get here, backend didn't come up in time
      setIsCheckingBackend(false);
      console.error("Backend failed to start within 2 minutes");
    };

    checkBackend();
  }, []);

  const handleCancel = useCallback(() => {
    setMessages([]);
    setDisplayData(null);
    setMessageEvents(new Map());
    setWebsiteCount(0);
    window.location.reload();
  }, []);

  const BackendLoadingScreen = () => (
    <div className="flex-1 flex flex-col items-center justify-center p-4 overflow-hidden relative">
      <div className="w-full max-w-2xl z-10
                      bg-neutral-900/50 backdrop-blur-md 
                      p-8 rounded-2xl border border-neutral-700 
                      shadow-2xl shadow-black/60">

        <div className="text-center space-y-6">
          <h1 className="text-4xl font-bold text-white flex items-center justify-center gap-3">
            ✨ Gemini FullStack - ADK 🚀
          </h1>

          <div className="flex flex-col items-center space-y-4">
            {/* Spinning animation */}
            <div className="relative">
              <div className="w-16 h-16 border-4 border-neutral-600 border-t-blue-500 rounded-full animate-spin"></div>
              <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-purple-500 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
            </div>

            <div className="space-y-2">
              <p className="text-xl text-neutral-300">
                Waiting for backend to be ready...
              </p>
              <p className="text-sm text-neutral-400">
                This may take a moment on first startup
              </p>
            </div>

            {/* Animated dots */}
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Auto-check delivery meta when processing finishes and session exists
  useEffect(() => {
    if (!isLoading && userId && sessionId && !deliveryMeta) {
      let attempts = 0;
      const id = setInterval(() => {
        attempts += 1;
        checkDeliveryMeta();
        if (attempts >= 20) {
          clearInterval(id);
        }
      }, 3000);
      // First immediate check
      checkDeliveryMeta();
      return () => clearInterval(id);
    }
  }, [isLoading, userId, sessionId, deliveryMeta, checkDeliveryMeta]);

  return (
    <div className="flex h-screen bg-neutral-800 text-neutral-100 font-sans antialiased">
      <main className="flex-1 flex flex-col overflow-hidden w-full">
        {/* Toolbar */}
        <div className="px-4 py-2 border-b border-neutral-700 bg-neutral-900/60 backdrop-blur sticky top-0 z-20 flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-neutral-200">
            <input
              type="checkbox"
              checked={preflightEnabled}
              onChange={(e) => setPreflightEnabled(e.target.checked)}
            />
            Preflight (plano fixo)
          </label>
          <span className="text-xs text-neutral-400">
            {preflightEnabled ? 'ON' : 'OFF'} — valida entrada e injeta plano por formato
          </span>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="outline"
              onClick={checkDeliveryMeta}
              disabled={!userId || !sessionId || deliveryChecking}
              className="text-xs border-neutral-600 text-neutral-200 hover:bg-neutral-700"
            >
              {deliveryChecking ? 'Verificando…' : 'Atualizar'}
            </Button>
            {previewEnabled && deliveryMeta?.ok && (
              <Button
                onClick={openPreview}
                disabled={!canOpenPreview}
                className={`${!canOpenPreview ? 'bg-neutral-700 text-neutral-300 cursor-not-allowed' : 'bg-indigo-500 hover:bg-indigo-600 text-white'} text-xs`}
              >
                Preview
              </Button>
            )}
            <Button
              onClick={handleDownloadFinal}
              disabled={!deliveryMeta || !deliveryMeta.ok}
              className={`${(!deliveryMeta || !deliveryMeta.ok) ? 'bg-neutral-700 text-neutral-300 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 text-white'} text-xs`}
            >
              Baixar JSON
            </Button>
          </div>
        </div>
        <div className={`flex-1 overflow-y-auto ${(messages.length === 0 || isCheckingBackend) ? "flex" : ""}`}>
          {isCheckingBackend ? (
            <BackendLoadingScreen />
          ) : !isBackendReady ? (
            <div className="flex-1 flex flex-col items-center justify-center p-4">
              <div className="text-center space-y-4">
                <h2 className="text-2xl font-bold text-red-400">Backend Unavailable</h2>
                <p className="text-neutral-300">
                  Unable to connect to backend services at localhost:8000
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={isLoading}
              onCancel={handleCancel}
            />
          ) : (
            <ChatMessagesView
              messages={messages}
              isLoading={isLoading}
              scrollAreaRef={scrollAreaRef}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              displayData={displayData}
              messageEvents={messageEvents}
              websiteCount={websiteCount}
            />
          )}
        </div>
        {previewEnabled && userId && sessionId && (
          <AdsPreview
            userId={userId}
            sessionId={sessionId}
            isOpen={showPreview}
            onClose={handleClosePreview}
          />
        )}
      </main>
    </div>
  );
}
