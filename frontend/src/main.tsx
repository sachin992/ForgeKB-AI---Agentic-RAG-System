import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router";
import { Providers } from "./providers";
import { useAppStore } from "../lib/store";
import "antd/dist/reset.css";
import "./styles.css";

useAppStore.getState().hydrate();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Providers>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </Providers>
  </React.StrictMode>
);
