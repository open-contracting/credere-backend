import { Container } from "@mui/material";
import type { PropsWithChildren } from "react";

import BaseLayout from "./BaseLayout";

export default function PublicPageLayout({ children }: PropsWithChildren) {
  return (
    <BaseLayout>
      <Container maxWidth={false} className="lg:pt-16 lg:px-20 md:pt-10 md:px-12 sm:pt-9 sm:px-10 pt-8 px-6 mx-0">
        {children}
      </Container>
    </BaseLayout>
  );
}
