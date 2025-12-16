import { useRouteError } from "react-router-dom";

import PageLayout from "../layout/PageLayout";
import Text from "../stories/text/Text";
import Title from "../stories/title/Title";

export default function RouterErrorPage() {
  const error = useRouteError();

  return (
    <PageLayout>
      <Title type="page" label="Ops" />
      <Text>{(error as Error)?.message || (error as { statusText?: string })?.statusText}</Text>
    </PageLayout>
  );
}
