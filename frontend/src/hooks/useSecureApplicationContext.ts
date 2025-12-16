import React from "react";

import { ApplicationContext } from "../providers/SecureApplicationContextProvider";

const useApplicationContext = () => {
  const context = React.useContext(ApplicationContext);

  if (context) {
    return context;
  }

  throw new Error("useApplicationContext must be used within a SecureApplicationContextProvider");
};

export default useApplicationContext;
