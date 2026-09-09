import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { ApiError } from "./api";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // A 4xx is a deliberate answer (no permission, not found) - retrying it
      // only delays the message the user needs to see.
      retry: (attempt, error) =>
        !(error instanceof ApiError && error.status >= 400 && error.status < 500) &&
        attempt < 1,
    },
  },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
