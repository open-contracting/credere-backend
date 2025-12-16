import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import {
  confirmCreditProductFn,
  rollbackConfirmCreditProductFn,
  rollbackSelectCreditProductFn,
  selectCreditProductFn,
} from "../api/public";
import { DISPATCH_ACTIONS, QUERY_KEYS } from "../constants";
import type { ApplicationBaseInput, IApplicationResponse, SelectCreditProductInput } from "../schemas/application";
import useApplicationContext from "./useApplicationContext";

type IUseGetCreditProductsOptions = {
  selectCreditProductMutation: UseMutateFunction<IApplicationResponse, unknown, SelectCreditProductInput, unknown>;
  rollbackSelectCreditProductMutation: UseMutateFunction<IApplicationResponse, unknown, ApplicationBaseInput, unknown>;
  confirmCreditProductMutation: UseMutateFunction<IApplicationResponse, unknown, ApplicationBaseInput, unknown>;
  rollbackConfirmCreditProductMutation: UseMutateFunction<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >;
  isLoading: boolean;
};

export default function useSelectCreditProduct(): IUseGetCreditProductsOptions {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const applicationContext = useApplicationContext();
  const { enqueueSnackbar } = useSnackbar();

  const { mutate: selectCreditProductMutation, isLoading } = useMutation<
    IApplicationResponse,
    unknown,
    SelectCreditProductInput,
    unknown
  >((payload) => selectCreditProductFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../confirm-credit-product");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error selecting credit product. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const { mutate: rollbackSelectCreditProductMutation, isLoading: isLoadingRollback } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => rollbackSelectCreditProductFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../credit-options");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error on rollback credit product selection. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const { mutate: confirmCreditProductMutation, isLoading: isLoadingConfirm } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => confirmCreditProductFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../documents");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error on rollback credit product selection. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const { mutate: rollbackConfirmCreditProductMutation, isLoading: isLoadingRollbackConfirm } = useMutation<
    IApplicationResponse,
    unknown,
    ApplicationBaseInput,
    unknown
  >((payload) => rollbackConfirmCreditProductFn(payload), {
    onSuccess: (data) => {
      queryClient.setQueryData([QUERY_KEYS.application_uuid, data.application.uuid], data);
      applicationContext.dispatch({ type: DISPATCH_ACTIONS.SET_APPLICATION, payload: data });
      navigate("../confirm-credit-product");
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error on rollback confirm credit product. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return {
    selectCreditProductMutation,
    confirmCreditProductMutation,
    rollbackSelectCreditProductMutation,
    rollbackConfirmCreditProductMutation,
    isLoading: isLoading || isLoadingRollback || isLoadingConfirm || isLoadingRollbackConfirm,
  };
}
