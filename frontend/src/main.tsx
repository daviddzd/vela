import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { setSimpleMode, getSimpleMode } from "./auth/simpleMode";
import "./index.css";

setSimpleMode(getSimpleMode()); // apply the saved text size before the first paint

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
