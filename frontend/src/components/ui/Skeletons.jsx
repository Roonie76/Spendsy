import React from "react";
import { cn } from "@shared/utils/cn";

export const Skeleton = ({ className }) => (
  <div className={cn("animate-pulse bg-white/5 rounded-xl", className)} />
);

export const WealthSkeleton = () => (
  <div className="space-y-6">
    <Skeleton className="h-64 rounded-[2.5rem]" />
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Skeleton className="h-48 rounded-[2rem]" />
      <Skeleton className="h-48 rounded-[2rem]" />
    </div>
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-24 rounded-2xl" />
      ))}
    </div>
  </div>
);
