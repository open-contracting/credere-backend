import type { PropsWithChildren } from "react";
import { useTranslation as useT } from "react-i18next";
import { Navigate } from "react-router-dom";

import type { USER_TYPES } from "../constants";
import useUser from "../hooks/useUser";

export interface ProtectedRouteProps extends PropsWithChildren {
  requiredUserType?: USER_TYPES;
}

export default function ProtectedRoute({ children, requiredUserType = undefined }: ProtectedRouteProps) {
  const user = useUser();
  const { t } = useT();

  if (!user) return <Navigate to="/login" replace />;
  if (requiredUserType && requiredUserType !== user.type) {
    throw new Error(t("Not authorized to access this page"));
  }

  return <>{children}</>;
}
