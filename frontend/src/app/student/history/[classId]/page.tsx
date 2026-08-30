"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useClassAttendance } from "@/queries/use-class-attendance";

export default function StudentClassAttendancePage() {
  const { classId } = useParams<{ classId: string }>();
  const { data: classAttendance } = useClassAttendance(classId);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <Link href="/student/history" className="text-sm underline">
        Back to history
      </Link>

      {classAttendance && (
        <>
          <h1 className="text-xl font-semibold">{classAttendance.class.subject}</h1>

          <div className="flex items-center gap-4 rounded-lg border border-black/10 p-4 dark:border-white/10">
            <p className="text-3xl font-semibold">{classAttendance.summary.percentage}%</p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {classAttendance.summary.present} / {classAttendance.summary.total} classes attended
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
              Recent Attendance
            </h2>

            {classAttendance.records.length === 0 && (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                No attendance recorded yet.
              </p>
            )}

            <div className="flex flex-col divide-y divide-black/10 dark:divide-white/10">
              {classAttendance.records.map((record) => (
                <div key={record.id} className="flex items-center justify-between py-2">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {new Date(record.marked_at).toLocaleString([], {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </p>
                  <span className="text-sm text-green-600 dark:text-green-400">✓ Present</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
