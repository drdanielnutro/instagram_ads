type BooleanLike = string | boolean | undefined | null;

function normalizeBoolean(value: BooleanLike, defaultValue = false): boolean {
  if (value === undefined || value === null) {
    return defaultValue;
  }

  if (typeof value === "boolean") {
    return value;
  }

  const normalized = value.toString().trim().toLowerCase();

  if (normalized === "true") {
    return true;
  }

  if (normalized === "false") {
    return false;
  }

  return defaultValue;
}

export function readBooleanFlag(key: string, defaultValue = false): boolean {
  const env = import.meta.env as Record<string, string | boolean | undefined>;
  const rawValue = env?.[key];
  return normalizeBoolean(rawValue, defaultValue);
}

export function isWizardEnabled(defaultValue = false): boolean {
  return readBooleanFlag("VITE_ENABLE_WIZARD", defaultValue);
}

export function isPreviewEnabled(defaultValue = false): boolean {
  return readBooleanFlag("VITE_ENABLE_ADS_PREVIEW", defaultValue);
}

