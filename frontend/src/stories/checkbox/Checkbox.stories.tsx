import { zodResolver } from "@hookform/resolvers/zod";
import type { Meta, StoryObj } from "@storybook/react";
import { FormProvider, useForm } from "react-hook-form";

import { type LoginInput, loginSchema } from "../../schemas/auth";
import Checkbox, { type CheckboxProps } from "./Checkbox";

// More on how to set up stories at: https://storybook.js.org/docs/react/writing-stories/introduction
const meta = {
  title: "Example/Checkbox",
  component: Checkbox,
  tags: ["autodocs"],
  argTypes: {},
} satisfies Meta<typeof Checkbox>;

export default meta;
type Story = StoryObj<typeof meta>;

function ComponentWithHooks(args: CheckboxProps) {
  const methods = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <FormProvider {...methods}>
      <Checkbox {...args} />
    </FormProvider>
  );
}

// More on writing stories with args: https://storybook.js.org/docs/react/writing-stories/args
export const DefaultCheckbox: Story = {
  args: {
    name: "acceptTerms",
    label: "I agree for my details to be passed onto the banking partner.",
  },
  render: (args) => <ComponentWithHooks {...args} />,
};
