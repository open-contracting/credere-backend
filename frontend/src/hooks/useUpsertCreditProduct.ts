import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createCreditProductFn, updateCreditProductFn } from "../api/private";
import { QUERY_KEYS } from "../constants";
import type { ICreditProduct, ICreditProductBase, ICreditProductUpdate } from "../schemas/application";

type IUseUpsertCreditProduct = {
  createCreditProductMutation: UseMutateFunction<ICreditProduct, unknown, ICreditProductBase, unknown>;
  updateCreditProductMutation: UseMutateFunction<ICreditProduct, unknown, ICreditProductUpdate, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useUpsertCreditProduct(): IUseUpsertCreditProduct {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: createCreditProductMutation,
    isError,
    isLoading,
  } = useMutation<ICreditProduct, unknown, ICreditProductBase, unknown>((payload) => createCreditProductFn(payload), {
    onSuccess: (data) => {
      queryClient.invalidateQueries([QUERY_KEYS.lenders, `${data.lender_id}`]);
      navigate(`/settings/lender/${data.lender_id}/edit`);
      return data;
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error creating credit product. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const {
    mutate: updateCreditProductMutation,
    isLoading: isLoadingUpdate,
    isError: isErrorUpdate,
  } = useMutation<ICreditProduct, unknown, ICreditProductUpdate, unknown>(
    (payload) => updateCreditProductFn(payload),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries([QUERY_KEYS.lenders, `${data.lender_id}`]);
        queryClient.invalidateQueries([QUERY_KEYS.credit_product, `${data.id}`]);
        navigate(`/settings/lender/${data.lender_id}/edit`);
        return data;
      },
      onError: (error) => {
        if (axios.isAxiosError(error) && error.response) {
          if (error.response.data?.detail) {
            enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
              variant: "error",
            });
          }
        } else {
          enqueueSnackbar(t("Error updating credit product. {{error}}", { error }), {
            variant: "error",
          });
        }
      },
    },
  );

  return {
    createCreditProductMutation,
    updateCreditProductMutation,
    isLoading: isLoading || isLoadingUpdate,
    isError: isError || isErrorUpdate,
  };
}
