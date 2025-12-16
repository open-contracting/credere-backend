import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { downloadApplicationFn } from "../api/private";
import { QUERY_KEYS } from "../constants";
import useLangContext from "./useLangContext";

type IUseDownloadApplication = {
  downloadedApplication?: Blob;
  isLoading: boolean;
};

export default function useDownloadApplication(id?: number): IUseDownloadApplication {
  const { t } = useT();
  const langContext = useLangContext();
  const { enqueueSnackbar } = useSnackbar();
  const lang = langContext.state.selected.split("_")[0];

  const { data: downloadedApplication, isLoading } = useQuery<Blob>({
    queryKey: [QUERY_KEYS.downloadApplication, `${id}-${lang}`],
    queryFn: () => downloadApplicationFn(Number(id), lang),
    enabled: Boolean(id),
    onSuccess: (data) => data,
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error downloading Application. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { downloadedApplication, isLoading: id ? isLoading : false };
}
