import { type UseMutateFunction, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createUserFn, updateUserFn } from "../api/private";
import { QUERY_KEYS } from "../constants";
import type { CreateUserInput, IUser, UpdateUserInput } from "../schemas/auth";

type IUseUpsertUser = {
  createUserMutation: UseMutateFunction<IUser, unknown, CreateUserInput, unknown>;
  updateUserMutation: UseMutateFunction<IUser, unknown, UpdateUserInput, unknown>;
  isLoading: boolean;
  isError: boolean;
};

export default function useUpsertUser(): IUseUpsertUser {
  const { t } = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();

  const {
    mutate: createUserMutation,
    isError,
    isLoading,
  } = useMutation<IUser, unknown, CreateUserInput, unknown>((payload) => createUserFn(payload), {
    onSuccess: (data) => {
      enqueueSnackbar(t('User "{name}" created', { name: data.name }), {
        variant: "success",
      });
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
        enqueueSnackbar(t("Error creating user. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  const {
    mutate: updateUserMutation,
    isLoading: isLoadingUpdate,
    isError: isErrorUpdate,
  } = useMutation<IUser, unknown, UpdateUserInput, unknown>((payload) => updateUserFn(payload), {
    onSuccess: (data) => {
      queryClient.invalidateQueries([QUERY_KEYS.users]);
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
        enqueueSnackbar(t("Error updating user. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return {
    createUserMutation,
    updateUserMutation,
    isLoading: isLoading || isLoadingUpdate,
    isError: isError || isErrorUpdate,
  };
}
