import { zodResolver } from "@hookform/resolvers/zod";
import type { Meta, StoryObj } from "@storybook/react";
import { FormProvider, useForm } from "react-hook-form";

import { type LoginInput, loginSchema } from "../../schemas/auth";
import Switch, { type SwitchProps } from "./Switch";

// More on how to set up stories at: https://storybook.js.org/docs/react/writing-stories/introduction
const meta = {
  title: "Example/Switch",
  component: Switch,
  tags: ["autodocs"],
  argTypes: {},
} satisfies Meta<typeof Switch>;

export default meta;
type Story = StoryObj<typeof meta>;

function ComponentWithHooks(args: SwitchProps) {
  const methods = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <FormProvider {...methods}>
      <Switch {...args} />
    </FormProvider>
  );
}

// More on writing stories with args: https://storybook.js.org/docs/react/writing-stories/args
export const DefaultSwitch: Story = {
  args: {
    name: "dataAvailable",
    label: "Data Available.",
  },
  render: (args) => <ComponentWithHooks {...args} />,
};
