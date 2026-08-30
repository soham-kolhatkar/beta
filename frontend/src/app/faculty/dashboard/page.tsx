"use client";

import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";
import { useCurrentUser } from "@/queries/use-current-user";
import { useEndSession } from "@/queries/use-end-session";
import { useFacultyDashboard } from "@/queries/use-faculty-dashboard";

export default function FacultyDashboardPage() {
  const { data: user } = useCurrentUser();
  const { data: dashboard } = useFacultyDashboard();
  const endSession = useEndSession();

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Faculty Dashboard</h1>
        <LogoutButton />
      </div>
      <p className="text-zinc-600 dark:text-zinc-400">Welcome, {user?.name}.</p>

      <div className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10">
        <p className="text-sm">Start a new attendance session.</p>
        <Link
          href="/faculty/sessions/new"
          className="rounded bg-black px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black"
        >
          Create Session
        </Link>
      </div>

      {dashboard && (
        <>
          <div className="flex gap-6">
            <div>
              <p className="text-2xl font-semibold">{dashboard.today.classes}</p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">Classes today</p>
            </div>
            <div>
              <p className="text-2xl font-semibold">{dashboard.today.active_sessions}</p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">Active</p>
            </div>
            <div>
              <p className="text-2xl font-semibold">{dashboard.today.upcoming_sessions}</p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">Upcoming</p>
            </div>
          </div>

          {dashboard.active_session && (
            <div className="flex flex-col gap-2 rounded-lg border border-black/10 p-4 dark:border-white/10">
              <div className="flex items-center justify-between">
                <p className="font-medium">
                  {dashboard.active_session.subject.code} • {dashboard.active_session.class.name}
                </p>
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                  <span className="h-2 w-2 rounded-full bg-green-500" /> LIVE
                </span>
              </div>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Started{" "}
                {new Date(dashboard.active_session.starts_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
              <div className="flex gap-3">
                <Link
                  href={`/faculty/sessions/${dashboard.active_session.id}`}
                  className="rounded bg-black px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black"
                >
                  View Live Attendance
                </Link>
                <button
                  type="button"
                  onClick={() => endSession.mutate(dashboard.active_session!.id)}
                  disabled={endSession.isPending}
                  className="rounded border border-black/10 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-white/10"
                >
                  {endSession.isPending ? "Ending..." : "End Session"}
                </button>
              </div>
            </div>
          )}

          {dashboard.upcoming_classes.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                Today&apos;s Upcoming Classes
              </h2>
              {dashboard.upcoming_classes.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between rounded-lg border border-black/10 p-3 dark:border-white/10"
                >
                  <p>
                    {session.subject.code} • {session.class.name}
                  </p>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {new Date(session.starts_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
