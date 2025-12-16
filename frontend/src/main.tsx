import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";
import "dayjs/locale/en";
import "dayjs/locale/es";
import React from "react";
import ReactDOM from "react-dom/client";

import { getLang } from "./api/localstore";
import i18n from "./i18n";
import "./index.css";
import { AppRouter } from "./routes/AppRouter";

dayjs.locale(import.meta.env.VITE_DEFAULT_LANG);

const renderApp = () => {
  const rootElement = document.getElementById("root-app");
  ReactDOM.createRoot(rootElement as HTMLElement).render(
    <React.StrictMode>
      <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale={import.meta.env.VITE_DEFAULT_LANG || "es"}>
        <AppRouter />
      </LocalizationProvider>
    </React.StrictMode>,
  );
};

i18n.changeLanguage(`${getLang() || import.meta.env.VITE_DEFAULT_LANG || "es"}`).then(
  () => {
    renderApp();
  },
  (error) => {
    console.error(error);
    renderApp();
  },
);
