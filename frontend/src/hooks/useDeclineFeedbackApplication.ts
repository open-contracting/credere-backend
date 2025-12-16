import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { declineApplicationFeedbackFn, declineApplicationRollbackFn } from "../api/public";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { ApplicationBaseInput, DeclineFeedbackInput, IApplicationResponse } from "../schemas/application";
import useApplicationContext from "./useApplicationContext";

type IUseDeclineFeedbackApplication = {
  declineFeedbackMutation: UseMutateFunction<IApplicationResponse, unknown, DeclineFeedbackInput, unknown>;
  declineRollbackMutation: UseMutateFunction<IApplicationResponse, unknown, ApplicationBaseInput, unknown>;
  isLoading: boolean;
};

export default function useDeclineFeedbackApplication(): IUseDeclineFeedbackApplication {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: declineFeedbackMutation, isLoading } = useMutation<
    IApplicationResponse,
    unknown,
    DeclineFeedbackInput,
    unknown
  >((payload) => declineApplicationFeedbackFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../decline-completed");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error on the decline feedback. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const { mutate: declineRollbackMutation, isLoading: isLoadingRollback } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => declineApplicationRollbackFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../decline");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error on rollback declined application. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { declineFeedbackMutation, declineRollbackMutation, isLoading: isLoading || isLoadingRollback };
}
