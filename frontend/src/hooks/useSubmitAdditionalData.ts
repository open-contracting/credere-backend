import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { additionalDataSubmitFn } from "../api/public";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { ApplicationBaseInput, IApplicationResponse } from "../schemas/application";
import useApplicationContext from "./useApplicationContext";

type IUseSubmitAdditionalData = {
  submitAdditionalDataMutation: UseMutateFunction<IApplicationResponse, unknown, ApplicationBaseInput, unknown>;
  isLoading: boolean;
};

export default function useSubmitAdditionalData(): IUseSubmitAdditionalData {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: submitAdditionalDataMutation, isLoading } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => additionalDataSubmitFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../submission-completed");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error submiting additional data to the application. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { submitAdditionalDataMutation, isLoading };
}
