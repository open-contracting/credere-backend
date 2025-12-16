import { zodResolver } from "@hookform/resolvers/zod";
import type { Meta, StoryObj } from "@storybook/react";
import { FormProvider, useForm } from "react-hook-form";

import { type LoginInput, loginSchema } from "../../schemas/auth";
import FormSelect, { type FormSelectProps } from "./FormSelect";

// More on how to set up stories at: https://storybook.js.org/docs/react/writing-stories/introduction
const meta = {
  title: "Example/FormSelect",
  component: FormSelect,
  tags: ["autodocs"],
  argTypes: {},
} satisfies Meta<typeof FormSelect>;

export default meta;
type Story = StoryObj<typeof meta>;

function ComponentWithHooks(args: FormSelectProps) {
  const methods = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <FormProvider {...methods}>
      <FormSelect {...args} />
    </FormProvider>
  );
}

// More on writing stories with args: https://storybook.js.org/docs/react/writing-stories/args
export const DefaultStringSelect: Story = {
  args: {
    name: "select",
    label: "Select Option",
    options: ["Option 1", "Option 2"],
  },
  render: (args) => <ComponentWithHooks {...args} />,
};

export const SelectWithPlaceholder: Story = {
  args: {
    name: "select",
    label: "Select With Placeholder",
    placeholder: "Select an option",
    options: ["Option 1", "Option 2"],
  },
  render: (args) => <ComponentWithHooks {...args} />,
};
