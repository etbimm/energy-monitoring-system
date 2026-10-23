import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-stone-200 bg-white text-stone-900 shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  title,
  subtitle,
  action,
}: {
  className?: string;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 px-5 pt-4 pb-2", className)}>
      <div>
        <h3 className="text-sm font-semibold tracking-wide text-stone-900">{title}</h3>
        {subtitle ? <p className="mt-0.5 text-xs text-stone-500">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 pb-5 pt-2", className)} {...props} />;
}