import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { approveApplicationFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { ApproveApplicationInput, IApplication } from "../schemas/application";
import { handleRequestError } from "../util/validation";
import useApplicationContext from "./useSecureApplicationContext";

type IUseApproveApplication = {
  approveApplicationMutation: UseMutateFunction<IApplication, unknown, ApproveApplicationInput, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useApproveApplication(): IUseApproveApplication {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: approveApplicationMutation,
    isError,
    isLoading,
  } = useMutation<IApplication, unknown, ApproveApplicationInput, unknown>(
    (payload) => approveApplicationFn(payload),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, data.id], data);
        applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
        navigate("../stage-five-approved");
      },
      onError: (error) => {
        handleRequestError(error, enqueueSnackbar, t("Error approving the application. {{error}}", { error }));
      },
    },
  );

  return { approveApplicationMutation, isLoading, isError };
}
