"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useCurrentUser } from "@/queries/use-current-user";
import { dashboardPathForRole, type UserRole } from "@/lib/types";

export function RequireRole({
  role,
  children,
}: {
  role: UserRole;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { data: currentUser, isLoading } = useCurrentUser();

  useEffect(() => {
    if (isLoading) return;

    if (!currentUser) {
      router.replace("/login");
      return;
    }

    if (currentUser.role !== role) {
      router.replace(dashboardPathForRole(currentUser.role));
    }
  }, [isLoading, currentUser, role, router]);

  if (isLoading || !currentUser || currentUser.role !== role) {
    return null;
  }

  return <>{children}</>;
}
