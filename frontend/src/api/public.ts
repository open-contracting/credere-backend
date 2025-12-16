import type {
  ApplicationBaseInput,
  ChangeEmailInput,
  ConfirmChangeEmailInput,
  DeclineApplicationInput,
  DeclineFeedbackInput,
  GetCreditProductsOptionsInput,
  IApplicationCreditOptions,
  IApplicationResponse,
  IBorrowerDocument,
  ICreditProduct,
  SelectCreditProductInput,
  UploadFileInput,
} from "../schemas/application";
import { publicApi } from "./axios";

export const applicationAccessSchemeFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/access-scheme", payload);
  return response.data;
};

export const declineApplicationFn = async (payload: DeclineApplicationInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/decline", payload);
  return response.data;
};

export const declineApplicationFeedbackFn = async (payload: DeclineFeedbackInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/decline-feedback", payload);
  return response.data;
};

export const declineApplicationRollbackFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/rollback-decline", payload);
  return response.data;
};

export const getApplicationFn = async (uuid: string) => {
  const response = await publicApi.get<IApplicationResponse>(`applications/uuid/${uuid}`);
  return response.data;
};

export const getCreditProductOptionsFn = async (payload: GetCreditProductsOptionsInput) => {
  const response = await publicApi.post<IApplicationCreditOptions>("applications/credit-product-options", payload);
  return response.data;
};

export const getCreditProductFn = async (id: string) => {
  const response = await publicApi.get<ICreditProduct>(`credit-products/${id}`);
  return response.data;
};

export const selectCreditProductFn = async (payload: SelectCreditProductInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/select-credit-product", payload);
  return response.data;
};

export const rollbackSelectCreditProductFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/rollback-select-credit-product", payload);
  return response.data;
};

export const confirmCreditProductFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/confirm-credit-product", payload);
  return response.data;
};

export const rollbackConfirmCreditProductFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/rollback-confirm-credit-product", payload);
  return response.data;
};

export const uploadFileFn = async (payload: UploadFileInput) => {
  const response = await publicApi.postForm<IBorrowerDocument>("applications/upload-document", payload);
  return response.data;
};

export const applicationSubmitFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/submit", payload);
  return response.data;
};

export const additionalDataSubmitFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/complete-information-request", payload);
  return response.data;
};

export const changeEmailFn = async (payload: ChangeEmailInput) => {
  const response = await publicApi.post<ChangeEmailInput>("applications/change-email", payload);
  return response.data;
};

export const confirmChangeEmailFn = async (payload: ConfirmChangeEmailInput) => {
  const response = await publicApi.post<ChangeEmailInput>("applications/confirm-change-email", payload);
  return response.data;
};

export const findAlternativeCreditOptionFn = async (payload: ApplicationBaseInput) => {
  const response = await publicApi.post<IApplicationResponse>("applications/find-alternative-credit-option", payload);
  return response.data;
};

export const getConstants = async () => {
  const response = await publicApi.get("meta");
  return response.data;
};
