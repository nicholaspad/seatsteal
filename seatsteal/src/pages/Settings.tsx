import { IonContent, IonPage } from "@ionic/react";
import { useSession } from "@/components/providers/SessionProvider";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import type { College } from "@/types/api";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { AlertTriangle, Mail, Save, School } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

interface UserSettings {
  email: string;
  phone: string;
  collegeId: number;
  collegeName: string;
}

export default function Settings() {
  const { user } = useSession();
  const [colleges, setColleges] = useState<College[]>([]);
  const [settings, setSettings] = useState<UserSettings>({
    email: "",
    phone: "",
    collegeId: 0,
    collegeName: "",
  });
  const [originalCollegeId, setOriginalCollegeId] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!user) return;

    try {
      setLoading(true);
      setError(null);

      // Fetch colleges and user settings in parallel
      const [collegesResponse, settingsResponse] = await Promise.all([
        fetchWithToasts("/api/colleges"),
        fetchWithToasts("/api/user/settings"),
      ]);

      // Handle colleges response
      if (collegesResponse.ok) {
        const collegesData = await collegesResponse.json();
        if (collegesData.success) {
          setColleges(collegesData.data);
        }
      }

      // Handle user settings response
      if (settingsResponse.ok) {
        const settingsData = await settingsResponse.json();
        if (settingsData.success) {
          const userSettings: UserSettings = settingsData.data;
          setSettings(userSettings);
          setOriginalCollegeId(userSettings.collegeId);
        }
      } else {
        throw new Error("Failed to load user settings");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Fetch colleges and user settings on page load
  useEffect(() => {
    if (user) {
      fetchData();
    }
  }, [user, fetchData]);

  const handleCollegeChange = (value: string) => {
    const collegeId = parseInt(value);
    const selectedCollege = colleges.find((c) => c.id === collegeId);

    setSettings({
      ...settings,
      collegeId,
      collegeName: selectedCollege?.name || "",
    });
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      // Save settings via API
      const response = await fetchWithToasts("/api/user/settings", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          collegeId: settings.collegeId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save settings");
      }

      const result = await response.json();

      // Update settings with the response data
      const updatedSettings: UserSettings = result.data;
      setSettings(updatedSettings);
      setOriginalCollegeId(updatedSettings.collegeId);

      // Show success message
      toast.success("Settings saved successfully");

      // Reload the page to refresh session context
      window.location.reload();
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = settings.collegeId !== originalCollegeId;

  if (loading) {
    return (
      <IonPage>
        <IonContent className="ion-padding">
          <div className="container mx-auto py-8">
            <div className="max-w-2xl mx-auto">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-center py-8">
                    <Spinner className="size-8" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  return (
    <IonPage>
      <IonContent className="ion-padding">
        <div className="container mx-auto py-8">
          {/* Breadcrumb Navigation */}
          <Breadcrumb className="mb-6">
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/">Home</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Settings</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl mx-auto space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Account Settings</CardTitle>
              </CardHeader>

              <CardContent className="space-y-6 pt-2">
                {error && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Email (Read-only) */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    Email Address
                  </Label>
                  <div className="relative">
                    <Input
                      id="email"
                      type="email"
                      value={settings.email}
                      disabled
                      className="bg-muted"
                    />
                    <Badge
                      variant="secondary"
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-xs"
                    >
                      Locked
                    </Badge>
                  </div>
                </div>

                {/* College Selection */}
                <div className="space-y-2">
                  <Label htmlFor="college" className="flex items-center gap-2">
                    <School className="h-4 w-4" />
                    College/University
                  </Label>
                  <Select
                    value={settings.collegeId.toString()}
                    onValueChange={handleCollegeChange}
                  >
                    <SelectTrigger id="college">
                      <SelectValue placeholder="Select your college" />
                    </SelectTrigger>
                    <SelectContent>
                      {colleges.map((college) => (
                        <SelectItem
                          key={college.id}
                          value={college.id.toString()}
                        >
                          {college.shortName} - {college.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-4">
                  <Button
                    onClick={handleSave}
                    disabled={!hasChanges || saving}
                    className="flex-1"
                  >
                    {saving ? (
                      <>
                        <Spinner className="size-4 mr-2" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </IonContent>
    </IonPage>
  );
}
