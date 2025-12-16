import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { resetPasswordFn } from "../api/auth";
import type { IResponse, ResetPasswordInput } from "../schemas/auth";

type IUseResetPassword = {
  resetPasswordMutation: UseMutateFunction<IResponse, unknown, ResetPasswordInput, unknown>;
  isLoading: boolean;
};

export default function useResetPassword(): IUseResetPassword {
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { t } = useT();

  const { mutate: resetPasswordMutation, isLoading } = useMutation<IResponse, unknown, ResetPasswordInput, unknown>(
    (payload) => resetPasswordFn(payload),
    {
      onSuccess: () => {
        enqueueSnackbar(t("Check your email to continue"), {
          variant: "info",
        });
        navigate("/login");
      },
      onError: () => {
        // console.log(error);
        // show success message always to avoid email enumeration
        enqueueSnackbar(t("Check your email to continue"), {
          variant: "info",
        });
        navigate("/login");
      },
    },
  );

  return { resetPasswordMutation, isLoading };
}
