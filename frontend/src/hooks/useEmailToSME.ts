import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { emailToSME } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { EmailToSMEInput, IApplication } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseEmailToSME = {
  emailToSMEMutation: UseMutateFunction<IApplication, unknown, EmailToSMEInput, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useEmailToSME(): IUseEmailToSME {
  const { t } = useT();

  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: emailToSMEMutation,
    isError,
    isLoading,
  } = useMutation<IApplication, unknown, EmailToSMEInput, unknown>((payload) => emailToSME(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.applications, data.id], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
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
  });

  return { emailToSMEMutation, isLoading, isError };
}
