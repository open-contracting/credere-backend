import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";
import { downloadBlob } from "src/util/index";

import { downloadApplicants } from "../api/private";
import useLangContext from "./useLangContext";

type IUseDownloadDocument = {
  downloadedDocument?: Blob | null;
  downloadDocument: () => void;
  isDownloading: boolean;
};

export default function useDownloadApplicants(): IUseDownloadDocument {
  const { t } = useT();
  const langContext = useLangContext();
  const { enqueueSnackbar } = useSnackbar();

  const {
    data: downloadedDocument,
    refetch: downloadDocument,
    fetchStatus,
  } = useQuery<Blob>({
    enabled: false,
    queryFn: () => downloadApplicants(langContext.state.selected.split("_")[0]),
    onSuccess: (data) => {
      downloadBlob(data, "export.csv");
      return data;
    },
    onError: (error) => {
      if (axios.isAxiosError(error) && error.response) {
        if (error.response.data?.detail) {
          enqueueSnackbar(t("Error: {{error}}", { error: error.response.data.detail }), {
            variant: "error",
          });
        }
      } else {
        enqueueSnackbar(t("Error downloading applicants. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { downloadedDocument, downloadDocument, isDownloading: fetchStatus !== "idle" };
}
