import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(js|jsx|ts|tsx)"],
  addons: ["@storybook/addon-links", "@storybook/addon-essentials", "@storybook/addon-interactions"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  typescript: {
    reactDocgen: "react-docgen-typescript",
    reactDocgenTypescriptOptions: {
      // For Storybook stories with enum types (string unions).
      shouldExtractLiteralValuesFromEnum: true,
      // For Storybook stories that import props from Material UI.
      propFilter: (prop) => {
        if (prop.parent) {
          return !/node_modules\/(?!@mui)/.test(prop.parent.fileName);
        }
        return true;
      },
    },
  },
};
export default config;
