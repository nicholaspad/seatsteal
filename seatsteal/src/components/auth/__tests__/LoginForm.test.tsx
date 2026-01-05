import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginForm } from "../LoginForm";

// Mock the supabase module
const mockSignInWithMagicLink = vi.fn();
const mockSignInWithGoogle = vi.fn();

vi.mock("@/lib/supabase", () => ({
  signInWithMagicLink: (...args: unknown[]) => mockSignInWithMagicLink(...args),
  signInWithGoogle: () => mockSignInWithGoogle(),
}));

vi.mock("@/lib/api", () => ({
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("LoginForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSignInWithMagicLink.mockResolvedValue({ error: null });
    mockSignInWithGoogle.mockResolvedValue({ error: null });
  });

  describe("Google Sign-In", () => {
    it("renders the Google sign-in button", () => {
      render(<LoginForm />);

      expect(
        screen.getByRole("button", { name: /continue with google/i }),
      ).toBeInTheDocument();
    });

    it("calls signInWithGoogle when Google button is clicked", async () => {
      render(<LoginForm />);

      const googleButton = screen.getByRole("button", {
        name: /continue with google/i,
      });
      await userEvent.click(googleButton);

      expect(mockSignInWithGoogle).toHaveBeenCalledTimes(1);
    });

    it("shows loading state while Google sign-in is in progress", async () => {
      // Make the sign-in hang
      mockSignInWithGoogle.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(<LoginForm />);

      const googleButton = screen.getByRole("button", {
        name: /continue with google/i,
      });
      fireEvent.click(googleButton);

      await waitFor(() => {
        expect(screen.getByText(/signing in\.\.\./i)).toBeInTheDocument();
      });
    });

    it("shows error when Google sign-in fails", async () => {
      mockSignInWithGoogle.mockResolvedValue({
        error: { message: "OAuth error" },
      });

      render(<LoginForm />);

      const googleButton = screen.getByRole("button", {
        name: /continue with google/i,
      });
      await userEvent.click(googleButton);

      await waitFor(() => {
        expect(
          screen.getByText(/failed to sign in with google/i),
        ).toBeInTheDocument();
      });
    });

    it("disables Google button while email login is in progress", async () => {
      // Make the magic link hang
      mockSignInWithMagicLink.mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );

      render(<LoginForm />);

      const emailInput = screen.getByPlaceholderText(/john@example\.com/i);
      await userEvent.type(emailInput, "test@example.com");

      const loginButton = screen.getByRole("button", { name: /^login$/i });
      fireEvent.click(loginButton);

      await waitFor(() => {
        const googleButton = screen.getByRole("button", {
          name: /continue with google/i,
        });
        expect(googleButton).toBeDisabled();
      });
    });
  });

  describe("Divider", () => {
    it("renders the divider with 'Or continue with email' text", () => {
      render(<LoginForm />);

      expect(screen.getByText(/or continue with email/i)).toBeInTheDocument();
    });
  });

  describe("Email Login", () => {
    it("renders email input field", () => {
      render(<LoginForm />);

      expect(
        screen.getByPlaceholderText(/john@example\.com/i),
      ).toBeInTheDocument();
    });

    it("renders login button", () => {
      render(<LoginForm />);

      expect(
        screen.getByRole("button", { name: /^login$/i }),
      ).toBeInTheDocument();
    });

    it("calls signInWithMagicLink when form is submitted with valid email", async () => {
      render(<LoginForm />);

      const emailInput = screen.getByPlaceholderText(/john@example\.com/i);
      await userEvent.type(emailInput, "test@example.com");

      const loginButton = screen.getByRole("button", { name: /^login$/i });
      await userEvent.click(loginButton);

      expect(mockSignInWithMagicLink).toHaveBeenCalledWith("test@example.com");
    });

    it("shows success message after successful magic link send", async () => {
      render(<LoginForm />);

      const emailInput = screen.getByPlaceholderText(/john@example\.com/i);
      await userEvent.type(emailInput, "test@example.com");

      const loginButton = screen.getByRole("button", { name: /^login$/i });
      await userEvent.click(loginButton);

      await waitFor(() => {
        expect(screen.getByText(/check your email/i)).toBeInTheDocument();
      });
    });

    it("shows validation error for email with + character", async () => {
      render(<LoginForm />);

      const emailInput = screen.getByPlaceholderText(/john@example\.com/i);
      await userEvent.type(emailInput, "test+tag@gmail.com");

      const loginButton = screen.getByRole("button", { name: /^login$/i });
      await userEvent.click(loginButton);

      expect(mockSignInWithMagicLink).not.toHaveBeenCalled();
    });
  });
});
