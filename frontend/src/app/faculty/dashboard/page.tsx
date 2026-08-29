"use client";

import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";
import { useActiveFacultySessions } from "@/queries/use-active-faculty-sessions";
import { useCurrentUser } from "@/queries/use-current-user";
import { useEndSession } from "@/queries/use-end-session";

export default function FacultyDashboardPage() {
  const { data: user } = useCurrentUser();
  const { data: activeSessions } = useActiveFacultySessions();
  const endSession = useEndSession();

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Faculty Dashboard</h1>
        <LogoutButton />
      </div>
      <p className="text-zinc-600 dark:text-zinc-400">
        Welcome, {user?.name}. This is a placeholder — live attendance monitoring and richer
        dashboards arrive in Phase 6a.
      </p>

      <div className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10">
        <p className="text-sm">Start a new attendance session.</p>
        <Link
          href="/faculty/sessions/new"
          className="rounded bg-black px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black"
        >
          Create Session
        </Link>
      </div>

      {activeSessions && activeSessions.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
            Active Session{activeSessions.length > 1 ? "s" : ""}
          </h2>
          {activeSessions.map((session) => (
            <div
              key={session.id}
              className="flex flex-col gap-2 rounded-lg border border-black/10 p-4 dark:border-white/10"
            >
              <div className="flex items-center justify-between">
                <p className="font-medium">
                  {session.subject.code} • {session.class.name}
                </p>
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                  <span className="h-2 w-2 rounded-full bg-green-500" /> LIVE
                </span>
              </div>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Started{" "}
                {new Date(session.starts_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
              <button
                type="button"
                onClick={() => endSession.mutate(session.id)}
                disabled={endSession.isPending}
                className="self-start rounded border border-black/10 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-white/10"
              >
                {endSession.isPending ? "Ending..." : "End Session"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
