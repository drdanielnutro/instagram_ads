import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/utils";

export interface StatPillProps extends HTMLAttributes<HTMLDivElement> {
  label?: ReactNode;
  value?: ReactNode;
  icon?: ReactNode;
  muted?: boolean;
}

export function StatPill({
  label,
  value,
  icon,
  muted = false,
  className,
  children,
  ...props
}: StatPillProps) {
  const content = value ?? children;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
        muted
          ? "border-border/50 bg-muted/60 text-muted-foreground"
          : "border-border/80 bg-secondary/60 text-foreground/90",
        className,
      )}
      {...props}
    >
      {icon && <span className="text-base text-primary/80">{icon}</span>}
      <div className="flex flex-col leading-tight">
        {label && <span className="text-[11px] uppercase text-muted-foreground/80 tracking-wide">{label}</span>}
        <span className="text-sm font-medium text-foreground/95">{content}</span>
      </div>
    </div>
  );
}

