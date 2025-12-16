import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { applicationLapseFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { IApplication } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseLapseApplication = {
  lapseApplicationMutation: UseMutateFunction<IApplication, unknown, number, unknown>;
  isLoading: boolean;
};

export default function useLapseApplication(): IUseLapseApplication {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: lapseApplicationMutation, isLoading } = useMutation<IApplication, unknown, number, unknown>(
    (id) => applicationLapseFn(id),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, data.id], data);
        applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
        navigate(`/applications/${data.id}/stage-five-lapsed`);
      },
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error lapsing the application. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { lapseApplicationMutation, isLoading };
}
