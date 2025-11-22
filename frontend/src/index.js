import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";
import * as serviceWorkerRegistration from "./serviceWorkerRegistration";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register service worker for PWA
serviceWorkerRegistration.register({
  onUpdate: (registration) => {
    // Show update notification
    if (window.confirm('Eine neue Version ist verfügbar. Seite neu laden?')) {
      registration.waiting?.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  },
  onSuccess: () => {
    console.log('PWA installiert. Funktioniert offline!');
  }
});
