import { StrictMode } from "react";
import { MotionConfig } from "framer-motion";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { I18nProvider } from "./i18n/I18nContext.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    {/* One motion personality app-wide; "user" honors prefers-reduced-motion (drops transforms, keeps fades) */}
    <MotionConfig reducedMotion="user" transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}>
      <I18nProvider>
        <App />
      </I18nProvider>
    </MotionConfig>
  </StrictMode>,
);
