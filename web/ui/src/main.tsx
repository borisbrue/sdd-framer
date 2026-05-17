import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { NotificationProvider } from "./components/NotificationContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <NotificationProvider>
      <App />
    </NotificationProvider>
  </StrictMode>
);
