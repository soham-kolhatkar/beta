"use client";

import Link from "next/link";
import { useFacultySessions } from "@/queries/use-faculty-sessions";

export default function FacultySessionHistoryPage() {
  const { data: sessions } = useFacultySessions("ENDED");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <Link href="/faculty/dashboard" className="text-sm underline">
        Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Session History</h1>

      {sessions && sessions.length === 0 && (
        <p className="text-sm text-zinc-500 dark:text-zinc-400">No past sessions yet.</p>
      )}

      <div className="flex flex-col divide-y divide-black/10 dark:divide-white/10">
        {sessions?.map((session) => (
          <Link
            key={session.id}
            href={`/faculty/sessions/${session.id}`}
            className="flex items-center justify-between py-3 hover:bg-black/5 dark:hover:bg-white/5"
          >
            <div>
              <p className="font-medium">
                {session.subject.code} • {session.class.name}
              </p>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                {new Date(session.starts_at).toLocaleString([], {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            </div>
            <span className="text-sm text-zinc-500 dark:text-zinc-400">View →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
