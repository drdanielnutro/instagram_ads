import { useCallback, useMemo, useState } from "react";

export type ReferenceImageType = "character" | "product";

export type ReferenceImageStatus = "idle" | "uploading" | "uploaded" | "error";

export interface ReferenceImageEntry {
  id: string | null;
  status: ReferenceImageStatus;
  fileName: string | null;
  signedUrl: string | null;
  labels: string[];
  userDescription: string;
  error: string | null;
}

export type ReferenceImagesRequestPayload = {
  character?: { id: string; user_description?: string };
  product?: { id: string; user_description?: string };
} | null;

interface UploadArgs {
  type: ReferenceImageType;
  file: File;
  userId?: string | null;
  sessionId?: string | null;
  signal?: AbortSignal;
}

interface UploadResponse {
  id?: string;
  signed_url?: string | null;
  labels?: unknown;
}

interface ReferenceImagesState {
  character: ReferenceImageEntry;
  product: ReferenceImageEntry;
}

export interface UseReferenceImagesReturn {
  character: ReferenceImageEntry;
  product: ReferenceImageEntry;
  isUploading: boolean;
  hasReferences: boolean;
  uploadReferenceImage: (args: UploadArgs) => Promise<boolean>;
  setUserDescription: (type: ReferenceImageType, description: string) => void;
  clearReferenceImage: (type: ReferenceImageType) => void;
  setError: (type: ReferenceImageType, message: string | null) => void;
  resetAll: () => void;
  getRequestPayload: () => ReferenceImagesRequestPayload;
}

const createInitialEntry = (): ReferenceImageEntry => ({
  id: null,
  status: "idle",
  fileName: null,
  signedUrl: null,
  labels: [],
  userDescription: "",
  error: null,
});

const INITIAL_STATE: ReferenceImagesState = {
  character: createInitialEntry(),
  product: createInitialEntry(),
};

const ALLOWED_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
]);

const parseLabels = (labels: unknown): string[] => {
  if (Array.isArray(labels)) {
    return labels.map(label => String(label)).filter(Boolean);
  }
  return [];
};

export function useReferenceImages(): UseReferenceImagesReturn {
  const [state, setState] = useState<ReferenceImagesState>(INITIAL_STATE);

  const updateEntry = useCallback(
    (
      type: ReferenceImageType,
      updater: (prev: ReferenceImageEntry) => ReferenceImageEntry,
    ) => {
      setState(prevState => ({
        ...prevState,
        [type]: updater(prevState[type]),
      }));
    },
    [],
  );

  const uploadReferenceImage = useCallback(
    async ({ type, file, userId, sessionId, signal }: UploadArgs): Promise<boolean> => {
      if (!ALLOWED_MIME_TYPES.has(file.type)) {
        updateEntry(type, prev => ({
          ...prev,
          status: "error",
          error: "Formato inválido. Use PNG, JPEG ou WebP.",
        }));
        return false;
      }

      updateEntry(type, prev => ({
        ...prev,
        status: "uploading",
        error: null,
        fileName: file.name,
      }));

      const formData = new FormData();
      formData.append("file", file);
      formData.append("type", type);
      if (userId) {
        formData.append("user_id", userId);
      }
      if (sessionId) {
        formData.append("session_id", sessionId);
      }

      try {
        const response = await fetch("/api/upload/reference-image", {
          method: "POST",
          body: formData,
          signal,
        });

        if (!response.ok) {
          let message = `Falha ao enviar imagem (${response.status}).`;
          try {
            const data = (await response.json()) as { detail?: unknown };
            if (typeof data.detail === "string" && data.detail.trim()) {
              message = data.detail.trim();
            }
          } catch {
            // Ignora falha ao ler resposta JSON para manter mensagem padrão.
          }

          updateEntry(type, prev => ({
            ...prev,
            status: "error",
            error: message,
          }));
          return false;
        }

        const data = (await response.json()) as UploadResponse;
        if (!data.id || typeof data.id !== "string") {
          updateEntry(type, prev => ({
            ...prev,
            status: "error",
            error: "Resposta inválida do servidor ao enviar a imagem.",
          }));
          return false;
        }

        updateEntry(type, prev => ({
          ...prev,
          id: data.id ?? prev.id,
          status: "uploaded",
          signedUrl: data.signed_url ?? null,
          labels: parseLabels(data.labels),
          error: null,
        }));
        return true;
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Falha inesperada ao enviar a imagem.";
        updateEntry(type, prev => ({
          ...prev,
          status: "error",
          error: message,
        }));
        return false;
      }
    },
    [updateEntry],
  );

  const setUserDescription = useCallback(
    (type: ReferenceImageType, description: string) => {
      updateEntry(type, prev => ({
        ...prev,
        userDescription: description,
      }));
    },
    [updateEntry],
  );

  const clearReferenceImage = useCallback(
    (type: ReferenceImageType) => {
      setState(prevState => ({
        ...prevState,
        [type]: createInitialEntry(),
      }));
    },
    [],
  );

  const setError = useCallback(
    (type: ReferenceImageType, message: string | null) => {
      updateEntry(type, prev => ({
        ...prev,
        status: message ? "error" : prev.id ? "uploaded" : "idle",
        error: message,
      }));
    },
    [updateEntry],
  );

  const resetAll = useCallback(() => {
    setState({
      character: createInitialEntry(),
      product: createInitialEntry(),
    });
  }, []);

  const character = state.character;
  const product = state.product;

  const isUploading = useMemo(
    () =>
      character.status === "uploading" || product.status === "uploading",
    [character.status, product.status],
  );

  const hasReferences = useMemo(
    () => Boolean(character.id || product.id),
    [character.id, product.id],
  );

  const getRequestPayload = useCallback((): ReferenceImagesRequestPayload => {
    const payload: NonNullable<ReferenceImagesRequestPayload> = {};

    if (character.id) {
      const entry: { id: string; user_description?: string } = {
        id: character.id,
      };
      const description = character.userDescription.trim();
      if (description) {
        entry.user_description = description;
      }
      payload.character = entry;
    }

    if (product.id) {
      const entry: { id: string; user_description?: string } = {
        id: product.id,
      };
      const description = product.userDescription.trim();
      if (description) {
        entry.user_description = description;
      }
      payload.product = entry;
    }

    return Object.keys(payload).length > 0 ? payload : null;
  }, [character.id, character.userDescription, product.id, product.userDescription]);

  return useMemo(
    () => ({
      character,
      product,
      isUploading,
      hasReferences,
      uploadReferenceImage,
      setUserDescription,
      clearReferenceImage,
      setError,
      resetAll,
      getRequestPayload,
    }),
    [
      character,
      product,
      isUploading,
      hasReferences,
      uploadReferenceImage,
      setUserDescription,
      clearReferenceImage,
      setError,
      resetAll,
      getRequestPayload,
    ],
  );
}

