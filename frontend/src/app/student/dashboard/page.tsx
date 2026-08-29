"use client";

import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";
import { useCurrentUser } from "@/queries/use-current-user";
import { useFaceStatus } from "@/queries/use-face-status";

export default function StudentDashboardPage() {
  const { data: user } = useCurrentUser();
  const { data: faceStatus } = useFaceStatus();

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
    </div>
  );
}
