import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { setSimpleMode, getSimpleMode } from "./auth/simpleMode";
import "./index.css";
import { installFormErrors } from "./lib/formErrors";

setSimpleMode(getSimpleMode()); // apply the saved text size before the first paint
installFormErrors();             // Spanish form messages instead of the browser's (lib/formErrors.ts)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
