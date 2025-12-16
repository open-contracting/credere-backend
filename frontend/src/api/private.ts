import type {
  ApproveApplicationInput,
  EmailToSMEInput,
  IApplication,
  IApplicationsListResponse,
  IAward,
  ICreditProduct,
  ICreditProductBase,
  ICreditProductUpdate,
  ILender,
  ILenderBase,
  ILenderListResponse,
  ILenderUpdate,
  IUpdateAward,
  IUpdateBorrower,
  IVerifyDocument,
  PaginationInput,
  RejectApplicationInput,
} from "../schemas/application";
import type { CreateUserInput, IUser, IUsersListResponse, UpdateUserInput } from "../schemas/auth";
import type { StatisticsFI, StatisticsOCPoptIn, StatisticsParmsInput } from "../schemas/statitics";
import { authApi } from "./axios";

export const getApplicationsOCP = async (payload: PaginationInput) => {
  const response = await authApi.get<IApplicationsListResponse>("applications/admin-list", { params: payload });
  return response.data;
};

export const getApplicationsFI = async (payload: PaginationInput) => {
  const response = await authApi.get<IApplicationsListResponse>("applications", { params: payload });
  return response.data;
};

export const getApplicationFn = async (id: string) => {
  const response = await authApi.get<IApplication>(`applications/id/${id}`);
  return response.data;
};

export const getLenderFn = async (id: string) => {
  const response = await authApi.get<ILender>(`lenders/${id}`);
  return response.data;
};

export const getLendersFn = async () => {
  const response = await authApi.get<ILenderListResponse>("lenders");
  return response.data;
};

export const createLenderFn = async (payload: ILenderBase) => {
  const response = await authApi.post<ILender>("lenders", payload);
  return response.data;
};

export const updateAwardFn = async (awardData: IUpdateAward) => {
  const { application_id, ...payload } = awardData;
  const response = await authApi.put<IApplication>(`applications/${application_id}/award`, payload);
  return response.data;
};

export const updateBorrowerFn = async (awardData: IUpdateBorrower) => {
  const { application_id, ...payload } = awardData;
  const response = await authApi.put<IApplication>(`applications/${application_id}/borrower`, payload);
  return response.data;
};

export const updateLenderFn = async (payload: ILenderUpdate) => {
  const response = await authApi.put<ILender>(`lenders/${payload.id}`, payload);
  return response.data;
};

export const getCreditProductFn = async (id: string) => {
  const response = await authApi.get<ICreditProduct>(`credit-products/${id}`);
  return response.data;
};

export const getProcurementCategoriesFn = async () => {
  const response = await authApi.get<Array<string>>("procurement-categories");
  return response.data;
};

export const createCreditProductFn = async (payload: ICreditProductBase) => {
  const response = await authApi.post<ICreditProduct>(`lenders/${payload.lender_id}/credit-products`, payload);
  return response.data;
};

export const updateCreditProductFn = async (payload: ICreditProductUpdate) => {
  const response = await authApi.put<ICreditProduct>(`credit-products/${payload.id}`, payload);
  return response.data;
};

export const createUserFn = async (payload: CreateUserInput) => {
  const response = await authApi.post<IUser>("users", payload);
  return response.data;
};

export const updateUserFn = async (payload: UpdateUserInput) => {
  const response = await authApi.put<IUser>(`users/${payload.id}`, payload);
  return response.data;
};

export const getUserFn = async (id: string) => {
  const response = await authApi.get<IUser>(`users/${id}`);
  return response.data;
};

export const getUsersFn = async (payload: PaginationInput) => {
  const response = await authApi.get<IUsersListResponse>("users", { params: payload });
  return response.data;
};

export const applicationStartFn = async (id: number) => {
  const response = await authApi.post<IApplication>(`applications/${id}/start`);
  return response.data;
};

export const applicationLapseFn = async (id: number) => {
  const response = await authApi.post<IApplication>(`applications/${id}/lapse`);
  return response.data;
};

export const verifyDataFieldFn = async (awardData: IUpdateBorrower) => {
  const { application_id, ...payload } = awardData;
  const response = await authApi.put<IApplication>(`applications/${application_id}/verify-data-field`, payload);
  return response.data;
};

export const verifyDocumentFn = async (verifyDocumentPayload: IVerifyDocument) => {
  const { document_id, ...payload } = verifyDocumentPayload;
  const response = await authApi.put<IApplication>(`applications/documents/${document_id}/verify-document`, payload);
  return response.data;
};

export const downloadDocumentFn = async (id: number) => {
  const response = await authApi.get(`applications/documents/id/${id}`, {
    responseType: "blob",
  });

  return response.data;
};

export const downloadApplicants = async (lang: string) => {
  const response = await authApi.get(`applications/export/${lang}`, {
    responseType: "blob",
  });

  return response.data;
};

export const downloadApplicationFn = async (id: number, lang: string) => {
  const response = await authApi.get(`applications/${id}/download-application/${lang}`, {
    responseType: "blob",
  });

  return response.data;
};

export const emailToSME = async (emailToSMEPayload: EmailToSMEInput) => {
  const { application_id, ...payload } = emailToSMEPayload;
  const response = await authApi.post<IApplication>(`applications/email-sme/${application_id}`, payload);
  return response.data;
};

export const approveApplicationFn = async (approvePayload: ApproveApplicationInput) => {
  const { application_id, ...payload } = approvePayload;
  const response = await authApi.post<IApplication>(`applications/${application_id}/approve-application`, payload);
  return response.data;
};

export const rejectApplicationFn = async (rejectPayload: RejectApplicationInput) => {
  const { application_id, ...payload } = rejectPayload;
  const response = await authApi.post<IApplication>(`applications/${application_id}/reject-application`, payload);
  return response.data;
};

export const getPreviousAwardsFn = async (id: number) => {
  const response = await authApi.get<IAward[]>(`applications/${id}/previous-awards`);
  return response.data;
};

export const getStatisticsFI = async () => {
  const response = await authApi.get<StatisticsFI>("statistics-fi");
  return response.data;
};

export const getStatisticsOCPoptIn = async () => {
  const response = await authApi.get<StatisticsOCPoptIn>("statistics-ocp/opt-in");
  return response.data;
};

export const getStatisticsOCP = async (params: StatisticsParmsInput) => {
  const response = await authApi.get<StatisticsFI>("statistics-ocp", { params });
  return response.data;
};
