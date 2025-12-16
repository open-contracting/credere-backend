import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useEffect, useState } from "react";
import { useTranslation as useT } from "react-i18next";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { getApplicationFn } from "../api/private";
import { APPLICATION_STATUS, DISPATCH_ACTIONS, QUERY_KEYS, USER_TYPES } from "../constants";
import { useParamsTypeSafe } from "../hooks/useParamsTypeSafe";
import useApplicationContext from "../hooks/useSecureApplicationContext";
import ApplicationErrorPage from "../pages/msme/ApplicationErrorPage";
import ProtectedRoute from "../routes/ProtectedRoute";
import type { IApplication } from "../schemas/application";
import Loader from "../stories/loader/Loader";
import PageLayout from "./PageLayout";

export default function SecureApplicationLayout() {
  const { t } = useT();
  const navigate = useNavigate();
  const location = useLocation();
  const [queryError, setQueryError] = useState<string>("");
  const applicationContext = useApplicationContext();

  const { id } = useParamsTypeSafe(
    z.object({
      id: z.coerce.string(),
    }),
  );

  const { isLoading, data, refetch } = useQuery({
    queryKey: [QUERY_KEYS.applications, `${id}`],
    queryFn: async (): Promise<IApplication | null> => {
      const application = await getApplicationFn(id);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: application });
      return application;
    },
    retry: 1,
    enabled: !!id,
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response && error.response.data && error.response.data.detail) {
        setQueryError(error.response.data.detail);
      } else {
        setQueryError(t("Error loading application"));
      }
    },
  });

  useEffect(() => {
    if (data) {
      const application = data;
      const { pathname } = location;
      const lastSegment = pathname.substring(pathname.lastIndexOf("/") + 1);

      if (lastSegment !== "view") {
        if (application.status === APPLICATION_STATUS.LAPSED) {
          if (lastSegment !== "stage-five-lapsed") navigate("./stage-five-lapsed");
        } else if (application.status === APPLICATION_STATUS.APPROVED) {
          if (lastSegment !== "application-completed") navigate("./application-completed");
        } else if (application.status === APPLICATION_STATUS.REJECTED) {
          if (lastSegment !== "stage-five-rejected") navigate("./stage-five-rejected");
        }
        refetch();
      }
    }
  }, [data, navigate, location, refetch]);

  return (
    <ProtectedRoute requiredUserType={USER_TYPES.FI}>
      <PageLayout>
        {isLoading && <Loader />}
        {!isLoading && !queryError && <Outlet />}
        {queryError && <ApplicationErrorPage message={queryError} />}
      </PageLayout>
    </ProtectedRoute>
  );
}
