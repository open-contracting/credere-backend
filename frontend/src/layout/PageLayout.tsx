import { Container } from "@mui/material";
import type { PropsWithChildren } from "react";

import { USER_TYPES } from "../constants";
import useSignOut from "../hooks/useLogout";
import useUser from "../hooks/useUser";
import BaseLayout from "./BaseLayout";

export default function PageLayout({ children }: PropsWithChildren) {
  const user = useUser();
  const signOut = useSignOut();

  const handleLogout = () => {
    signOut();
  };

  return (
    <BaseLayout auth={!!user} logout={handleLogout}>
      {user?.type === USER_TYPES.OCP && (
        <Container
          maxWidth={false}
          className="lg:pt-14 lg:px-20 md:pt-8 md:px-12 sm:pt-7 sm:px-10 pt-6 px-6 pb-12 mx-0"
        >
          {children}
        </Container>
      )}
      {user?.type === USER_TYPES.FI && (
        <Container
          maxWidth={false}
          className="lg:pt-16 lg:px-20 md:pt-10 md:px-12 sm:pt-9 sm:px-10 pt-8 px-6 pb-12 mx-0"
        >
          {children}
        </Container>
      )}
    </BaseLayout>
  );
}
