import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { updateBorrowerFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { IApplication, IUpdateBorrower } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseUpdateBorrower = {
  updateBorrowerMutation: UseMutateFunction<IApplication, unknown, IUpdateBorrower, unknown>;
  isLoading: boolean;
};

export default function useUpdateBorrower(): IUseUpdateBorrower {
  const { t } = useT();

  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: updateBorrowerMutation, isLoading } = useMutation<IApplication, unknown, IUpdateBorrower, unknown>(
    (payload) => updateBorrowerFn(payload),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, `${data.id}`], data);
        applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
        enqueueSnackbar(t("Borrower Updated"), {
          variant: "success",
        });
      },
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error updating borrower. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { updateBorrowerMutation, isLoading };
}
