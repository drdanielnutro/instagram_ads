import { useCallback, useMemo, useRef } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ImageIcon,
  Loader2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type {
  ReferenceImageEntry,
  ReferenceImageType,
} from "@/state/useReferenceImages";

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
]);

interface ReferenceUploadProps {
  type: ReferenceImageType;
  entry: ReferenceImageEntry;
  onUpload: (file: File) => Promise<boolean>;
  onDescriptionChange: (value: string) => void;
  onRemove: () => void;
  onValidationError: (message: string | null) => void;
  disabled?: boolean;
}

const typeCopy: Record<ReferenceImageType, { title: string; description: string; placeholder: string }> = {
  character: {
    title: "Referência de personagem",
    description:
      "Use esta opção quando houver um personagem aprovado. A IA preserva tom de pele, cabelo e traços principais.",
    placeholder:
      "Descreva brevemente o personagem, expressões desejadas ou restrições (opcional).",
  },
  product: {
    title: "Referência de produto ou serviço",
    description:
      "Ajuda a manter o produto real nas variações visuais. Utilize quando houver foto oficial ou mock aprovado.",
    placeholder:
      "Resuma atributos essenciais do produto/serviço para reforçar nos prompts (opcional).",
  },
};

export function ReferenceUpload({
  type,
  entry,
  onUpload,
  onDescriptionChange,
  onRemove,
  onValidationError,
  disabled = false,
}: ReferenceUploadProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const copy = typeCopy[type];
  const isUploading = entry.status === "uploading";

  const handleButtonClick = useCallback(() => {
    if (disabled || isUploading) {
      return;
    }
    fileInputRef.current?.click();
  }, [disabled, isUploading]);

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = ""; // allow re-selecting the same file later

      if (!file) {
        return;
      }

      if (file.size > MAX_FILE_SIZE_BYTES) {
        onValidationError("Arquivo muito grande. Limite de 5 MB.");
        return;
      }

      if (!ALLOWED_MIME_TYPES.has(file.type)) {
        onValidationError("Formato inválido. Use PNG, JPEG ou WebP.");
        return;
      }

      onValidationError(null);
      await onUpload(file);
    },
    [onUpload, onValidationError],
  );

  const statusContent = useMemo(() => {
    if (isUploading) {
      return (
        <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Enviando imagem...
        </span>
      );
    }

    if (entry.status === "uploaded" && entry.id) {
      return (
        <span className="inline-flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          Upload concluído
        </span>
      );
    }

    if (entry.status === "error" && entry.error) {
      return (
        <span className="inline-flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {entry.error}
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <ImageIcon className="h-4 w-4" />
        Nenhum arquivo selecionado
      </span>
    );
  }, [entry.error, entry.id, entry.status, isUploading]);

  return (
    <div className="rounded-xl border border-border/60 bg-card/80 p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-foreground/90 uppercase tracking-wide">
            {copy.title}
          </h4>
          <p className="mt-1 text-sm text-muted-foreground">{copy.description}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleButtonClick}
          disabled={disabled || isUploading}
          className="mt-2 w-full gap-2 sm:mt-0 sm:w-auto"
        >
          {isUploading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Enviando...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Selecionar imagem
            </>
          )}
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={handleFileChange}
          disabled={disabled}
        />
      </div>

      <div className="mt-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm text-muted-foreground">
            Máx. 5 MB · Formatos aceitos: PNG, JPG, JPEG, WebP
          </div>
          {entry.id && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={onRemove}
              disabled={disabled || isUploading}
              className="gap-2 text-destructive hover:text-destructive/80"
            >
              <X className="h-4 w-4" />
              Remover
            </Button>
          )}
        </div>

        {entry.fileName && (
          <div className="rounded-md bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground/80">Arquivo:</span> {entry.fileName}
          </div>
        )}

        <div>{statusContent}</div>

        <Textarea
          value={entry.userDescription}
          onChange={event => onDescriptionChange(event.target.value)}
          placeholder={copy.placeholder}
          rows={3}
          disabled={disabled}
        />

        {entry.labels.length > 0 && (
          <div className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground/80">Labels detectados:</span>{" "}
            {entry.labels.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}

