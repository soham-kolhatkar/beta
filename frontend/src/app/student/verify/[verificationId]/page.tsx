"use client";

import { isAxiosError } from "axios";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useSubmitLocation } from "@/queries/use-submit-location";

type Step =
  | "idle"
  | "requesting"
  | "submitting"
  | "verified"
  | "rejected"
  | "denied"
  | "unavailable"
  | "error";

export default function VerifyLocationPage() {
  const { verificationId } = useParams<{ verificationId: string }>();
  const submitLocation = useSubmitLocation();
  const [step, setStep] = useState<Step>("idle");
  const [message, setMessage] = useState<string | null>(null);

  function requestLocation() {
    if (!navigator.geolocation) {
      setStep("unavailable");
      return;
    }

    setStep("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setStep("submitting");
        submitLocation.mutate(
          {
            verificationId,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracyMeters: position.coords.accuracy,
          },
          {
            onSuccess: (result) => {
              if (result.verified) {
                setStep("verified");
              } else {
                setMessage(result.message ?? "We couldn't verify your location.");
                setStep("rejected");
              }
            },
            onError: (error) => {
              setMessage(
                isAxiosError(error) && error.response?.data?.error?.message
                  ? error.response.data.error.message
                  : "Something went wrong. Please try again.",
              );
              setStep("error");
            },
          },
        );
      },
      () => setStep("denied"),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
      <h1 className="text-xl font-semibold">Verify Your Location</h1>

      {(step === "idle" || step === "denied" || step === "unavailable") && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="text-zinc-600 dark:text-zinc-400">
            We need your location to confirm you&apos;re in the classroom.
          </p>
          <button
            type="button"
            onClick={requestLocation}
            className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
          >
            Share My Location
          </button>
          {step === "denied" && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Location access was denied. Please allow location access and try again.
            </p>
          )}
          {step === "unavailable" && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Location access isn&apos;t available on this device/browser.
            </p>
          )}
        </div>
      )}

      {(step === "requesting" || step === "submitting") && (
        <p className="text-zinc-600 dark:text-zinc-400">
          {step === "requesting" ? "Getting your location..." : "Verifying..."}
        </p>
      )}

      {step === "verified" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="text-2xl">✓</p>
          <p>Location verified</p>
          <p className="max-w-sm text-sm text-zinc-600 dark:text-zinc-400">
            Face verification is part of a later phase — there&apos;s nothing more to do here yet.
          </p>
          <Link href="/student/dashboard" className="text-sm underline">
            Back to dashboard
          </Link>
        </div>
      )}

      {step === "rejected" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
          <button
            type="button"
            onClick={() => {
              submitLocation.reset();
              setStep("idle");
            }}
            className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
          >
            Try Again
          </button>
        </div>
      )}

      {step === "error" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
          <Link href="/student/dashboard" className="text-sm underline">
            Back to dashboard
          </Link>
        </div>
      )}
    </div>
  );
}
