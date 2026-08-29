"use client";

import { isAxiosError } from "axios";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CameraCapture } from "@/components/face/camera-capture";
import { useCompleteVerification } from "@/queries/use-complete-verification";
import { useSubmitFace } from "@/queries/use-submit-face";
import { useSubmitLocation } from "@/queries/use-submit-location";

type Phase = "location" | "face" | "completing" | "done";

type LocationStep =
  | "idle"
  | "requesting"
  | "submitting"
  | "rejected"
  | "denied"
  | "unavailable"
  | "error";

type FaceStep = "capture" | "preview" | "submitting" | "rejected" | "error";

function errorMessageFrom(error: unknown): string {
  return isAxiosError(error) && error.response?.data?.error?.message
    ? error.response.data.error.message
    : "Something went wrong. Please try again.";
}

export default function VerifyLocationPage() {
  const { verificationId } = useParams<{ verificationId: string }>();
  const submitLocation = useSubmitLocation();
  const submitFace = useSubmitFace();
  const completeVerification = useCompleteVerification();

  const [phase, setPhase] = useState<Phase>("location");
  const [message, setMessage] = useState<string | null>(null);

  const [locationStep, setLocationStep] = useState<LocationStep>("idle");

  const [faceStep, setFaceStep] = useState<FaceStep>("capture");
  const [captured, setCaptured] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // /complete needs no input beyond the verification id, so it fires as
  // soon as the face step succeeds rather than waiting on another user
  // action — this is a side effect synchronizing with the backend once
  // `phase` changes, not state that could be derived at render time.
  useEffect(() => {
    if (phase === "completing") {
      completeVerification.mutate(verificationId, {
        onSuccess: () => setPhase("done"),
        onError: (error) => {
          setMessage(errorMessageFrom(error));
          setPhase("face");
          setFaceStep("error");
        },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function requestLocation() {
    if (!navigator.geolocation) {
      setLocationStep("unavailable");
      return;
    }

    setLocationStep("requesting");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocationStep("submitting");
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
                setPhase("face");
              } else {
                setMessage(result.message ?? "We couldn't verify your location.");
                setLocationStep("rejected");
              }
            },
            onError: (error) => {
              setMessage(errorMessageFrom(error));
              setLocationStep("error");
            },
          },
        );
      },
      () => setLocationStep("denied"),
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  function handleFaceCapture(blob: Blob) {
    setCaptured(blob);
    setPreviewUrl(URL.createObjectURL(blob));
    setFaceStep("preview");
  }

  function retakeFace() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setCaptured(null);
    submitFace.reset();
    setFaceStep("capture");
  }

  function confirmFace() {
    if (!captured) return;
    setFaceStep("submitting");
    submitFace.mutate(
      { verificationId, image: captured },
      {
        onSuccess: (result) => {
          if (result.verified) {
            setPhase("completing");
          } else {
            setMessage(result.message ?? "We couldn't verify your identity.");
            setFaceStep("rejected");
          }
        },
        onError: (error) => {
          setMessage(errorMessageFrom(error));
          setFaceStep("error");
        },
      },
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
      <h1 className="text-xl font-semibold">
        {phase === "location" && "Verify Your Location"}
        {phase === "face" && "Verify Your Face"}
        {(phase === "completing" || phase === "done") && "Marking Attendance"}
      </h1>

      {phase === "location" && (
        <>
          {(locationStep === "idle" ||
            locationStep === "denied" ||
            locationStep === "unavailable") && (
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
              {locationStep === "denied" && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  Location access was denied. Please allow location access and try again.
                </p>
              )}
              {locationStep === "unavailable" && (
                <p className="text-sm text-red-600 dark:text-red-400">
                  Location access isn&apos;t available on this device/browser.
                </p>
              )}
            </div>
          )}

          {(locationStep === "requesting" || locationStep === "submitting") && (
            <p className="text-zinc-600 dark:text-zinc-400">
              {locationStep === "requesting" ? "Getting your location..." : "Verifying..."}
            </p>
          )}

          {locationStep === "rejected" && (
            <div className="flex flex-col items-center gap-4 text-center">
              <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
              <button
                type="button"
                onClick={() => {
                  submitLocation.reset();
                  setLocationStep("idle");
                }}
                className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
              >
                Try Again
              </button>
            </div>
          )}

          {locationStep === "error" && (
            <div className="flex flex-col items-center gap-4 text-center">
              <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
              <Link href="/student/dashboard" className="text-sm underline">
                Back to dashboard
              </Link>
            </div>
          )}
        </>
      )}

      {phase === "face" && (
        <>
          {faceStep === "capture" && (
            <CameraCapture
              guidance="Keep your face centered and well lit."
              onCapture={handleFaceCapture}
            />
          )}

          {faceStep === "preview" && previewUrl && (
            <div className="flex flex-col items-center gap-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previewUrl}
                alt="Captured face preview"
                className="w-full max-w-sm rounded-lg"
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={retakeFace}
                  className="rounded border border-black/10 px-4 py-2 dark:border-white/10"
                >
                  Retake
                </button>
                <button
                  type="button"
                  onClick={confirmFace}
                  className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
                >
                  Confirm
                </button>
              </div>
            </div>
          )}

          {faceStep === "submitting" && (
            <p className="text-zinc-600 dark:text-zinc-400">Verifying...</p>
          )}

          {faceStep === "rejected" && (
            <div className="flex flex-col items-center gap-4 text-center">
              <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
              <button
                type="button"
                onClick={retakeFace}
                className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
              >
                Try Again
              </button>
            </div>
          )}

          {faceStep === "error" && (
            <div className="flex flex-col items-center gap-4 text-center">
              <p className="max-w-sm text-red-600 dark:text-red-400">{message}</p>
              <Link href="/student/dashboard" className="text-sm underline">
                Back to dashboard
              </Link>
            </div>
          )}
        </>
      )}

      {phase === "completing" && (
        <p className="text-zinc-600 dark:text-zinc-400">Marking your attendance...</p>
      )}

      {phase === "done" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="text-2xl">✓</p>
          <p>Attendance marked</p>
          <Link href="/student/dashboard" className="text-sm underline">
            Back to dashboard
          </Link>
        </div>
      )}
    </div>
  );
}
