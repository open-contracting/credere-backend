import { zodResolver } from "@hookform/resolvers/zod";
import { Box } from "@mui/material";
import { FormProvider, type SubmitHandler, useForm } from "react-hook-form";
import { useTranslation as useT } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import useConstants from "src/hooks/useConstants";
import Text from "src/stories/text/Text";
import Title from "src/stories/title/Title";

import CreditProductConfirmation from "../../components/CreditProductConfirmation";
import FAQComponent from "../../components/FAQComponent";
import NeedHelpComponent from "../../components/NeedHelpComponent";
import useApplicationContext from "../../hooks/useApplicationContext";
import useSubmitApplication from "../../hooks/useSubmitApplication";
import { type SubmitInput, submitSchema } from "../../schemas/application";
import Button from "../../stories/button/Button";
import Checkbox from "../../stories/checkbox/Checkbox";

function ConfirmSubmission() {
  const { t } = useT();
  const constants = useConstants();
  const navigate = useNavigate();
  const { isLoading, submitApplicationMutation } = useSubmitApplication();
  const applicationContext = useApplicationContext();

  const onSubmitHandler: SubmitHandler<SubmitInput> = () => {
    submitApplicationMutation({ uuid: applicationContext.state.data?.application.uuid });
  };

  const methods = useForm<SubmitInput>({
    resolver: zodResolver(submitSchema),
  });

  const onBackHandler = () => {
    navigate("../documents");
  };

  const { handleSubmit } = methods;

  return (
    <>
      <Title type="page" label={t("Confirm Submission")} className="mb-10" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:col-span-2 md:mr-10">
          <Text className="mb-2">
            {t("Please, confirm the data you will submit to Credere and {{fi_name}}.", {
              fi_name: applicationContext.state.data?.lender.name,
            })}
          </Text>

          <Text className="mb-8">{t("You have selected the following financing option:")}</Text>

          {applicationContext.state.data?.creditProduct && applicationContext.state.data?.application && (
            <CreditProductConfirmation
              creditProduct={{
                ...applicationContext.state.data?.creditProduct,
                lender: applicationContext.state.data?.lender,
              }}
              application={applicationContext.state.data?.application}
            />
          )}

          <Title
            type="subsection"
            className="mb-2 mt-8"
            label={t("Documents to share with  {{fi_name}}.", {
              fi_name: applicationContext.state.data?.lender.name,
            })}
          />
          <ul>
            {applicationContext.state.data?.creditProduct.required_document_types &&
              Object.keys(applicationContext.state.data?.creditProduct.required_document_types)
                .filter(
                  (documentTypeKey: string) =>
                    applicationContext.state.data?.creditProduct.required_document_types[documentTypeKey],
                )
                .map((documentTypeKey: string) => (
                  <li key={documentTypeKey} className="text-darkest">
                    <Text className="mb-2">
                      {(constants?.BorrowerDocumentType || []).filter((d) => d.value === documentTypeKey)[0]?.label ||
                        ""}
                    </Text>
                  </li>
                ))}
          </ul>
          <FormProvider {...methods}>
            <Box
              component="form"
              onSubmit={handleSubmit(onSubmitHandler)}
              noValidate
              autoComplete="off"
              sx={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Checkbox
                name="agree_topass_info_to_banking_partner"
                defaultValue={false}
                label={t(
                  "I agree for these documents, the information entered in my application and the information about my award to be passed to {fi_name}, so that they can offer me credit alternatives in accordance with the OCP Data Processing Policy. Once my information is shared, it will be treated in accordance with the data processing policy of each financial institution.",
                  {
                    fi_name: applicationContext.state.data?.lender.name,
                  },
                )}
              />
              <Box>
                <Text className="inline-block">{t("You can read")} </Text>

                <Link
                  className="text-darkest"
                  to="https://www.open-contracting.org/es/about/our-privacy-policy/"
                  target="_blank"
                >
                  <Text className="inline-block underline ml-1 mb-X">
                    {t("the OCP Data Processing Policy in this link")}
                  </Text>
                </Link>
              </Box>

              <div className="mt-6 md:mb-8 grid grid-cols-1 gap-4 md:flex md:gap-0">
                <div>
                  <Button className="md:mr-4" label={t("Back")} onClick={onBackHandler} disabled={isLoading} />
                </div>
                <div>
                  <Button label={t("Submit Application")} type="submit" disabled={isLoading} />
                </div>
              </div>
            </Box>
          </FormProvider>
        </div>
        <div className="my-6 md:my-0 md:ml-10">
          <NeedHelpComponent />
          <FAQComponent className="my-8" />
        </div>
      </div>
    </>
  );
}

export default ConfirmSubmission;
