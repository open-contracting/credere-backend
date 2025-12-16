import { useMemo } from "react";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ChartData } from "../schemas/statitics";
import { t } from "../util/i18n";

interface ChartsProps {
  data: ChartData[];
}

interface MultipleChartsProps {
  series: ChartData[][];
  dataKeys: string[];
  seriesNames: string[];
  labelMapper?: (label: any) => string;
}

const COLORS_TO_FILL = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#82ca9d",
  "#8884d8",
  "var(--color-dark-green)",
  "var(--color-red)",
  "var(--color-yellow)",
];

const labelFormatterBase = (_label: any, payload: any, labelMapper?: (label: any) => string) => {
  if (labelMapper) {
    return t(labelMapper(payload[0]?.payload.name));
  }
  return t(payload[0]?.payload.name);
};

export function ChartPie({ data }: ChartsProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart width={400} height={400}>
        <Pie data={data} cx="50%" cy="50%" labelLine={false} outerRadius={80} fill="#8884d8" dataKey="value">
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS_TO_FILL[index % COLORS_TO_FILL.length]} />
          ))}
        </Pie>
        <Tooltip separator=" " labelFormatter={labelFormatterBase} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ChartBar({ data }: ChartsProps) {
  return (
    <ResponsiveContainer width="100%" height="95%">
      <BarChart width={140} data={data}>
        <Tooltip
          labelFormatter={labelFormatterBase}
          formatter={(value: any) => [value, ""]}
          separator=""
          cursor={{ stroke: "var(--color-field-border)", strokeWidth: 0.5, fill: "transparent" }}
        />
        <Bar dataKey="value" fill="var(--color-dark-green)" minPointSize={1} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ChartMultipleBar({
  series,
  dataKeys,
  seriesNames,
  labelMapper = (label: any) => label,
}: MultipleChartsProps) {
  const data = useMemo(() => {
    const result: any = [];
    dataKeys.forEach((key) => {
      const dataItem: any = { name: key };
      series.forEach((serie, index) => {
        dataItem[`series${index + 1}`] = serie.find((item) => item.name === key)?.value || 0;
      });
      result.push({ ...dataItem });
    });

    return result;
  }, [series, dataKeys]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart width={140} data={data}>
        {series.map((_serie, index) => (
          <Bar
            key={index}
            dataKey={`series${index + 1}`}
            name={t(seriesNames[index])}
            fill={COLORS_TO_FILL[index]}
            minPointSize={1}
          />
        ))}
        <Tooltip
          separator=" "
          labelFormatter={(_label: any, payload: any) => labelFormatterBase(_label, payload, labelMapper)}
          cursor={{ stroke: "var(--color-field-border)", strokeWidth: 0.5, fill: "transparent" }}
        />
        <Legend />
      </BarChart>
    </ResponsiveContainer>
  );
}
