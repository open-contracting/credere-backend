import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { setupMFAFn } from "../api/auth";
import type { IResponse, SetupMFAInput } from "../schemas/auth";

type IUseSetupMFA = {
  setupMFAMutation: UseMutateFunction<IResponse, unknown, SetupMFAInput, unknown>;
  isLoading: boolean;
};

export default function useSetupMFA(): IUseSetupMFA {
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { t } = useT();
  const { mutate: setupMFAMutation, isLoading } = useMutation<IResponse, unknown, SetupMFAInput, unknown>(
    (payload) => setupMFAFn(payload),
    {
      onSuccess: (_data) => {
        navigate("/password-created");
      },
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response && error.response.status === 401) {
          enqueueSnackbar(t("MFA code setup failed"), {
            variant: "error",
          });
        } else {
          enqueueSnackbar(`${t("Error in setup MFA ")} ${error}`, {
            variant: "error",
          });
        }
      },
    },
  );

  return { setupMFAMutation, isLoading };
}
