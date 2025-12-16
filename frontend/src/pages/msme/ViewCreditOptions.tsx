import { zodResolver } from "@hookform/resolvers/zod";
import { Box } from "@mui/material";
import { debounce } from "lodash";
import { useCallback, useEffect, useMemo } from "react";
import { FormProvider, type SubmitHandler, useForm } from "react-hook-form";
import { useTranslation as useT } from "react-i18next";
import NeedHelpComponent from "src/components/NeedHelpComponent";
import useConstants from "src/hooks/useConstants";
import Text from "src/stories/text/Text";
import Title from "src/stories/title/Title";

import CreditLinesTable from "../../components/CreditLinesTable";
import LoansTable from "../../components/LoansTable";
import { DEFAULT_BORROWER_SIZE } from "../../constants";
import useApplicationContext from "../../hooks/useApplicationContext";
import useGetCreditProductsOptions from "../../hooks/useGetCreditProductsOptions";
import useLocalizedDateFormatter from "../../hooks/useLocalizedDateFormatter";
import useSelectCreditProduct from "../../hooks/useSelectCreditProduct";
import {
  type CreditOptionsInput,
  type GetCreditProductsOptionsInput,
  type ICreditProduct,
  type RepaymentTermsInput,
  repaymentTermsSchema,
  type SelectCreditProductInput,
} from "../../schemas/application";
import FormInput from "../../stories/form-input/FormInput";
import FormSelect from "../../stories/form-select/FormSelect";
import RadioGroup from "../../stories/radio-group/RadioGroup";
import { formatCurrency } from "../../util";

