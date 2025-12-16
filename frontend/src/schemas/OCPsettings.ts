import { type TypeOf, z } from "zod";

import { CREDIT_PRODUCT_TYPE } from "../constants";

const creditProviderNameSchema = z.string().min(1, "Provider name is required");
const creditProviderTypeSchema = z.string().min(1, "Provider type is required");

export const lenderSchema = z.object({
  name: creditProviderNameSchema,
  type: creditProviderTypeSchema,
  sla_days: z.coerce
    .number()
    .int()
    .positive("SLA days must be greater than 0")
    .min(1, "SLA days must be greater than 0"),
  email_group: z.string().email("Email Address is invalid"),
  logo_filename: z.string(),
  external_onboarding_url: z.string().url("URL is invalid (Hint: include http:// or https://)"),
});

export type ProviderInput = TypeOf<typeof lenderSchema>;

export const creditProductSchema = z
  .object({
    borrower_size: z.string().min(1, "Borrower size is required"),
    lower_limit: z.coerce.number().min(1, "Lower limit must be greater than 0"),
    upper_limit: z.coerce.number().min(1, "Upper limit must be greater than 0"),
    interest_rate: z.string().min(1, "Interest rate description is required"),
    type: z.nativeEnum(CREDIT_PRODUCT_TYPE, {
      errorMap: (issue) => {
        switch (issue.code) {
          case "invalid_type":
          case "invalid_enum_value":
            return { message: "Type of product is required" };
          default:
            return { message: "Select an option" };
        }
      },
    }),
    procurement_category_to_exclude: z.string(),
    required_document_types: z.record(z.string().min(1), z.boolean()),
    borrower_types: z.record(z.string().min(1), z.boolean()),
    other_fees_total_amount: z.preprocess(
      (args) => (args === "" ? undefined : args),
      z.coerce
        .number({
          required_error: "Other fees total amount is required",
          invalid_type_error: "Other fees total amount must be a number",
        })
        .gte(0, "Other fees total amount must be greater or equal than 0"),
    ),
    other_fees_description: z.string().min(1, "Other fees description is required"),
    additional_information: z.string(),
    more_info_url: z.string().url("URL is invalid (Hint: include http:// or https://)"),
  })
  .refine((data) => data.lower_limit < data.upper_limit, {
    path: ["lower_limit"],
    message: "Lower limit must be less than upper limit",
  })
  .refine((data) => data.lower_limit < data.upper_limit, {
    path: ["upper_limit"],
    message: "Upper limit must be greater than lower limit",
  });

export type CreditProductInput = TypeOf<typeof creditProductSchema>;
