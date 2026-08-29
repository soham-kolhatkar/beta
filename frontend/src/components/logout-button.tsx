"use client";

import { useRouter } from "next/navigation";
import { useLogout } from "@/queries/use-logout";

export function LogoutButton() {
  const router = useRouter();
  const logout = useLogout();

  return (
    <button
      type="button"
      onClick={() => logout.mutate(undefined, { onSuccess: () => router.replace("/login") })}
      disabled={logout.isPending}
      className="rounded border border-black/10 px-3 py-1.5 text-sm text-black disabled:opacity-50 dark:border-white/10 dark:text-zinc-50"
    >
      {logout.isPending ? "Signing out..." : "Sign out"}
    </button>
  );
}
