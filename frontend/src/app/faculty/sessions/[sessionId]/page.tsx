"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useSessionRoster } from "@/queries/use-session-roster";

const STATUS_LABEL: Record<string, string> = {
  PRESENT: "Present",
  NOT_MARKED: "Not marked",
  VERIFICATION_ISSUE: "Verification issue",
};

const STATUS_COLOR: Record<string, string> = {
  PRESENT: "text-green-600 dark:text-green-400",
  NOT_MARKED: "text-zinc-500 dark:text-zinc-400",
  VERIFICATION_ISSUE: "text-red-600 dark:text-red-400",
};

export default function SessionRosterPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { data: roster } = useSessionRoster(sessionId);
  const [search, setSearch] = useState("");

  const filteredStudents = roster?.students.filter((student) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;
    return (
      student.name.toLowerCase().includes(query) || student.prn.toLowerCase().includes(query)
    );
  });

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <Link href="/faculty/dashboard" className="text-sm underline">
        Back to dashboard
      </Link>

      {roster && (
        <>
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold">
              {roster.session.subject} • {roster.session.class_name}
            </h1>
            {roster.session.status === "ACTIVE" ? (
              <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <span className="h-2 w-2 rounded-full bg-green-500" /> LIVE
              </span>
            ) : (
              <span className="text-xs text-zinc-500 dark:text-zinc-400">Ended</span>
            )}
          </div>

          <p className="text-lg">
            {roster.summary.present} / {roster.summary.total_students} Present
          </p>
          <div className="h-2 w-full overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
            <div
              className="h-full bg-black dark:bg-white"
              style={{
                width:
                  roster.summary.total_students > 0
                    ? `${(roster.summary.present / roster.summary.total_students) * 100}%`
                    : "0%",
              }}
            />
          </div>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            {roster.summary.not_marked} not marked • {roster.summary.verification_issues}{" "}
            verification issue{roster.summary.verification_issues === 1 ? "" : "s"}
          </p>

          <input
            type="search"
            placeholder="Search by name or PRN..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="rounded border border-black/10 px-3 py-2 dark:border-white/10 dark:bg-zinc-950"
          />

          <div className="flex flex-col divide-y divide-black/10 dark:divide-white/10">
            {filteredStudents?.map((student) => (
              <div key={student.student_id} className="flex items-center justify-between py-2">
                <div>
                  <p>{student.name}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">{student.prn}</p>
                </div>
                <span className={`text-sm ${STATUS_COLOR[student.status]}`}>
                  {STATUS_LABEL[student.status]}
                </span>
              </div>
            ))}
            {filteredStudents?.length === 0 && (
              <p className="py-4 text-center text-sm text-zinc-500 dark:text-zinc-400">
                No students match &quot;{search}&quot;.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
