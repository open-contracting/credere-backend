import React from "react";

import { LangContext } from "../providers/LangContextProvider";

const useLangContext = () => {
  const context = React.useContext(LangContext);

  if (context) {
    return context;
  }

  throw new Error("useLangContext must be used within a LangContextProvider");
};

export default useLangContext;
