"use client";

import { LogoutButton } from "@/components/logout-button";
import { useCurrentUser } from "@/queries/use-current-user";

export default function StudentDashboardPage() {
  const { data: user } = useCurrentUser();

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Student Dashboard</h1>
        <LogoutButton />
      </div>
      <p className="text-zinc-600 dark:text-zinc-400">
        Welcome, {user?.name}. This is a placeholder — the real dashboard (today&apos;s classes,
        attendance, active session) arrives in Phase 6a.
      </p>
    </div>
  );
}
