import { Box, Collapse } from "@mui/material";
import { useState } from "react";

import ArrowUp from "../assets/icons/arrow-up.svg";
import Text from "../stories/text/Text";

interface DataWithDetailProps {
  name: string;
  detail: string;
}

export function DataWithDetail({ name, detail }: DataWithDetailProps) {
  const [open, setOpen] = useState(false);

  const handleToggle = () => {
    setOpen(!open);
  };

  return (
    <Box className="py-2 flex flex-col">
      <Box className="flex flex-col align-top" onClick={handleToggle}>
        <Box className="flex flex-row">
          <Text fontVariant className="mb-0 mt-1 text-sm">
            {name}
          </Text>
          <img
            className={`self-start ${open ? "rotate-180" : ""}`}
            src={ArrowUp}
            alt={`arrow-${open ? "up" : "down"}`}
          />
        </Box>
        <Collapse in={open}>
          <Text fontVariant className="ml-3 mt-4 text-sm">
            {detail}
          </Text>
        </Collapse>
      </Box>
    </Box>
  );
}

export default DataWithDetail;
