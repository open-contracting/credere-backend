import type { Preview } from "@storybook/react";

import "../src/index.css";
import MuiTheme from "../src/mui-theme";

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
  },
};

export const withMuiTheme = (Story) => (
  <div id="root-app">
    <MuiTheme>
      <Story />
    </MuiTheme>
  </div>
);

export const decorators = [withMuiTheme];

export default preview;
