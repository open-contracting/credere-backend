import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { rejectApplicationFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { IApplication, RejectApplicationInput } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseRejectApplication = {
  rejectApplicationMutation: UseMutateFunction<IApplication, unknown, RejectApplicationInput, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useRejectApplication(): IUseRejectApplication {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: rejectApplicationMutation,
    isError,
    isLoading,
  } = useMutation<IApplication, unknown, RejectApplicationInput, unknown>((payload) => rejectApplicationFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.applications, data.id], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../stage-five-rejected");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error rejecting the application. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { rejectApplicationMutation, isLoading, isError };
}
