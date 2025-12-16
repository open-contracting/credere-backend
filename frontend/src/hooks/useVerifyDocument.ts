import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { verifyDocumentFn } from "../api/private";
import { QUERY_KEYS } from "../constants";
import type { IApplication, IVerifyDocument } from "../schemas/application";

type IUseVerifyDocument = {
  verifyDocumentMutation: UseMutateFunction<IApplication, unknown, IVerifyDocument, unknown>;
  isLoading: boolean;
};

export default function useVerifyDocument(): IUseVerifyDocument {
  const { t } = useT();

  const queryClient = useQueryClient();

  const { enqueueSnackbar } = useSnackbar();

  const { mutate: verifyDocumentMutation, isLoading } = useMutation<IApplication, unknown, IVerifyDocument, unknown>(
    (payload) => verifyDocumentFn(payload),
    {
      onSuccess: (data) => {
        queryClient.setQueryData([QUERY_KEYS.applications, `${data.id}`], data);
        enqueueSnackbar(t("Document verification state updated"), {
          variant: "info",
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
          enqueueSnackbar(t("Error verifying document. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { verifyDocumentMutation, isLoading };
}
