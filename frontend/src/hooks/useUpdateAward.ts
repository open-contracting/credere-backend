import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { updateAwardFn } from "../api/private";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { IApplication, IUpdateAward } from "../schemas/application";
import useApplicationContext from "./useSecureApplicationContext";

type IUseUpdateAward = {
  updateAwardMutation: UseMutateFunction<IApplication, unknown, IUpdateAward, unknown>;
  isLoading: boolean;
};

export default function useUpdateAward(): IUseUpdateAward {
  const { t } = useT();

  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: updateAwardMutation, isLoading } = useMutation<IApplication, unknown, IUpdateAward, unknown>(
    (payload) => updateAwardFn(payload),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, `${data.id}`], data);
        applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });

        enqueueSnackbar(t("Award Updated"), {
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
          enqueueSnackbar(t("Error updating award. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { updateAwardMutation, isLoading };
}
