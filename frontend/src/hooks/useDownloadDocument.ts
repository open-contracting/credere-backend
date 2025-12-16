import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useSnackbar } from "notistack";
import { useTranslation as useT } from "react-i18next";

import { downloadDocumentFn } from "../api/private";
import { QUERY_KEYS } from "../constants";

type IUseDownloadDocument = {
  downloadedDocument?: Blob;
  isLoading: boolean;
};

export default function useDownloadDocument(id?: number, name?: string): IUseDownloadDocument {
  const { t } = useT();

  const { enqueueSnackbar } = useSnackbar();

  const { data: downloadedDocument, isLoading } = useQuery<Blob>({
    queryKey: [QUERY_KEYS.downloadDocument, `${id}-${name}`],
    queryFn: () => downloadDocumentFn(Number(id)),
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
        enqueueSnackbar(t("Error downloading document. {{error}}", { error }), {
          variant: "error",
        });
      }
    },
  });

  return { downloadedDocument, isLoading: id ? isLoading : false };
}
