import { useCallback } from "react";

import { formatLocalizedDate, formatLocalizedDateFromString } from "../util";
import useLangContext from "./useLangContext";

const useLocalizedDateFormatter = () => {
  const langContext = useLangContext();

  const formatDate = useCallback(
    (date: Date) => formatLocalizedDate(langContext.state.selected.replace("_", "-"), date),
    [langContext.state.selected],
  );

  const formatDateFromString = useCallback(
    (date: string | null | undefined) =>
      formatLocalizedDateFromString(langContext.state.selected.replace("_", "-"), date),
    [langContext.state.selected],
  );

  return {
    formatDate,
    formatDateFromString,
  };
};

export default useLocalizedDateFormatter;
