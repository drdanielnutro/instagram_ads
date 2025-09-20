import type { ReactNode } from "react";

import { cn } from "@/utils";

interface SectionCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: ReactNode;
  description?: ReactNode;
  headerAction?: ReactNode;
  contentClassName?: string;
}

export function SectionCard({
  title,
  description,
  headerAction,
  className,
  contentClassName,
  children,
  ...props
}: SectionCardProps) {
  const hasHeader = title || description || headerAction;

  return (
    <div
      className={cn(
        "rounded-3xl border border-border/60 bg-card/80 backdrop-blur-xl shadow-[0_30px_80px_-40px_rgba(8,12,24,0.65)]",
        "transition-transform duration-200 hover:translate-y-[-1px] hover:shadow-[0_35px_90px_-45px_rgba(12,18,32,0.75)]",
        className,
      )}
      {...props}
    >
      {hasHeader && (
        <div className="flex items-start justify-between gap-4 border-b border-border/50 px-6 pt-6 pb-4">
          <div className="space-y-1">
            {title && (
              <div className="text-lg font-semibold text-foreground/95 tracking-tight">
                {title}
              </div>
            )}
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {headerAction && <div className="shrink-0">{headerAction}</div>}
        </div>
      )}
      <div className={cn("px-6 pb-6 pt-4", contentClassName)}>{children}</div>
    </div>
  );
}

