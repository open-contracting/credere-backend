import { zodResolver } from "@hookform/resolvers/zod";
import type { Meta, StoryObj } from "@storybook/react";
import { FormProvider, useForm } from "react-hook-form";

import { type LoginInput, loginSchema } from "../../schemas/auth";
import RadioGroup, { type RadioGroupProps } from "./RadioGroup";

// More on how to set up stories at: https://storybook.js.org/docs/react/writing-stories/introduction
const meta = {
  title: "Example/RadioGroup",
  component: RadioGroup,
  tags: ["autodocs"],
  argTypes: {},
} satisfies Meta<typeof RadioGroup>;

export default meta;
type Story = StoryObj<typeof meta>;

function ComponentWithHooks(args: RadioGroupProps) {
  const methods = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <FormProvider {...methods}>
      <RadioGroup {...args} />
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
