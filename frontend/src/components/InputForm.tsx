import { useState, useRef, useEffect } from "react";
import { ArrowRight, FileText, LinkIcon, Target, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Send } from "lucide-react";

interface InputFormProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  context?: "homepage" | "chat";
}

const objetivoFinalOptions = ["agendamentos", "leads", "vendas", "contato"];

const formatoAnuncioOptions = ["Feed", "Stories", "Reels"];

export function InputForm({ onSubmit, isLoading, context = "homepage" }: InputFormProps) {
  const [inputValue, setInputValue] = useState("");
  const [landingPageUrl, setLandingPageUrl] = useState("");
  const [perfilCliente, setPerfilCliente] = useState("");
  const [foco, setFoco] = useState("");
  const [objetivoFinal, setObjetivoFinal] = useState("");
  const [formatoAnuncio, setFormatoAnuncio] = useState("");

  const chatTextareaRef = useRef<HTMLTextAreaElement>(null);
  const landingPageRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (context === "chat") {
      chatTextareaRef.current?.focus();
    } else {
      landingPageRef.current?.focus();
    }
  }, [context]);

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) {
      return;
    }
    onSubmit(inputValue.trim());
    setInputValue("");
  };

  const handleChatKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit(e);
    }
  };

  const handleHomepageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) {
      return;
    }

    const lines: string[] = [];

    if (landingPageUrl.trim()) {
      lines.push(`landing_page_url: ${landingPageUrl.trim()}`);
    }
    if (objetivoFinal.trim()) {
      lines.push(`objetivo_final: ${objetivoFinal.trim()}`);
    }
    if (perfilCliente.trim()) {
      lines.push(`perfil_cliente: ${perfilCliente.trim()}`);
    }
    if (formatoAnuncio.trim()) {
      lines.push(`formato_anuncio: ${formatoAnuncio.trim()}`);
    }
    if (foco.trim()) {
      lines.push(`foco: ${foco.trim()}`);
    }

    if (!lines.length) {
      return;
    }

    onSubmit(lines.join("\n"));

    setLandingPageUrl("");
    setPerfilCliente("");
    setFoco("");
    setObjetivoFinal("");
    setFormatoAnuncio("");
  };

  if (context === "chat") {
    return (
      <form onSubmit={handleChatSubmit} className="flex flex-col gap-2">
        <div className="flex items-end space-x-2">
          <Textarea
            ref={chatTextareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleChatKeyDown}
            placeholder="Refine, peça ajustes (ex.: mude CTA para 'Saiba mais') ou continue a conversa..."
            rows={1}
            className="flex-1 resize-none pr-10 min-h-[40px]"
            disabled={isLoading}
          />
          <Button type="submit" size="icon" disabled={isLoading || !inputValue.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleHomepageSubmit} className="space-y-6">
      <div className="space-y-5">
        <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary shadow-sm">
              1
            </span>
            <div className="flex-1 space-y-1">
              <h3 className="text-base font-semibold text-foreground/95">Passo 1 — Landing page</h3>
              <p className="text-sm text-muted-foreground">
                Informe a URL principal que resume a oferta. Usaremos a página para validar copy, tom e CTA.
              </p>
            </div>
          </div>
          <div className="mt-4">
            <div className="relative">
              <Input
                id="landing-page-url"
                ref={landingPageRef}
                value={landingPageUrl}
                onChange={(e) => setLandingPageUrl(e.target.value)}
                placeholder="https://sua-pagina.com"
                disabled={isLoading}
                autoComplete="off"
                className="pl-11"
              />
              <LinkIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary shadow-sm">
              2
            </span>
            <div className="flex-1 space-y-1">
              <h3 className="text-base font-semibold text-foreground/95">Passo 2 — Objetivo final</h3>
              <p className="text-sm text-muted-foreground">
                Escolha a ação esperada do público para ajustar copy, CTA e fluxo do anúncio.
              </p>
            </div>
          </div>
          <div className="mt-4">
            <Select
              value={objetivoFinal || undefined}
              onValueChange={setObjetivoFinal}
              disabled={isLoading}
            >
              <div className="relative">
                <SelectTrigger className="pl-11">
                  <SelectValue placeholder="Selecione o objetivo" />
                </SelectTrigger>
                <Target className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              </div>
              <SelectContent>
                {objetivoFinalOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary shadow-sm">
              3
            </span>
            <div className="flex-1 space-y-1">
              <h3 className="text-base font-semibold text-foreground/95">Passo 3 — Formato do anúncio</h3>
              <p className="text-sm text-muted-foreground">
                Feed, Stories ou Reels determinam limites de texto, aspect ratio e estilo visual.
              </p>
            </div>
          </div>
          <div className="mt-4">
            <Select
              value={formatoAnuncio || undefined}
              onValueChange={setFormatoAnuncio}
              disabled={isLoading}
            >
              <div className="relative">
                <SelectTrigger className="pl-11">
                  <SelectValue placeholder="Selecione o formato" />
                </SelectTrigger>
                <FileText className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              </div>
              <SelectContent>
                {formatoAnuncioOptions.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary shadow-sm">
              4
            </span>
            <div className="flex-1 space-y-1">
              <h3 className="text-base font-semibold text-foreground/95">Passo 4 — Perfil do cliente</h3>
              <p className="text-sm text-muted-foreground">
                Resuma persona, dores, desejos e estilo de comunicação desejado para manter coerência.
              </p>
            </div>
          </div>
          <div className="mt-4">
            <div className="relative">
              <Textarea
                id="perfil-cliente"
                value={perfilCliente}
                onChange={(e) => setPerfilCliente(e.target.value)}
                placeholder="Ex.: mulheres 35-55, buscam emagrecimento com suporte médico, tom acolhedor."
                rows={4}
                disabled={isLoading}
                className="pl-11"
              />
              <Users className="pointer-events-none absolute left-3 top-5 h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-gradient-to-br from-card/80 to-card/60 px-6 py-5 shadow-lg backdrop-blur-sm transition-all hover:border-primary/30 hover:shadow-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary shadow-sm">
              5
            </span>
            <div className="flex-1 space-y-1">
              <h3 className="text-base font-semibold text-foreground/95">Passo 5 — Foco da campanha</h3>
              <p className="text-sm text-muted-foreground">
                Liste diferenciais, mensagens obrigatórias ou restrições (compliance, claims proibidos, etc.).
              </p>
            </div>
          </div>
          <div className="mt-4">
            <Textarea
              id="foco-campanha"
              value={foco}
              onChange={(e) => setFoco(e.target.value)}
              placeholder="Ex.: destacar acompanhamento médico, evitar promessas de emagrecimento rápido."
              rows={4}
              disabled={isLoading}
            />
          </div>
        </div>
      </div>

      <div className="mt-8 flex flex-col gap-4 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10 px-6 py-5 md:flex-row md:items-center md:justify-between shadow-sm">
        <p className="text-sm font-medium text-foreground/80">
          Campos deixados em branco serão completados pelo assistente com base nas melhores práticas do formato.
        </p>
        <Button
          type="submit"
          disabled={isLoading}
          className="w-full gap-2 md:w-auto shadow-lg hover:shadow-xl transition-all min-w-[180px] group"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Gerando anúncios...
            </>
          ) : (
            <>
              Iniciar geração
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
