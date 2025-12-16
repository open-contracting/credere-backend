import type { FormSelectOption } from "../stories/form-select/FormSelect";
import { t } from "../util/i18n";

export const USER_LOCAL_STORAGE_KEY = "CREDERE_USER";
export const ACCESS_TOKEN_LOCAL_STORAGE_KEY = "CREDERE_USER_ACCESS_TOKEN";
export const LANG_STORAGE_KEY = "CREDERE_LANG";

export enum QUERY_KEYS {
  user = "user",
  application_uuid = "application_uuid",
  applications = "applications",
  lenders = "lenders",
  users = "users",
  credit_product = "credit_product",
  procurement_categories = "procurement_categories",
  downloadDocument = "downloadDocument",
  downloadApplication = "downloadApplication",
  awards = "awards",
  statistics_fi = "statistics_fi",
  statistics_ocp = "statistics_ocp",
  statistics_ocp_opt_in = "statistics_ocp_opt_in",
}

export const DISPATCH_ACTIONS = {
  SET_USER: "SET_USER",
  SET_LANG: "SET_LANG",
  SET_APPLICATION: "SET_APPLICATION",
};

export const PAGE_SIZES = [5, 10, 25];

export enum APPLICATION_STATUS {
  PENDING = "PENDING",
  ACCEPTED = "ACCEPTED",
  LAPSED = "LAPSED",
  DECLINED = "DECLINED",
  SUBMITTED = "SUBMITTED",
  STARTED = "STARTED",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  INFORMATION_REQUESTED = "INFORMATION_REQUESTED",
}

export const COMPLETED_STATUS = [APPLICATION_STATUS.REJECTED, APPLICATION_STATUS.APPROVED, APPLICATION_STATUS.LAPSED];

export const NOT_STARTED_STATUS = [APPLICATION_STATUS.SUBMITTED];

export const STARTED_STATUS = [APPLICATION_STATUS.STARTED, APPLICATION_STATUS.INFORMATION_REQUESTED];

export const LENDER_TYPES: FormSelectOption[] = [
  {
    value: "commercial_bank",
    label: t("Commercial Bank"),
  },
  {
    value: "fintech",
    label: t("FinTech"),
  },
  {
    value: "government_bank",
    label: t("Government Bank"),
  },
];

export const CREDIT_PRODUCT_TYPE = {
  LOAN: "LOAN",
  CREDIT_LINE: "CREDIT_LINE",
};

export const CREDIT_PRODUCT_OPTIONS: FormSelectOption[] = [
  {
    value: CREDIT_PRODUCT_TYPE.LOAN,
    label: t("Loan"),
  },
  {
    value: CREDIT_PRODUCT_TYPE.CREDIT_LINE,
    label: t("Credit line"),
  },
];

export enum STATISTICS_DATE_FILTER {
  CUSTOM_RANGE = "CUSTOM_RANGE",
  LAST_WEEK = "LAST_WEEK",
  LAST_MONTH = "LAST_MONTH",
}

export const STATISTICS_DATE_FILTER_OPTIONS: FormSelectOption[] = [
  {
    value: STATISTICS_DATE_FILTER.CUSTOM_RANGE,
    label: t("Custom range"),
  },
  {
    value: STATISTICS_DATE_FILTER.LAST_WEEK,
    label: t("Last week"),
  },
  {
    value: STATISTICS_DATE_FILTER.LAST_MONTH,
    label: t("Last month"),
  },
];

export const DEFAULT_BORROWER_SIZE = "NOT_INFORMED";

export enum USER_TYPES {
  OCP = "OCP",
  FI = "FI",
}

export const USER_TYPE_OPTIONS: FormSelectOption[] = [
  {
    value: USER_TYPES.OCP,
    label: t("OCP Admin"),
  },
  {
    value: USER_TYPES.FI,
    label: t("FI User"),
  },
];

export const AVAILABLE_LANGUAGES: FormSelectOption[] = [
  { label: "English", value: "en" },
  { label: "Español", value: "es" },
];
