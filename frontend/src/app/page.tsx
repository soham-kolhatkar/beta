"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useCurrentUser } from "@/queries/use-current-user";
import { dashboardPathForRole } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const { data: user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? dashboardPathForRole(user.role) : "/login");
  }, [isLoading, user, router]);

  return null;
}
