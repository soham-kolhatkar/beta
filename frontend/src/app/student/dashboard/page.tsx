"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogoutButton } from "@/components/logout-button";
import { useCurrentUser } from "@/queries/use-current-user";
import { useFaceStatus } from "@/queries/use-face-status";
import { useStartVerification } from "@/queries/use-start-verification";
import { useStudentDashboard } from "@/queries/use-student-dashboard";

export default function StudentDashboardPage() {
  const router = useRouter();
  const { data: user } = useCurrentUser();
  const { data: faceStatus } = useFaceStatus();
  const { data: dashboard } = useStudentDashboard();
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
      <p className="text-zinc-600 dark:text-zinc-400">Welcome, {user?.name}.</p>

      {faceStatus && !faceStatus.registered && (
        <div className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10">
          <p className="text-sm">Register your face before you can mark attendance.</p>
          <Link
            href="/student/face-registration"
            className="rounded bg-black px-3 py-1.5 text-sm text-white dark:bg-white dark:text-black"
          >
            Register Face
          </Link>
        </div>
      )}

      {dashboard && (
        <>
          <div className="flex items-center gap-4 rounded-lg border border-black/10 p-4 dark:border-white/10">
            <p className="text-3xl font-semibold">{dashboard.attendance.percentage}%</p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {dashboard.attendance.present} / {dashboard.attendance.total} classes attended
            </p>
          </div>

          <Link href="/student/history" className="text-sm underline">
            View Full Attendance History
          </Link>

          {dashboard.active_session && (
            <div className="flex flex-col gap-3">
              <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                Active Session
              </h2>
              <div className="flex items-center justify-between rounded-lg border border-black/10 p-4 dark:border-white/10">
                <div>
                  <p className="font-medium">
                    {dashboard.active_session.subject.code} • {dashboard.active_session.class.name}
                  </p>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {dashboard.active_session.faculty.name}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleContinue(dashboard.active_session!.id)}
                  disabled={startVerification.isPending}
                  className="rounded bg-black px-3 py-1.5 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-black"
                >
                  {startVerification.isPending ? "Starting..." : "Continue"}
                </button>
              </div>
            </div>
          )}

          {dashboard.today_classes.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                Today&apos;s Classes
              </h2>
              {dashboard.today_classes.map((session) => (
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
