"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogoutButton } from "@/components/logout-button";
import { useActiveSessions } from "@/queries/use-active-sessions";
import { useCurrentUser } from "@/queries/use-current-user";
import { useFaceStatus } from "@/queries/use-face-status";
import { useStartVerification } from "@/queries/use-start-verification";

export default function StudentDashboardPage() {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: faceStatus } = useFaceStatus();
  const { data: activeSessions } = useActiveSessions();
  const startVerification = useStartVerification();

  function handleContinue(sessionId: string) {
    startVerification.mutate(sessionId, {
      onSuccess: (result) => router.push(`/student/verify/${result.verification_id}`),
    });
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Student Dashboard</h1>
        <LogoutButton />
      </div>
      <p className="text-zinc-600 dark:text-zinc-400">
        Welcome, {user?.name}. This is a placeholder — the real dashboard (today&apos;s classes,
        attendance history) arrives in Phase 6a.
      </p>

      {faceStatus && !faceStatus.registered && (
        <div className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10">
          <p className="text-sm">
            Register your face before you can mark attendance.
          </p>
          <Link
            href="/student/face-registration"
            className="rounded bg-black px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black"
          >
            Register Face
          </Link>
        </div>
      )}

      {activeSessions && activeSessions.length > 0 && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
            Active Session{activeSessions.length > 1 ? "s" : ""}
          </h2>
          {activeSessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10"
            >
              <div>
                <p className="font-medium">
                  {session.subject.code} • {session.class.name}
                </p>
                <p className="text-sm text-zinc-600 dark:text-zinc-400">{session.faculty.name}</p>
              </div>
              <button
                type="button"
                onClick={() => handleContinue(session.id)}
                disabled={startVerification.isPending}
                className="rounded bg-black px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black"
              >
                {startVerification.isPending ? "Starting..." : "Continue"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
