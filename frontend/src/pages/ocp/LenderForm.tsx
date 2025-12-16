import { zodResolver } from "@hookform/resolvers/zod";
import { Box } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useEffect, useState } from "react";
import { FormProvider, type SubmitHandler, useForm } from "react-hook-form";
import { useTranslation as useT } from "react-i18next";
import { Link } from "react-router-dom";
import { lenderSchema, type ProviderInput } from "src/schemas/OCPsettings";
import Button from "src/stories/button/Button";
import FormInput from "src/stories/form-input/FormInput";
import FormSelect from "src/stories/form-select/FormSelect";
import Title from "src/stories/title/Title";
import { z } from "zod";

import { getLenderFn } from "../../api/private";
import CreditProductList from "../../components/CreditProductList";
import { LENDER_TYPES, QUERY_KEYS } from "../../constants";
import { useParamsTypeSafe } from "../../hooks/useParamsTypeSafe";
import useUpsertLender from "../../hooks/useUpsertLender";
import type { ILender } from "../../schemas/application";
import Loader from "../../stories/loader/Loader";
import ApplicationErrorPage from "../msme/ApplicationErrorPage";

export interface LenderFormProps {
  lender?: ILender | null;
}

export function LenderForm({ lender = null }: LenderFormProps) {
  const { t } = useT();
  const { createLenderMutation, updateLenderMutation, isLoading, isError } = useUpsertLender();

  const methods = useForm<ProviderInput>({
    resolver: zodResolver(lenderSchema),
    defaultValues: lender || {},
  });
  const {
    reset,
    handleSubmit,

    formState: { isSubmitSuccessful },
  } = methods;

  useEffect(() => {
    if (isSubmitSuccessful && !isError && !isLoading) {
      reset();
    }
  }, [isSubmitSuccessful, isError, isLoading]);

  const onSubmitHandler: SubmitHandler<ProviderInput> = (values) => {
    if (lender) {
      updateLenderMutation({ ...values, id: lender.id });
    } else {
      createLenderMutation(values);
    }
  };

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 lg:mb-8 md:mb-8 mb-4 md:grid-cols-2 gap-4 ">
        <div className="flex items-end col-span-1 md:mr-10">
          <Title className="mb-0" type="page" label={t("Settings")} />
        </div>
        <div className="flex justify-start items-start my-4 col-span-1 md:justify-end md:my-0 md:ml-10 lg:justify-end lg:col-span-2">
          <div className="grid grid-cols-1 gap-4 md:flex md:gap-0">
            <div>
              <Button className="md:mr-4" label={t("Dashboard")} component={Link} to="/" />
            </div>

            <div>
              <Button label={t("Applications")} component={Link} to="/admin/applications" />
            </div>
          </div>
        </div>
      </div>

      <Title
        type="section"
        label={lender ? t("Edit Credit Provider") : t("Add New Credit Provider")}
        className="mb-6"
      />
      <FormProvider {...methods}>
        <Box
          component="form"
          onSubmit={handleSubmit(onSubmitHandler)}
          noValidate
          autoComplete="off"
          maxWidth="md"
          sx={{
            display: "flex",
            flexDirection: "column",
            borderRadius: 0,
          }}
        >
          <FormInput
            className="w-3/5"
            label={t("Credit provider name (as you want it to appear in the Credere UI)")}
            name="name"
            big={false}
            placeholder={t("Credit provider name")}
          />
          <FormSelect
            className="w-3/5"
            label={t("Select the credit provider type")}
            name="type"
            options={LENDER_TYPES}
            placeholder={t("Type")}
          />
          <FormInput
            className="w-3/5"
            label={t("Group destination to send notifications of new applications")}
            name="email_group"
            big={false}
            placeholder={t("Email group list")}
          />
          <FormInput
            className="w-3/5"
            label={t("Credit provider logo (as you want it to appear in the Credere UI)")}
            name="logo_filename"
            big={false}
            placeholder={t("Credit provider logo")}
          />
          <FormInput
            className="w-3/5"
            label={t(
              "A URL to the lender onboarding system, if any, to indicate to the borrower where to continue the application process",
            )}
            name="external_onboarding_url"
            big={false}
            placeholder={t("URL to the lender onboarding system")}
          />
          <FormInput
            className="w-3/5"
            label={t(
              "Set service level agreement (SLA) agreed timeframe for processing applications in Credere (days)",
            )}
            name="sla_days"
            type="number"
            big={false}
            placeholder={t("SLA days")}
          />

          {lender && (
            <>
              <Title type="subsection" className="mt-5 mb-2" label={t("Credit Products of Lender")} />
              <CreditProductList rows={lender.credit_products} />
              <Button
                size="small"
                noIcon
                primary={false}
                className="my-2"
                label={t("+ Add New Credit Product")}
                component={Link}
                to={`/settings/lender/${lender.id}/credit-product/new`}
              />
            </>
          )}

          <div className="mt-8 grid grid-cols-1 gap-4 md:flex md:gap-0">
            <div>
              <Button className="md:mr-4" primary={false} label={t("Back")} component={Link} to="/settings" />
            </div>
            <div>
              <Button
                disabled={isLoading}
                label={lender ? t("Update Credit Provider") : t("Save and Add Credit Product")}
                type="submit"
              />
            </div>
          </div>
        </Box>
      </FormProvider>
    </>
  );
}

export function LoadLender() {
  const { t } = useT();
  const [queryError, setQueryError] = useState<string>("");

  const { id } = useParamsTypeSafe(
    z.object({
      id: z.coerce.string(),
    }),
  );

  const { isLoading, data } = useQuery({
    queryKey: [QUERY_KEYS.lenders, `${id}`],
    queryFn: async (): Promise<ILender | null> => {
      const lender = await getLenderFn(id);
      return lender;
    },
    retry: 1,
    enabled: !!id,
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response && error.response.data && error.response.data.detail) {
        setQueryError(error.response.data.detail);
      } else {
        setQueryError(t("Error loading lender"));
      }
    },
  });

  return (
    <>
      {isLoading && <Loader />}
      {!isLoading && !queryError && <LenderForm lender={data} />}
      {queryError && <ApplicationErrorPage message={queryError} />}
    </>
  );
}
