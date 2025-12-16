import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createLenderFn, updateLenderFn } from "../api/private";
import { QUERY_KEYS } from "../constants";
import type { ILender, ILenderBase, ILenderUpdate } from "../schemas/application";

type IUseUpsertLender = {
  createLenderMutation: UseMutateFunction<ILender, unknown, ILenderBase, unknown>;
  updateLenderMutation: UseMutateFunction<ILender, unknown, ILenderUpdate, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useUpsertLender(): IUseUpsertLender {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: createLenderMutation,
    isError,
    isLoading,
  } = useMutation<ILender, unknown, ILenderBase, unknown>((payload) => createLenderFn(payload), {
    onSuccess: (data) => {
      enqueueSnackbar(t('Credit Provider "{lenderName}" created', { lenderName: data.name }), {
        variant: "success",
      });
      navigate(`/settings/lender/${data.id}/credit-product/new`);
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
        enqueueSnackbar(t("Error creating lender. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const {
    mutate: updateLenderMutation,
    isLoading: isLoadingUpdate,
    isError: isErrorUpdate,
  } = useMutation<ILender, unknown, ILenderUpdate, unknown>((payload) => updateLenderFn(payload), {
    onSuccess: (data) => {
      queryClient.invalidateQueries([QUERY_KEYS.lenders]);
      navigate("/settings");
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
        enqueueSnackbar(t("Error updating lender. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return {
    createLenderMutation,
    updateLenderMutation,
    isLoading: isLoading || isLoadingUpdate,
    isError: isError || isErrorUpdate,
  };
}
