import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Settings from "../Settings";
import { renderAuthenticated } from "@/test/utils";
import { mockCollegesResponse, mockSettingsResponse } from "@/test/mocks/api";

// Mock the API module
const mockFetchWithToasts = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchWithToasts: (...args: unknown[]) => mockFetchWithToasts(...args),
  ServerErrorWithToast: class ServerErrorWithToast extends Error {},
}));

describe("Settings Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("shows loading spinner initially", () => {
      // Never resolve to keep in loading state
      mockFetchWithToasts.mockImplementation(
        () =>
          new Promise(() => {
            // Never resolve
          }),
      );

      renderAuthenticated(<Settings />);

      // The loading state should be rendered
      expect(screen.getByTestId("ion-content")).toBeInTheDocument();
    });
  });

  describe("Form Display", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSettingsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("displays phone number input", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        const phoneInput = screen.getByLabelText(/Phone Number/i);
        expect(phoneInput).toHaveValue("1234567890");
      });
    });

    it("displays college selector", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/College\/University/i),
        ).toBeInTheDocument();
      });
    });

    it("shows placeholder when no college is selected", async () => {
      const settingsWithoutCollege = {
        ...mockSettingsResponse,
        data: {
          ...mockSettingsResponse.data,
          collegeId: 0,
          collegeName: "",
        },
      };

      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(settingsWithoutCollege),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Settings />);

      await waitFor(() => {
        const collegeTrigger = screen.getByLabelText(/College\/University/i);
        expect(collegeTrigger).toHaveTextContent("Select");
      });
    });

    it("displays Account Settings title", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("Account Settings")).toBeInTheDocument();
      });
    });

    it("displays notification info alert", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(
          screen.getByText("Avoid Missing Notifications"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("notifications@seatsteal.app"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Phone Validation", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSettingsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("shows error for invalid phone number length", async () => {
      const user = userEvent.setup();
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Phone Number/i)).toBeInTheDocument();
      });

      const phoneInput = screen.getByLabelText(/Phone Number/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, "123");

      await waitFor(() => {
        expect(
          screen.getByText("Phone number must be exactly 10 digits"),
        ).toBeInTheDocument();
      });
    });

    it("allows empty phone number as valid", async () => {
      const user = userEvent.setup();
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Phone Number/i)).toBeInTheDocument();
      });

      const phoneInput = screen.getByLabelText(/Phone Number/i);
      await user.clear(phoneInput);

      // Empty phone should not show error
      await waitFor(() => {
        expect(
          screen.queryByText("Phone number must be exactly 10 digits"),
        ).not.toBeInTheDocument();
      });
    });

    it("strips non-digit characters from phone input", async () => {
      const user = userEvent.setup();
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Phone Number/i)).toBeInTheDocument();
      });

      const phoneInput = screen.getByLabelText(/Phone Number/i);
      await user.clear(phoneInput);
      // Type with dashes and parentheses
      await user.type(phoneInput, "(555) 123-4567");

      // Should only contain digits (strips non-digits)
      await waitFor(() => {
        expect(phoneInput).toHaveValue("5551234567");
      });
    });

    it("shows error immediately when phone is 1-9 digits", async () => {
      const user = userEvent.setup();
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Phone Number/i)).toBeInTheDocument();
      });

      const phoneInput = screen.getByLabelText(/Phone Number/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, "12345");

      await waitFor(() => {
        expect(
          screen.getByText("Phone number must be exactly 10 digits"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Save Changes Button", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSettingsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("disables save button when no changes", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        const saveButton = screen.getByRole("button", {
          name: /Save Changes/i,
        });
        expect(saveButton).toBeDisabled();
      });
    });

    it("enables save button when phone number changes", async () => {
      const user = userEvent.setup();
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByLabelText(/Phone Number/i)).toBeInTheDocument();
      });

      const phoneInput = screen.getByLabelText(/Phone Number/i);
      await user.clear(phoneInput);
      await user.type(phoneInput, "9876543210");

      await waitFor(() => {
        const saveButton = screen.getByRole("button", {
          name: /Save Changes/i,
        });
        expect(saveButton).not.toBeDisabled();
      });
    });
  });

  describe("Breadcrumb Navigation", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSettingsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("displays breadcrumb with Home, Dashboard, and Settings", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("Home")).toBeInTheDocument();
        expect(screen.getByText("Dashboard")).toBeInTheDocument();
        expect(screen.getByText("Settings")).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("shows error alert when settings fetch fails", async () => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({ success: false, error: "Server error" }),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });

      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(screen.getByText("Failed to load settings")).toBeInTheDocument();
      });
    });
  });

  describe("Notification Info", () => {
    beforeEach(() => {
      mockFetchWithToasts.mockImplementation((url: string) => {
        if (url.includes("/api/colleges")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockCollegesResponse),
          } as Response);
        }
        if (url.includes("/api/user/settings")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSettingsResponse),
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        } as Response);
      });
    });

    it("displays email and SMS contact information", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(
          screen.getByText("Avoid Missing Notifications"),
        ).toBeInTheDocument();
        expect(
          screen.getByText("notifications@seatsteal.app"),
        ).toBeInTheDocument();
        expect(screen.getByText("(415) 909-5191")).toBeInTheDocument();
      });
    });

    it("displays copy buttons next to contact info", async () => {
      renderAuthenticated(<Settings />);

      await waitFor(() => {
        expect(
          screen.getByText("notifications@seatsteal.app"),
        ).toBeInTheDocument();
      });

      // Find buttons that are ghost variant (used for copy buttons)
      const allButtons = screen.getAllByRole("button");
      // Filter for small ghost buttons (copy buttons have h-7 px-2 class)
      const smallButtons = allButtons.filter(
        (btn) =>
          btn.className.includes("h-7") && btn.className.includes("px-2"),
      );
      expect(smallButtons.length).toBeGreaterThanOrEqual(2);
    });
  });
});
