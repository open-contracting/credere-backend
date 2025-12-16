import { useTranslation as useT } from "react-i18next";
import Text from "src/stories/text/Text";
import Title from "src/stories/title/Title";

import useApplicationContext from "../../hooks/useApplicationContext";

function ExternalOnboardingCompleted() {
  const { t } = useT();
  const applicationContext = useApplicationContext();

  return (
    <>
      <Title type="page" label={t("External Onboarding Completed")} className="mb-8" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:col-span-2 md:mr-10">
          <Text className="mb-8">
            {t("Thank you for confirming that you have already started the onboarding process with {{fi_name}}. ", {
              fi_name: applicationContext.state.data?.lender.name,
            })}
          </Text>
          <div>
            <Text className="mb-8">
              {t(
                "Pending some checks by {fi_name}, we will be in touch via email to let you know if the application has been approved and tell you the next steps for funds to be disbursed to you.",
                {
                  fi_name: applicationContext.state.data?.lender.name,
                },
              )}
            </Text>
          </div>
          <div>
            <Text className="mb-8">
              {t(
                "In the meantime if you have any questions, you can reach out to member of the Open Contracting Partnership team at: credere@open-contracting.org.",
              )}
            </Text>
            <Text className="mb-8">{t("Thank you for counting with us")}</Text>
            <Text className="mb-8">{t("Credere team")}</Text>
          </div>
        </div>
      </div>
    </>
  );
}

export default ExternalOnboardingCompleted;
