import React from "react";
import { cn } from "@shared/utils/cn";

export const Skeleton = ({ className }) => (
  <div className={cn("animate-pulse bg-white/5 rounded-xl", className)} />
);

export const WealthSkeleton = () => (
  <div className="space-y-6 animate-in fade-in duration-500">
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

export const StatsSkeleton = () => (
  <div className="space-y-6 animate-in fade-in duration-500">
    <div className="flex justify-between items-center px-1">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-10 w-24" />
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-8 space-y-6">
        <Skeleton className="h-[400px] rounded-[2.5rem]" />
        <Skeleton className="h-[300px] rounded-[2.5rem]" />
      </div>
      <div className="lg:col-span-4 space-y-6">
        <Skeleton className="h-[350px] rounded-[2.5rem]" />
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-[2rem]" />
          <Skeleton className="h-32 rounded-[2rem]" />
          <Skeleton className="h-32 rounded-[2rem]" />
        </div>
      </div>
    </div>
  </div>
);

export const ProfileSkeleton = () => (
  <div className="space-y-4 animate-in fade-in duration-500">
    <Skeleton className="h-44 rounded-3xl" />
    <Skeleton className="h-20 rounded-3xl" />
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Skeleton className="h-56 rounded-3xl" />
      <Skeleton className="h-56 rounded-3xl" />
    </div>
    <Skeleton className="h-40 rounded-3xl" />
    <div className="grid grid-cols-3 gap-2.5">
      {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-32 rounded-3xl" />)}
    </div>
  </div>
);

export const SettingsSkeleton = () => (
  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in duration-500">
    <div className="lg:col-span-4 space-y-6">
      <Skeleton className="h-16 rounded-2xl w-3/4" />
      <Skeleton className="h-24 rounded-2xl" />
      <Skeleton className="h-12 rounded-2xl" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5, 6, 7].map(i => <Skeleton key={i} className="h-16 rounded-2xl" />)}
      </div>
    </div>
    <div className="hidden lg:block lg:col-span-8">
      <Skeleton className="h-[600px] rounded-[3rem]" />
    </div>
  </div>
);

export const GenericPageSkeleton = () => (
  <div className="space-y-6 animate-in fade-in duration-500">
    <div className="flex justify-between items-center px-1">
      <Skeleton className="h-8 w-48" />
      <div className="flex gap-2">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="h-10 w-10 rounded-full" />
      </div>
    </div>
    <Skeleton className="h-40 rounded-[2.5rem]" />
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Skeleton className="h-64 rounded-[2.5rem]" />
      <Skeleton className="h-64 rounded-[2.5rem]" />
    </div>
    <Skeleton className="h-80 rounded-[2.5rem]" />
  </div>
);
