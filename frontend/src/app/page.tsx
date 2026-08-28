"use client";

import { useHealth } from "@/queries/use-health";

export default function Home() {
  const { data, isLoading, isError } = useHealth();

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 bg-zinc-50 font-sans dark:bg-black">
      <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">GeoAttend</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        Backend:{" "}
        {isLoading ? "checking..." : isError ? "unreachable" : `${data?.status}`}
      </p>
    </div>
  );
}
