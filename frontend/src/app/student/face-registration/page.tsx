"use client";

import { isAxiosError } from "axios";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CameraCapture } from "@/components/face/camera-capture";
import { useRegisterFace } from "@/queries/use-register-face";

type Step = "capture" | "preview" | "success";

export default function FaceRegistrationPage() {
  const [step, setStep] = useState<Step>("capture");
  const [captured, setCaptured] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const registerFace = useRegisterFace();

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function handleCapture(blob: Blob) {
    setCaptured(blob);
    setPreviewUrl(URL.createObjectURL(blob));
    setStep("preview");
  }

  function retake() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setCaptured(null);
    registerFace.reset();
    setStep("capture");
  }

  function confirm() {
    if (!captured) return;
    registerFace.mutate(captured, { onSuccess: () => setStep("success") });
  }

  const errorMessage =
    registerFace.isError &&
    (isAxiosError(registerFace.error) && registerFace.error.response?.data?.error?.message
      ? registerFace.error.response.data.error.message
      : "Something went wrong. Please try again.");

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-6">
      <h1 className="text-xl font-semibold">Face Registration</h1>

      {step === "capture" && (
        <CameraCapture guidance="Keep your face centered and well lit." onCapture={handleCapture} />
      )}

      {step === "preview" && previewUrl && (
        <div className="flex flex-col items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Captured face preview"
            className="w-full max-w-sm rounded-lg"
          />

          {errorMessage && (
            <p className="max-w-sm text-center text-sm text-red-600 dark:text-red-400">
              {errorMessage}
            </p>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={retake}
              disabled={registerFace.isPending}
              className="rounded border border-black/10 px-4 py-2 disabled:opacity-50 dark:border-white/10"
            >
              Retake
            </button>
            <button
              type="button"
              onClick={confirm}
              disabled={registerFace.isPending}
              className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
            >
              {registerFace.isPending ? "Registering..." : "Confirm"}
            </button>
          </div>
        </div>
      )}

      {step === "success" && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="text-2xl">✓</p>
          <p>Face registered</p>
          <Link href="/student/dashboard" className="text-sm underline">
            Back to dashboard
          </Link>
        </div>
      )}
    </div>
  );
}
