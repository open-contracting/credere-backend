import { Box } from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation as useT } from "react-i18next";
import { useNavigate } from "react-router-dom";
import NeedHelpComponent from "src/components/NeedHelpComponent";
import FAQ_QUESTIONS from "src/constants/faq-questions";
import FAQPageSection from "src/stories/faq/FAQPageSection";
import LinkButton from "src/stories/link-button/LinkButton";
import Title from "src/stories/title/Title";

import Button from "../../stories/button/Button";

function FrequentlyAskedQuestionsPage() {
  const { t } = useT();
  const navigate = useNavigate();

  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [allExpanded, setAllExpanded] = useState<boolean>(false);

  useEffect(() => {
    Object.keys(open).some((key) => {
      if (open[key] === false) {
        setAllExpanded(false);
        return true;
      }
      setAllExpanded(true);
      return false;
    });
  }, [open]);

  useEffect(() => {
    Object.keys(FAQ_QUESTIONS).forEach((key) => {
      setOpen((prev) => ({ ...prev, [key]: false }));
    });
  }, []);

  const handleToggle = (key: string) => {
    setOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleExpandAll = () => {
    Object.keys(FAQ_QUESTIONS).forEach((key) => {
      setOpen((prev) => ({ ...prev, [key]: true }));
    });
  };

  const handleCollapseAll = () => {
    Object.keys(FAQ_QUESTIONS).forEach((key) => {
      setOpen((prev) => ({ ...prev, [key]: false }));
    });
  };

  return (
    <>
      <Title type="page" label={t("Frequently Asked Questions")} className="mb-8" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="col-span-1 md:col-span-2 md:mr-10">
          <Box className="flex items-end justify-end">
            {!allExpanded && (
              <LinkButton
                onClick={handleExpandAll}
                className="mb-0 px-0 self-end"
                iconClassName="rotate-90"
                label={t("Expand all")}
              />
            )}
            {allExpanded && (
              <LinkButton
                onClick={handleCollapseAll}
                className="mb-0 px-0 self-end"
                iconClassName="-rotate-90"
                label={t("Collapse all")}
              />
            )}
          </Box>
          {Object.keys(FAQ_QUESTIONS).map((key: string) => (
            <FAQPageSection
              key={key}
              open={open[key]}
              handleToggle={() => handleToggle(key)}
              title={t(FAQ_QUESTIONS[key].question)}
            >
              {t(FAQ_QUESTIONS[key].answer)}
            </FAQPageSection>
          ))}
        </div>
        <div className="my-6 md:my-0 md:ml-10">
          <NeedHelpComponent />
        </div>
      </div>
      <Button className="my-8" primary={false} label={t("Go back")} onClick={() => navigate(-1)} />
    </>
  );
}

export default FrequentlyAskedQuestionsPage;
