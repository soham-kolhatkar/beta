"use client";

import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useCreateSession } from "@/queries/use-create-session";
import { useFacultyClasses } from "@/queries/use-faculty-classes";

type LocationState = "idle" | "requesting" | "success" | "denied" | "unavailable";

interface Coords {
  latitude: number;
  longitude: number;
  accuracy: number;
}

function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const datePart = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  const timePart = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return `${datePart}T${timePart}`;
}

export default function CreateSessionPage() {
  const router = useRouter();
  const { data: classes, isLoading: isLoadingClasses } = useFacultyClasses();
  const createSession = useCreateSession();

  const [selectedClassId, setSelectedClassId] = useState("");
  const [startsAt, setStartsAt] = useState(() => toDatetimeLocalValue(new Date()));
  const [endsAt, setEndsAt] = useState(() =>
    toDatetimeLocalValue(new Date(Date.now() + 60 * 60 * 1000)),
  );
  const [radiusMeters, setRadiusMeters] = useState(100);
  const [locationState, setLocationState] = useState<LocationState>("idle");
  const [coords, setCoords] = useState<Coords | null>(null);

  // Falls back to the first class until the faculty explicitly picks one —
  // derived at render time rather than synced via an effect (there's
  // nothing external to subscribe to here, just a default).
  const classId = selectedClassId || classes?.[0]?.id || "";

  function requestLocation() {
    if (!navigator.geolocation) {
      setLocationState("unavailable");
      return;
    }
    setLocationState("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setLocationState("success");
      },
      () => setLocationState("denied"),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!coords || !classId) return;

    createSession.mutate(
      {
        class_id: classId,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        latitude: coords.latitude,
        longitude: coords.longitude,
        radius_meters: radiusMeters,
      },
      { onSuccess: () => router.push("/faculty/dashboard") },
    );
  }

  const errorMessage =
    createSession.isError &&
    (isAxiosError(createSession.error) && createSession.error.response?.data?.error?.message
      ? createSession.error.response.data.error.message
      : "Something went wrong. Please try again.");

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-zinc-950"
      >
        <h1 className="text-xl font-semibold">Create Attendance Session</h1>

        <div className="flex flex-col gap-1">
          <label htmlFor="class" className="text-sm text-zinc-600 dark:text-zinc-400">
            Class
          </label>
          <select
            id="class"
            required
            value={classId}
            onChange={(event) => setSelectedClassId(event.target.value)}
            className="rounded border border-black/10 px-3 py-2 dark:border-white/10 dark:bg-zinc-950"
          >
            {isLoadingClasses && <option value="">Loading...</option>}
            {classes?.length === 0 && <option value="">No classes assigned</option>}
            {classes?.map((classItem) => (
              <option key={classItem.id} value={classItem.id}>
                {classItem.subject.code} • {classItem.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-3">
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="starts-at" className="text-sm text-zinc-600 dark:text-zinc-400">
              Starts
            </label>
            <input
              id="starts-at"
              type="datetime-local"
              required
              value={startsAt}
              onChange={(event) => setStartsAt(event.target.value)}
              className="rounded border border-black/10 px-3 py-2 dark:border-white/10 dark:bg-zinc-950"
            />
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="ends-at" className="text-sm text-zinc-600 dark:text-zinc-400">
              Ends
            </label>
            <input
              id="ends-at"
              type="datetime-local"
              required
              value={endsAt}
              onChange={(event) => setEndsAt(event.target.value)}
              className="rounded border border-black/10 px-3 py-2 dark:border-white/10 dark:bg-zinc-950"
            />
          </div>
        </div>

        {/* docs/UI.md §28 shows a map preview; no map library is wired up
            yet, so this is a text-only equivalent (accuracy + confirm) —
            same deliberate scope reduction as camera-capture.tsx's manual
            capture in Phase 3. */}
        <div className="flex flex-col gap-2">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">Location</span>
          {locationState === "success" && coords ? (
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                ● You are here (±{Math.round(coords.accuracy)} m)
              </p>
              <button type="button" onClick={requestLocation} className="text-sm underline">
                Update
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={requestLocation}
              className="rounded border border-black/10 px-3 py-2 text-sm dark:border-white/10"
            >
              {locationState === "requesting" ? "Getting location..." : "Use Current Location"}
            </button>
          )}
          {locationState === "denied" && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Location access was denied. Please allow location access and try again.
            </p>
          )}
          {locationState === "unavailable" && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Location access isn&apos;t available on this device/browser.
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="radius" className="text-sm text-zinc-600 dark:text-zinc-400">
            Radius (meters)
          </label>
          <input
            id="radius"
            type="number"
            required
            min={1}
            value={radiusMeters}
            onChange={(event) => setRadiusMeters(Number(event.target.value))}
            className="rounded border border-black/10 px-3 py-2 dark:border-white/10 dark:bg-zinc-950"
          />
        </div>

        {errorMessage && <p className="text-sm text-red-600 dark:text-red-400">{errorMessage}</p>}

        <button
          type="submit"
          disabled={createSession.isPending || !coords || !classId}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
        >
          {createSession.isPending ? "Starting..." : "Start Session"}
        </button>

        <Link href="/faculty/dashboard" className="text-center text-sm underline">
          Cancel
        </Link>
      </form>
    </div>
  );
}
