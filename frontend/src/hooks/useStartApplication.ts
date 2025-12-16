import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { applicationStartFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { IApplication } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseStartApplication = {
  startApplicationMutation: UseMutateFunction<IApplication, unknown, number, unknown>;
  isLoading: boolean;
};

export default function useStartApplication(): IUseStartApplication {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: startApplicationMutation, isLoading } = useMutation<IApplication, unknown, number, unknown>(
    (id) => applicationStartFn(id),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, data.id], data);
        applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
        navigate(`/applications/${data.id}/stage-one`);
      },
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error starting the application. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { startApplicationMutation, isLoading };
}
