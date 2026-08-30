"use client";

import Link from "next/link";
import { useState } from "react";
import { useAttendanceHistory } from "@/queries/use-attendance-history";
import { useAttendanceSummary } from "@/queries/use-attendance-summary";

const PAGE_SIZE = 10;

export default function StudentHistoryPage() {
  const { data: summary } = useAttendanceSummary();
  const [page, setPage] = useState(1);
  const { data: history } = useAttendanceHistory(page, PAGE_SIZE);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <Link href="/student/dashboard" className="text-sm underline">
        Back to dashboard
      </Link>
      <h1 className="text-xl font-semibold">Attendance History</h1>

      {summary && (
        <>
          <div className="flex items-center gap-4 rounded-lg border border-black/10 p-4 dark:border-white/10">
            <p className="text-3xl font-semibold">{summary.overall.percentage}%</p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {summary.overall.present} / {summary.overall.total} classes attended
            </p>
          </div>

          {summary.subjects.length > 0 && (
            <div className="flex flex-col gap-2">
              <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">By Subject</h2>
              {summary.subjects.map((subject) => (
                <Link
                  key={subject.class_id}
                  href={`/student/history/${subject.class_id}`}
                  className="flex items-center justify-between rounded-lg border border-black/10 p-3 hover:bg-black/5 dark:border-white/10 dark:hover:bg-white/5"
                >
                  <p>{subject.subject}</p>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    {subject.percentage}% ({subject.present} / {subject.total})
                  </p>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">Recent Attendance</h2>

        {history?.items.length === 0 && (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">No attendance recorded yet.</p>
        )}

        <div className="flex flex-col divide-y divide-black/10 dark:divide-white/10">
          {history?.items.map((item) => (
            <div key={item.id} className="flex items-center justify-between py-2">
              <div>
                <p>{item.subject}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {new Date(item.marked_at).toLocaleString([], {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>
              </div>
              <span className="text-sm text-green-600 dark:text-green-400">✓ Present</span>
            </div>
          ))}
        </div>

        {history && history.pagination.total_pages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded border border-black/10 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-white/10"
            >
              Previous
            </button>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Page {history.pagination.page} of {history.pagination.total_pages}
            </p>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(history.pagination.total_pages, p + 1))}
              disabled={page >= history.pagination.total_pages}
              className="rounded border border-black/10 px-3 py-1.5 text-sm disabled:opacity-50 dark:border-white/10"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
