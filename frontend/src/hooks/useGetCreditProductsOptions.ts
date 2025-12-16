import { type UseMutateFunction, useMutation } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { getCreditProductOptionsFn } from "../api/public";
import type { GetCreditProductsOptionsInput, IApplicationCreditOptions } from "../schemas/application";

type IUseGetCreditProductsOptions = {
  getCreditProductOptionsMutation: UseMutateFunction<
    IApplicationCreditOptions,
    unknown,
    GetCreditProductsOptionsInput,
    unknown
  >;
  isLoading: boolean;
  data: IApplicationCreditOptions;
};

export default function useGetCreditProductsOptions(): IUseGetCreditProductsOptions {
  const { t } = useT();

  const { enqueueSnackbar } = useSnackbar();

  const {
    data,
    mutate: getCreditProductOptionsMutation,
    isLoading,
  } = useMutation<IApplicationCreditOptions, unknown, GetCreditProductsOptionsInput, unknown>(
    (payload) => getCreditProductOptionsFn(payload),
    {
      onSuccess: (dataResult) => dataResult,
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error getting credit product options. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return { getCreditProductOptionsMutation, isLoading, data: data || { loans: [], credit_lines: [] } };
}
