import React from "react";

import { StateContext } from "../providers/StateContextProvider";

const useStateContext = () => {
  const context = React.useContext(StateContext);

  if (context) {
    return context;
  }

  throw new Error("useStateContext must be used within a StateContextProvider");
};

export default useStateContext;
