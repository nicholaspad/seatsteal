import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import ProtectedRoute from "../ProtectedRoute";
import {
  customRender,
  renderAuthenticated,
  renderAnonymous,
} from "@/test/utils";

describe("ProtectedRoute", () => {
  it("shows loading state when auth is loading", () => {
    customRender(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
      { loading: true },
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when user is authenticated", () => {
    renderAuthenticated(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("does not render children when user is not authenticated", () => {
    renderAnonymous(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    );

    // Redirect component renders, content should not be visible
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders nested content when authenticated", () => {
    renderAuthenticated(
      <ProtectedRoute>
        <div>
          <h1>Dashboard</h1>
          <p>Welcome back!</p>
        </div>
      </ProtectedRoute>,
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Welcome back!")).toBeInTheDocument();
  });

  it("renders children immediately if user already authenticated on mount", () => {
    // Render with auth already complete (no loading states)
    renderAuthenticated(
      <ProtectedRoute>
        <div>Immediate Content</div>
      </ProtectedRoute>,
      { loading: false, profileLoading: false },
    );

    // Content should be rendered immediately
    expect(screen.getByText("Immediate Content")).toBeInTheDocument();
    expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
  });
});
