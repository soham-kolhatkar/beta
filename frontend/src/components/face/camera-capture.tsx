"use client";

import { useEffect, useRef, useState } from "react";

type CameraState = "idle" | "requesting" | "streaming" | "denied" | "unavailable";

/**
 * Live camera preview with an oval guide overlay and a manual capture
 * button. No live client-side face detection in this phase (docs/UI.md
 * §17-18 describe automatic-capture guidance as the ideal, but that needs
 * its own model/library evaluation — deliberately out of scope for now;
 * manual capture is the primary path here, not just a fallback).
 * Camera access is requested only after an explicit user action, and every
 * track is stopped on unmount (docs/SECURITY.md §29: camera shouldn't stay
 * active after it's no longer needed).
 */
export function CameraCapture({
  guidance,
  onCapture,
}: {
  guidance: string;
  onCapture: (blob: Blob) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("idle");

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // The <video> element only exists in the DOM once state === "streaming"
  // (it's conditionally rendered below), so the stream can't be attached
  // inline in requestCamera() — videoRef.current would still be null at that
  // point. Attaching it here runs after React has actually mounted the
  // element.
  useEffect(() => {
    if (state === "streaming" && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [state]);

  async function requestCamera() {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("unavailable");
      return;
    }

    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      setState("streaming");
    } catch {
      setState("denied");
    }
  }

  function capture() {
    const video = videoRef.current;
    if (!video) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) onCapture(blob);
    }, "image/jpeg");
  }

  if (state === "idle") {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-zinc-600 dark:text-zinc-400">
          We need camera access to verify your identity. Your camera is used only during face
          registration.
        </p>
        <button
          type="button"
          onClick={requestCamera}
          className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
        >
          Allow Camera
        </button>
      </div>
    );
  }

  if (state === "requesting") {
    return <p className="text-center text-zinc-600 dark:text-zinc-400">Preparing camera...</p>;
  }

  if (state === "denied") {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <p className="text-red-600 dark:text-red-400">
          Camera access was denied. Please allow camera access in your browser settings and try
          again.
        </p>
        <button
          type="button"
          onClick={requestCamera}
          className="rounded border border-black/10 px-4 py-2 dark:border-white/10"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (state === "unavailable") {
    return (
      <p className="text-center text-red-600 dark:text-red-400">
        Camera access isn&apos;t available on this device/browser.
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full max-w-sm overflow-hidden rounded-lg bg-black">
        <video ref={videoRef} autoPlay playsInline muted className="w-full" />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-56 w-44 rounded-[50%] border-2 border-white/70" />
        </div>
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{guidance}</p>
      <button
        type="button"
        onClick={capture}
        className="rounded bg-black px-4 py-2 text-white dark:bg-white dark:text-black"
      >
        Capture
      </button>
    </div>
  );
}
