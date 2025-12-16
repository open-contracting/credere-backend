import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { findAlternativeCreditOptionFn } from "../api/public";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { ApplicationBaseInput, IApplicationResponse } from "../schemas/application";
import { handleRequestError } from "../util/validation";
import useApplicationContext from "./useApplicationContext";

type IUseConfirmFindAlternativeCredit = {
  confirmFindAlternativeCreditMutation: UseMutateFunction<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >;
  isLoading: boolean;
};

export default function useConfirmFindAlternativeCredit(): IUseConfirmFindAlternativeCredit {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: confirmFindAlternativeCreditMutation, isLoading } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => findAlternativeCreditOptionFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate(`/application/${data.application.uuid}/credit-options`);
    },
    onError: (error) => {
      handleRequestError(error, enqueueSnackbar, t("Error creating new application. {{error}}", { error }));
    },
  });

  return { confirmFindAlternativeCreditMutation, isLoading };
}
