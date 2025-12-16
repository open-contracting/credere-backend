import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { changeEmailFn } from "../api/public";
import type { ChangeEmailInput } from "../schemas/application";

type IUseChangeEmail = {
  changeEmailMutation: UseMutateFunction<ChangeEmailInput, unknown, ChangeEmailInput, unknown>;
  isLoading: boolean;
  data?: ChangeEmailInput;
};

export default function useChangeEmail(): IUseChangeEmail {
  const { t } = useT();

  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: changeEmailMutation,
    isLoading,
    data,
  } = useMutation<ChangeEmailInput, unknown, ChangeEmailInput, unknown>((payload) => changeEmailFn(payload), {
    onSuccess: (dataResponse) => dataResponse,
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error changing primary email. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { changeEmailMutation, isLoading, data };
}
