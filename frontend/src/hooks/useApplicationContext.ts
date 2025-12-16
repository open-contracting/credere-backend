import React from "react";

import { ApplicationContext } from "../providers/ApplicationContextProvider";

const useApplicationContext = () => {
  const context = React.useContext(ApplicationContext);

  if (context) {
    return context;
  }

  throw new Error("useApplicationContext must be used within a ApplicationContextProvider");
};

export default useApplicationContext;
