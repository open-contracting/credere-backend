import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { confirmChangeEmailFn } from "../api/public";
import type { ChangeEmailInput, ConfirmChangeEmailInput } from "../schemas/application";

type IUseConfirmChangeEmail = {
  confirmChangeEmailMutation: UseMutateFunction<ChangeEmailInput, unknown, ConfirmChangeEmailInput, unknown>;
  isLoading: boolean;
  data?: ChangeEmailInput;
};

export default function useConfirmChangeEmail(): IUseConfirmChangeEmail {
  const { t } = useT();

  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: confirmChangeEmailMutation,
    isLoading,
    data,
  } = useMutation<ChangeEmailInput, unknown, ConfirmChangeEmailInput, unknown>(
    (payload) => confirmChangeEmailFn(payload),
    {
      onSuccess: (dataResponse) => dataResponse,
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error confirming change of primary email. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { confirmChangeEmailMutation, isLoading, data };
}
