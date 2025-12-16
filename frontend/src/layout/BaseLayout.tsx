import { Container } from "@mui/material";
import type { PropsWithChildren } from "react";

import ScrollToTop from "../components/ScrollToTop";
import { AppBar, type AppBarProps } from "./AppBar";

export default function BaseLayout({ children, auth, logout }: AppBarProps & PropsWithChildren) {
  return (
    <Container
      maxWidth={false}
      className="bg-background p-0 m-0"
      sx={{
        minHeight: "100vh",
      }}
    >
      <ScrollToTop />
      <AppBar auth={auth} logout={logout} />
      {children}
    </Container>
  );
}