const DEBOUNCE_TIME = 1;
function ViewCreditOptions() {
  const { t } = useT();
  const constants = useConstants();
  const { formatDateFromString } = useLocalizedDateFormatter();

  const applicationContext = useApplicationContext();
  const { data, isLoading: isLoadingOptions, getCreditProductOptionsMutation } = useGetCreditProductsOptions();
  const { isLoading, selectCreditProductMutation } = useSelectCreditProduct();

  const methodsMainForm = useForm<CreditOptionsInput>({
    defaultValues: {
      borrower_size: applicationContext.state.data?.application.calculator_data.borrower_size || undefined,
      sector: applicationContext.state.data?.borrower.sector || undefined,
      annual_revenue: applicationContext.state.data?.borrower.annual_revenue || undefined,
      amount_requested: applicationContext.state.data?.application.calculator_data.amount_requested || undefined,
    },
  });

  const {
    handleSubmit: handleSubmitMainForm,
    watch: watchMainForm,
    // formState: { touchedFields },
  } = methodsMainForm;

  const methodsLoanForm = useForm<RepaymentTermsInput>({
    defaultValues: {
      repayment_years: applicationContext.state.data?.application.calculator_data.repayment_years || undefined,
      repayment_months: applicationContext.state.data?.application.calculator_data.repayment_months || undefined,
      payment_start_date: applicationContext.state.data?.application.calculator_data.payment_start_date || undefined,
    },
    resolver: zodResolver(repaymentTermsSchema),
  });

  const [borrowerSizeValue, amountRequestedValue] = watchMainForm(["borrower_size", "amount_requested"]);

  const {
    handleSubmit: handleSubmitLoanForm,
    // formState: { touchedFields },
  } = methodsLoanForm;

  const debounceGetCreditProducts = useCallback(debounce(getCreditProductOptionsMutation, DEBOUNCE_TIME), [
    getCreditProductOptionsMutation,
    debounce,
  ]);

  useEffect(() => {
    if (!borrowerSizeValue || borrowerSizeValue === DEFAULT_BORROWER_SIZE || !amountRequestedValue) {
      return;
    }

    const payload: GetCreditProductsOptionsInput = {
      borrower_size: borrowerSizeValue,
      amount_requested: amountRequestedValue,
      uuid: applicationContext.state.data?.application.uuid,
    };

    debounceGetCreditProducts(payload);
  }, [
    borrowerSizeValue,
    amountRequestedValue,
    debounceGetCreditProducts,
    applicationContext.state.data?.application.uuid,
  ]);

  const onSelectCreditLine = async (option: ICreditProduct) => {
    const onSubmitHandlerMainForm: SubmitHandler<CreditOptionsInput> = (values) => {
      const formInput: SelectCreditProductInput = {
        credit_product_id: option.id,
        borrower_size: values.borrower_size,
        sector: values.sector,
        annual_revenue: values.annual_revenue || null,
        amount_requested: values.amount_requested,
        uuid: applicationContext.state.data?.application.uuid,
      };

      selectCreditProductMutation(formInput);
    };

    handleSubmitMainForm(onSubmitHandlerMainForm)();
  };

  const onSelectLoan = async (option: ICreditProduct) => {
    const partialFormInput: Partial<CreditOptionsInput> = {};

    const onSubmitHandlerMainForm: SubmitHandler<CreditOptionsInput> = (values) => {
      partialFormInput.borrower_size = values.borrower_size;
      partialFormInput.sector = values.sector;
      partialFormInput.annual_revenue = values.annual_revenue || 0;
      partialFormInput.amount_requested = values.amount_requested;
    };

    const onSubmitHandlerLoanForm: SubmitHandler<RepaymentTermsInput> = (values) => {
      if (partialFormInput.borrower_size && partialFormInput.sector && partialFormInput.amount_requested) {
        const formInput: SelectCreditProductInput = {
          credit_product_id: option.id,
          borrower_size: partialFormInput.borrower_size,
          sector: partialFormInput.sector,
          annual_revenue: partialFormInput.annual_revenue || 0,
          amount_requested: partialFormInput.amount_requested,
          repayment_years: values.repayment_years || 0,
          repayment_months: values.repayment_months || 0,
          payment_start_date: values.payment_start_date,
          uuid: applicationContext.state.data?.application.uuid,
        };

        selectCreditProductMutation(formInput);
      }
    };
    await handleSubmitMainForm(onSubmitHandlerMainForm)();
    await handleSubmitLoanForm(onSubmitHandlerLoanForm)();
  };

  const paramsForText = useMemo(() => {
    if (!applicationContext.state.data) return {};
    return {
      award_contract_value: Number(applicationContext.state.data.award.award_amount)
        ? `${applicationContext.state.data.award.award_currency} ${formatCurrency(
            applicationContext.state.data.award.award_amount,
            applicationContext.state.data.award.award_currency,
          )}`
        : "",
      award_contract_startdate: `${formatDateFromString(
        applicationContext.state.data.award.contractperiod_startdate,
      )}`,
    };
  }, [applicationContext.state.data, formatDateFromString]);

  return (
    <>
      <Title type="page" label={t("Financing Options")} className="mb-8" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:col-span-2 md:mr-10">
          <Text className="mb-1">
            {t(
              "Fill out the required information on the left and we'll show you the available financing options on the right.",
            )}
          </Text>
          <Text className="mb-8">{t("Financing can be through credit lines or through loans.")}</Text>
          <Title type="subsection" className="mb-2" label={t("What are the differences?")} />
          <ul>
            <li className="text-darkest">
              <Text className="mb-2">
                {t(
                  "In a loan, the entire amount of money approved is transferred to the borrower upfront. Interest must be paid from the moment that the money is delivered. The loan must be repaid within an agreed time.",
                )}
              </Text>
            </li>
            <li className="text-darkest">
              <Text className="mb-2">
                {t(
                  "In a line of credit, the borrower may choose how much of the approved amount to withdraw. Interest must be paid only on the withdrawn amount. The term of the line of credit can be extended. Interest rates on lines of credit may be higher.",
                )}
              </Text>
            </li>
          </ul>
        </div>
        <div className="my-6 md:my-0 md:ml-10">
          <NeedHelpComponent />
        </div>
      </div>
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:mr-10">
          <FormProvider {...methodsMainForm}>
            <Box
              component="form"
              noValidate
              autoComplete="off"
              sx={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <RadioGroup
                label={t("Number of employees")}
                name="borrower_size"
                options={(constants?.BorrowerSize || []).filter((o) => o.value !== DEFAULT_BORROWER_SIZE)}
              />
              <FormSelect
                className="w-3/5"
                label={t("Sector")}
                name="sector"
                options={constants?.BorrowerSector || []}
                placeholder={t("Sector")}
              />
              <FormInput
                className="w-3/5"
                label={t("Annual Revenue")}
                name="annual_revenue"
                big={false}
                type="currency"
                placeholder={applicationContext.state.data?.borrower.currency}
              />
              <FormInput
                className="w-3/5"
                label={t("Amount to finance")}
                name="amount_requested"
                big={false}
                type="currency"
                placeholder={`${
                  t("Award amount") || " " || applicationContext.state.data?.award.award_currency
                } ${formatCurrency(
                  applicationContext.state.data?.award.award_amount
                    ? applicationContext.state.data?.award.award_amount
                    : 0,
                  applicationContext.state.data?.award.award_currency,
                )}`}
              />
            </Box>
          </FormProvider>
        </div>
        <div className="grid grid-cols-1 md:col-span-2 gap-4 md:flex md:flex-col md:gap-0">
          <Title type="subsection" className="mb-2" label={t("Credit Lines")} />

          {borrowerSizeValue && amountRequestedValue && (
            <CreditLinesTable
              rows={data?.credit_lines || []}
              currency={applicationContext.state.data?.award.award_currency || import.meta.env.VITE_CURRENCY}
              selectOption={onSelectCreditLine}
              isLoading={isLoading || isLoadingOptions}
            />
          )}
          {(!borrowerSizeValue || borrowerSizeValue === DEFAULT_BORROWER_SIZE) && (
            <Text className="mb-0 text-sm">{t("Select a number of employees to evaluate available options")}</Text>
          )}
          {!amountRequestedValue && (
            <Text className="mb-0 text-sm">
              {t("Enter a value for amount to finance to evaluate available options")}
            </Text>
          )}
        </div>
      </div>

      {/* Loan Form */}

      <div className="mt-8 pb-10 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:mr-10">
          <Title type="subsection" className="mb-2" label={t("For loans")} />

          <FormProvider {...methodsLoanForm}>
            <Box
              component="form"
              noValidate
              autoComplete="off"
              sx={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Text className="mb-1">{t("Repayment terms")}</Text>
              <Box className="mb-2 w-3/5 flex flex-row items-start justify-start gap-2">
                <FormInput label="" name="repayment_years" placeholder={t("Year(s)")} type="number" />
                <FormInput label="" name="repayment_months" placeholder={t("Month(s)")} type="number" />
              </Box>
              <FormInput
                className="w-3/5"
                helperText={
                  applicationContext.state.data?.award.contractperiod_startdate
                    ? t(
                        "The latest the payment start date can is three months after your contract begins on {award_contract_startdate}.",
                        {
                          award_contract_startdate: paramsForText.award_contract_startdate,
                        },
                      )
                    : t("The latest the payment start date can be three months after your contract begins.")
                }
                big={false}
                label={t("Payment start date")}
                name="payment_start_date"
                type="date-picker"
              />
            </Box>
          </FormProvider>
        </div>
        <div className="grid grid-cols-1 mb-8 md:col-span-2 gap-4 md:flex md:flex-col md:gap-0">
          <Title type="subsection" className="mb-2" label={t("Loans")} />

          {borrowerSizeValue && amountRequestedValue && (
            <LoansTable
              rows={data?.loans || []}
              amountRequested={amountRequestedValue}
              currency={applicationContext.state.data?.award.award_currency || import.meta.env.VITE_CURRENCY}
              selectOption={onSelectLoan}
              isLoading={isLoading || isLoadingOptions}
            />
          )}
          {(!borrowerSizeValue || borrowerSizeValue === DEFAULT_BORROWER_SIZE) && (
            <Text className="mb-0 text-sm">{t("Select a number of employees to evaluate available options")}</Text>
          )}
          {!amountRequestedValue && (
            <Text className="mb-0 text-sm">
              {t("Enter a value for amount to finance to evaluate available options")}
            </Text>
          )}
        </div>
      </div>
    </>
  );
}

export default ViewCreditOptions;
