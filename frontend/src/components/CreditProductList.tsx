import { Link } from "react-router-dom";
import type { ICreditProduct } from "../schemas/application";
import LinkButton from "../stories/link-button/LinkButton";
import { RenderSize, renderCreditProductType } from "../util";
import { t } from "../util/i18n";
import { DataTable, type HeadCell } from "./DataTable";

const headCells: HeadCell<ICreditProduct>[] = [
  {
    id: "borrower_size",
    disablePadding: false,
    label: t("Borrower size"),
    sortable: false,
    render: (row: ICreditProduct) => RenderSize(row.borrower_size),
  },
  {
    id: "lower_limit",
    type: "currency",
    disablePadding: false,
    label: t("Lower"),
    sortable: false,
  },
  {
    id: "upper_limit",
    type: "currency",
    disablePadding: false,
    label: t("Upper"),
    sortable: false,
  },

  {
    id: "interest_rate",
    disablePadding: false,
    label: t("Interest rate"),
    sortable: false,
  },
  {
    id: "type",
    disablePadding: false,
    label: t("Type"),
    sortable: false,
    render: (row: ICreditProduct) => renderCreditProductType(row.type),
  },
];

const CreditProductDataTable = DataTable<ICreditProduct>;

const actions = (row: ICreditProduct) => (
  <LinkButton
    className="p-1 justify-start"
    component={Link}
    to={`/settings/lender/${row.lender_id}/credit-product/${row.id}/edit`}
    label={t("Edit")}
    size="small"
    noIcon
  />
);

export interface CreditProductListProps {
  rows: ICreditProduct[];
}

export function CreditProductList({ rows }: CreditProductListProps) {
  return <CreditProductDataTable rows={rows} useEmptyRows={false} headCells={headCells} actions={actions} />;
}

export default CreditProductList;
