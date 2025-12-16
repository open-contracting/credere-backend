import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { updatePasswordFn } from "../api/auth";
import type { IUpdatePasswordResponse, UpdatePasswordPayload } from "../schemas/auth";

type IUseUpdatePassword = UseMutateFunction<IUpdatePasswordResponse, unknown, UpdatePasswordPayload, unknown>;

export default function useUpdatePassword(): IUseUpdatePassword {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useT();

  const { mutate: updatePasswordMutation } = useMutation<
    IUpdatePasswordResponse,
    unknown,
    UpdatePasswordPayload,
    unknown
  >((payload) => updatePasswordFn(payload), {
    onSuccess: (data) => {
      if (data.secret_code && data.session && data.username) {
        navigate(`/setup-mfa/${data.secret_code}/${data.session}?username=${data.username}`);
      } else {
        navigate("/password-created");
      }
    },
    onError: (error) => {
      console.log(error);
      enqueueSnackbar(`${t("Error on update password.")} ${error}`, {
        variant: "error",
      });
    },
  });

  return updatePasswordMutation;
}
