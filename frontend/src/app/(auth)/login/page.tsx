"use client";

import { isAxiosError } from "axios";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useCurrentUser } from "@/queries/use-current-user";
import { useLogin } from "@/queries/use-login";
import { dashboardPathForRole } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const { data: currentUser, isLoading: isLoadingCurrentUser } = useCurrentUser();
  const login = useLogin();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (currentUser) {
      router.replace(dashboardPathForRole(currentUser.role));
    }
  }, [currentUser, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    login.mutate(
      { email, password },
      {
        onSuccess: (user) => {
          router.replace(dashboardPathForRole(user.role));
        },
      },
    );
  }

  const errorMessage =
    login.isError &&
    (isAxiosError(login.error) && login.error.response?.status === 401
      ? "Incorrect email or password."
      : "Something went wrong. Please try again.");

  if (isLoadingCurrentUser || currentUser) {
    return null;
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-zinc-50 px-4 dark:bg-black">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-zinc-950"
      >
        <h1 className="text-xl font-semibold text-black dark:text-zinc-50">
          Sign in to GeoAttend
        </h1>

        <div className="flex flex-col gap-1">
          <label htmlFor="email" className="text-sm text-zinc-600 dark:text-zinc-400">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded border border-black/10 px-3 py-2 text-black dark:border-white/10 dark:text-zinc-50"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-sm text-zinc-600 dark:text-zinc-400">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded border border-black/10 px-3 py-2 text-black dark:border-white/10 dark:text-zinc-50"
          />
        </div>

        {errorMessage && <p className="text-sm text-red-600 dark:text-red-400">{errorMessage}</p>}

        <button
          type="submit"
          disabled={login.isPending}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50 dark:bg-white dark:text-black"
        >
          {login.isPending ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
