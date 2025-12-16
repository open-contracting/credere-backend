import type {
  ILoginResponse,
  IResponse,
  IUpdatePasswordResponse,
  IUserResponse,
  LoginInput,
  ResetPasswordInput,
  SetupMFAInput,
  UpdatePasswordPayload,
} from "../schemas/auth";
import { authApi } from "./axios";

export const loginMFAUserFn = async (payload: LoginInput) => {
  const response = await authApi.post<ILoginResponse>("users/login", payload);
  return response.data;
};

export const setupMFAFn = async (payload: SetupMFAInput) => {
  const response = await authApi.put<IResponse>("users/setup-mfa", payload);
  return response.data;
};

export const logoutUserFn = async () => {
  const response = await authApi.get<IResponse>("users/logout");
  return response.data;
};

export const updatePasswordFn = async (payload: UpdatePasswordPayload) => {
  const response = await authApi.put<IUpdatePasswordResponse>("users/change-password", payload);
  return response.data;
};

export const resetPasswordFn = async (payload: ResetPasswordInput) => {
  const response = await authApi.post<IResponse>("users/forgot-password", payload);
  return response.data;
};

export const getMeFn = async () => {
  const response = await authApi.get<IUserResponse>("users/me");
  return response.data;
};
