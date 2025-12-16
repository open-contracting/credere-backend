import { useQuery } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { getStatisticsOCP } from "../api/private";
import { QUERY_KEYS } from "../constants";
import type { StatisticsFI, StatisticsParmsInput } from "../schemas/statitics";
import { handleRequestError } from "../util/validation";

type IUseGetStatisticsOCP = {
  data?: StatisticsFI;
  isLoading: boolean;
};

export default function useGetStatisticsOCP(
  customRange: string,
  initialDate: string | null,
  finalDate: string | null,
  lenderId: number | null,
): IUseGetStatisticsOCP {
  const { t } = useT();
  const { enqueueSnackbar } = useSnackbar();

  const { data, isLoading } = useQuery<StatisticsFI>({
    queryKey: [QUERY_KEYS.statistics_ocp, `${customRange}-${initialDate}-${finalDate}-${lenderId}`],
    queryFn: () => {
      const params: StatisticsParmsInput = {
        custom_range: customRange,
      };
      if (initialDate !== null) {
        params.initial_date = initialDate;
      }
      if (finalDate !== null) {
        params.final_date = finalDate;
      }
      if (lenderId !== null) {
        params.lender_id = lenderId;
      }
      return getStatisticsOCP(params);
    },
    onSuccess: (dataResult) => dataResult,
    onError: (error) => {
      handleRequestError(error, enqueueSnackbar, t("Error getting statistics opt-in . {{error}}", { error }));
    },
  });

  return { data, isLoading };
}
