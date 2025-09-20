import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/utils";

const VARIANT_STYLES: Record<string, string> = {
  info: "bg-primary/10 text-primary border-primary/30",
  success: "bg-emerald-400/10 text-emerald-200 border-emerald-400/30",
  warning: "bg-amber-400/10 text-amber-200 border-amber-400/30",
  danger: "bg-red-500/10 text-red-200 border-red-400/30",
  neutral: "bg-muted text-muted-foreground border-border/60",
};

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "info" | "success" | "warning" | "danger" | "neutral";
  icon?: ReactNode;
}

export function StatusBadge({
  variant = "info",
  icon,
  className,
  children,
  ...props
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide",
        VARIANT_STYLES[variant] ?? VARIANT_STYLES.info,
        className,
      )}
      {...props}
    >
      {icon && <span className="inline-flex items-center text-base leading-none">{icon}</span>}
      <span className="leading-none">{children}</span>
    </span>
  );
}

