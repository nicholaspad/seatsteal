import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  RefreshCw,
  Building2,
  BookOpen,
  Users,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Mail,
  MessageSquare,
  Download,
  Bell,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { formatLocalDateTime } from "@/lib/date-utils";

interface College {
  collegeId: number;
  collegeName: string;
  shortName: string;
}

interface CollegeInfo {
  id: number;
  name: string;
  shortName: string;
  termCode: string | null;
  termName: string | null;
  emailEnabled: boolean;
  smsEnabled: boolean;
}

interface CollegeStats {
  totalCourses: number;
  totalClasses: number;
  activeSubscriptions: number;
  totalSubscriptions: number;
  totalNotifications: number;
  successfulNotifications: number;
  failedNotifications: number;
}

interface ScraperLog {
  id: number;
  outcome: string;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
  coursesCreated: number;
  classesCreated: number;
  enrollmentsSaved: number;
  errorMessage: string | null;
}

interface CollegeStatsData {
  college: CollegeInfo;
  stats: CollegeStats;
  recentScraperLogs: ScraperLog[];
}

interface TermCode {
  code: string;
  description: string;
}

interface TermCodesData {
  college: string;
  terms: TermCode[];
  status: "success" | "error" | "manual";
  error: string | null;
}

interface Notification {
  id: number;
  sentAt: string;
  notificationType: string;
  status: string;
  message: string;
  userEmail: string | null;
  courseCode: string | null;
  courseTitle: string | null;
  collegeName: string;
  seatsRemaining: number | null;
  enrollmentStatus: string | null;
}

export function CollegesClient() {
  const [colleges, setColleges] = useState<College[]>([]);
  const [selectedCollegeId, setSelectedCollegeId] = useState<number | null>(
    null,
  );
  const [collegeStats, setCollegeStats] = useState<CollegeStatsData | null>(
    null,
  );
  const [availableTerms, setAvailableTerms] = useState<TermCode[]>([]);
  const [termsStatus, setTermsStatus] = useState<string | null>(null);
  const [termsError, setTermsError] = useState<string | null>(null);
  const [selectedNewTerm, setSelectedNewTerm] = useState<string>("");
  const [newTermName, setNewTermName] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);
  const [termsLoading, setTermsLoading] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [error, setError] = useState("");
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);

  // Fetch colleges list on mount
  useEffect(() => {
    fetchColleges();
  }, []);

  // Fetch college stats and notifications when selection changes
  useEffect(() => {
    if (selectedCollegeId) {
      fetchCollegeStats(selectedCollegeId);
      fetchNotifications(selectedCollegeId);
      // Reset term selection
      setAvailableTerms([]);
      setSelectedNewTerm("");
      setNewTermName("");
      setTermsStatus(null);
      setTermsError(null);
    }
  }, [selectedCollegeId]);

  const fetchColleges = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetchWithToasts("/api/admin/analytics");
      const result = await response.json();

      if (response.ok && result.success) {
        setColleges(result.data.collegeStats || []);
        // Auto-select first college
        if (result.data.collegeStats?.length > 0) {
          setSelectedCollegeId(result.data.collegeStats[0].collegeId);
        }
      } else {
        setError(result.error || "Failed to fetch colleges");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setError("An error occurred while fetching colleges");
    } finally {
      setLoading(false);
    }
  };

  const fetchCollegeStats = async (collegeId: number) => {
    setStatsLoading(true);

    try {
      const response = await fetchWithToasts(
        `/api/admin/colleges/${collegeId}/stats`,
      );
      const result = await response.json();

      if (response.ok && result.success) {
        setCollegeStats(result.data);
      } else {
        setError(result.error || "Failed to fetch college stats");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setError("An error occurred while fetching college stats");
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchNotifications = async (collegeId: number) => {
    setNotificationsLoading(true);

    try {
      const response = await fetchWithToasts(
        `/api/admin/notifications?college=${collegeId}&limit=100&timeframe=365`,
      );
      const result = await response.json();

      if (response.ok && result.success) {
        setNotifications(result.data.notifications || []);
      } else {
        // Don't set error for notifications failure, just clear the list
        setNotifications([]);
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setNotifications([]);
    } finally {
      setNotificationsLoading(false);
    }
  };

  const fetchAvailableTerms = async () => {
    if (!collegeStats) return;

    setTermsLoading(true);
    setTermsError(null);

    try {
      const response = await fetchWithToasts(
        `/api/admin/term-codes/${collegeStats.college.shortName}`,
      );
      const result = await response.json();

      if (response.ok && result.success) {
        const data: TermCodesData = result.data;
        setAvailableTerms(data.terms);
        setTermsStatus(data.status);
        if (data.error) {
          setTermsError(data.error);
        }
      } else {
        setTermsError(result.error || "Failed to fetch term codes");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setTermsError("An error occurred while fetching term codes");
    } finally {
      setTermsLoading(false);
    }
  };

  const handleUpdateTerm = async () => {
    if (!selectedCollegeId || !selectedNewTerm) return;

    setUpdateLoading(true);

    try {
      const body: { termCode: string; termName?: string } = {
        termCode: selectedNewTerm,
      };
      if (newTermName.trim()) {
        body.termName = newTermName.trim();
      }

      const response = await fetchWithToasts(
        `/api/admin/colleges/${selectedCollegeId}/term`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );

      const result = await response.json();

      if (response.ok) {
        setConfirmDialogOpen(false);
        setSelectedNewTerm("");
        setNewTermName("");
        setAvailableTerms([]);
        // Refresh college stats
        fetchCollegeStats(selectedCollegeId);
      } else {
        setError(result.detail || result.error || "Failed to update term code");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return;
      }
      setError("An error occurred while updating term code");
    } finally {
      setUpdateLoading(false);
    }
  };

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "partial":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "timeout":
        return <Clock className="h-4 w-4 text-orange-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getOutcomeBadgeVariant = (outcome: string) => {
    switch (outcome) {
      case "success":
        return "default" as const;
      case "error":
        return "destructive" as const;
      case "partial":
        return "secondary" as const;
      default:
        return "outline" as const;
    }
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null) return "-";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getNotificationStatusIcon = (status: string) => {
    switch (status) {
      case "sent":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getNotificationStatusBadgeVariant = (status: string) => {
    switch (status) {
      case "sent":
        return "default" as const;
      case "failed":
        return "destructive" as const;
      case "pending":
        return "secondary" as const;
      default:
        return "outline" as const;
    }
  };

  const getNotificationTypeIcon = (type: string) => {
    switch (type) {
      case "email":
        return <Mail className="h-3 w-3" />;
      case "sms":
        return <MessageSquare className="h-3 w-3" />;
      default:
        return <Bell className="h-3 w-3" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (error && !collegeStats) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-red-500">{error}</p>
        <Button onClick={fetchColleges}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Colleges
        </h1>
        <div className="flex items-center gap-4">
          <Select
            value={selectedCollegeId?.toString() || ""}
            onValueChange={(value) => setSelectedCollegeId(parseInt(value))}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select college" />
            </SelectTrigger>
            <SelectContent>
              {colleges.map((college) => (
                <SelectItem
                  key={college.collegeId}
                  value={college.collegeId.toString()}
                >
                  {college.shortName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              selectedCollegeId && fetchCollegeStats(selectedCollegeId)
            }
            disabled={statsLoading || !selectedCollegeId}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${statsLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Main content */}
      {statsLoading ? (
        <div className="flex items-center justify-center h-64">
          <Spinner className="h-8 w-8" />
        </div>
      ) : collegeStats ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column - College Info & Stats */}
          <div className="space-y-6">
            {/* College Info Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2 className="h-5 w-5" />
                  College Info
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Name
                    </p>
                    <p className="font-medium">{collegeStats.college.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Short Name
                    </p>
                    <p className="font-medium">
                      {collegeStats.college.shortName}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Current Term
                    </p>
                    <p className="font-medium">
                      {collegeStats.college.termCode || "Not set"}
                      {collegeStats.college.termName &&
                        ` - ${collegeStats.college.termName}`}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Notifications
                    </p>
                    <div className="flex items-center gap-2">
                      <div
                        className={`flex items-center gap-1 ${
                          collegeStats.college.emailEnabled
                            ? "text-green-600"
                            : "text-gray-400"
                        }`}
                      >
                        <Mail className="h-4 w-4" />
                        <span className="text-sm">Email</span>
                      </div>
                      <div
                        className={`flex items-center gap-1 ${
                          collegeStats.college.smsEnabled
                            ? "text-green-600"
                            : "text-gray-400"
                        }`}
                      >
                        <MessageSquare className="h-4 w-4" />
                        <span className="text-sm">SMS</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Stats Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Statistics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold">
                      {collegeStats.stats.totalCourses.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Courses
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold">
                      {collegeStats.stats.totalClasses.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Classes
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold">
                      {collegeStats.stats.activeSubscriptions.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Active Subscriptions
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold">
                      {collegeStats.stats.totalSubscriptions.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Total Subscriptions
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold">
                      {collegeStats.stats.totalNotifications.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Total Notifications
                    </p>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {collegeStats.stats.successfulNotifications.toLocaleString()}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Successful
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Scraper Logs Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Recent Scraper Logs
                </CardTitle>
              </CardHeader>
              <CardContent>
                {collegeStats.recentScraperLogs.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                    No scraper logs found
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {collegeStats.recentScraperLogs.map((log) => (
                      <div
                        key={log.id}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          {getOutcomeIcon(log.outcome)}
                          <div>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={getOutcomeBadgeVariant(log.outcome)}
                              >
                                {log.outcome}
                              </Badge>
                              <span className="text-sm text-gray-500">
                                {formatDuration(log.durationMs)}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {formatLocalDateTime(new Date(log.startedAt))}
                            </p>
                          </div>
                        </div>
                        <div className="text-right text-xs text-gray-500">
                          <div>+{log.coursesCreated} courses</div>
                          <div>+{log.classesCreated} classes</div>
                          <div>+{log.enrollmentsSaved} enrollments</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Term Code Update */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-red-600 dark:text-red-400">
                  Update Term Code
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Current Term */}
                <div>
                  <Label className="text-sm text-gray-500 dark:text-gray-400">
                    Current Term
                  </Label>
                  <div className="mt-1 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <p className="font-medium">
                      {collegeStats.college.termCode || "Not set"}
                      {collegeStats.college.termName &&
                        ` - ${collegeStats.college.termName}`}
                    </p>
                  </div>
                </div>

                {/* Fetch Available Terms */}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    onClick={fetchAvailableTerms}
                    disabled={termsLoading}
                    className="w-full"
                  >
                    {termsLoading ? (
                      <Spinner className="mr-2" />
                    ) : (
                      <Download className="h-4 w-4 mr-2" />
                    )}
                    {termsLoading
                      ? "Fetching..."
                      : "Fetch Available Term Codes"}
                  </Button>

                  {termsStatus === "manual" && (
                    <p className="text-sm text-yellow-600 dark:text-yellow-400">
                      {termsError}
                    </p>
                  )}

                  {termsStatus === "error" && (
                    <p className="text-sm text-red-600 dark:text-red-400">
                      Error: {termsError}
                    </p>
                  )}
                </div>

                {/* Term Selection */}
                {availableTerms.length > 0 && (
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="term-select">New Term Code</Label>
                      <Select
                        value={selectedNewTerm}
                        onValueChange={(value) => {
                          setSelectedNewTerm(value);
                          // Auto-fill term name from description
                          const term = availableTerms.find(
                            (t) => t.code === value,
                          );
                          if (term) {
                            setNewTermName(term.description);
                          }
                        }}
                      >
                        <SelectTrigger id="term-select" className="mt-1">
                          <SelectValue placeholder="Select a term" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableTerms.map((term) => (
                            <SelectItem key={term.code} value={term.code}>
                              {term.code} - {term.description}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label htmlFor="term-name">Term Name (optional)</Label>
                      <Input
                        id="term-name"
                        value={newTermName}
                        onChange={(e) => setNewTermName(e.target.value)}
                        placeholder="e.g., Spring 2026"
                        className="mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Manual Entry (if no terms fetched) */}
                {availableTerms.length === 0 && (
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="manual-term-code">
                        New Term Code (manual entry)
                      </Label>
                      <Input
                        id="manual-term-code"
                        value={selectedNewTerm}
                        onChange={(e) => setSelectedNewTerm(e.target.value)}
                        placeholder="e.g., SP26, 1262, 202601"
                        className="mt-1"
                      />
                    </div>

                    <div>
                      <Label htmlFor="manual-term-name">
                        Term Name (optional)
                      </Label>
                      <Input
                        id="manual-term-name"
                        value={newTermName}
                        onChange={(e) => setNewTermName(e.target.value)}
                        placeholder="e.g., Spring 2026"
                        className="mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Update Button */}
                <Button
                  variant="destructive"
                  onClick={() => setConfirmDialogOpen(true)}
                  disabled={!selectedNewTerm.trim()}
                  className="w-full"
                >
                  Update Term Code
                </Button>

                {/* Warning */}
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                    Warning: This will permanently delete:
                  </p>
                  <ul className="text-sm text-red-600 dark:text-red-400 list-disc list-inside mt-2">
                    <li>All courses and classes for this college</li>
                    <li>All enrollment data</li>
                    <li>All subscriptions</li>
                  </ul>
                  <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                    Notification logs are preserved for historical analytics.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Recent Notifications Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Recent Notifications
                </CardTitle>
              </CardHeader>
              <CardContent>
                {notificationsLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Spinner className="h-6 w-6" />
                  </div>
                ) : notifications.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                    No notifications found
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                      >
                        <div className="flex-shrink-0 mt-0.5">
                          {getNotificationStatusIcon(notification.status)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge
                              variant={getNotificationStatusBadgeVariant(
                                notification.status,
                              )}
                            >
                              {notification.status}
                            </Badge>
                            <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                              {getNotificationTypeIcon(
                                notification.notificationType,
                              )}
                              {notification.notificationType}
                            </span>
                            {notification.courseCode && (
                              <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                                {notification.courseCode}
                              </span>
                            )}
                          </div>
                          {notification.userEmail && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 truncate mt-1">
                              {notification.userEmail}
                            </p>
                          )}
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {formatLocalDateTime(new Date(notification.sentAt))}
                          </p>
                        </div>
                        {notification.seatsRemaining !== null && (
                          <div className="flex-shrink-0 text-right">
                            <p className="text-sm font-medium">
                              {notification.seatsRemaining}
                            </p>
                            <p className="text-xs text-gray-500">seats</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500">Select a college to view details</p>
        </div>
      )}

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent className="p-6">
          <DialogHeader>
            <DialogTitle className="text-red-600">
              Confirm Term Code Change
            </DialogTitle>
            <DialogDescription className="space-y-4">
              <p>
                You are about to update the term code for{" "}
                <strong>{collegeStats?.college.name}</strong> from{" "}
                <strong>{collegeStats?.college.termCode || "none"}</strong> to{" "}
                <strong>{selectedNewTerm}</strong>.
              </p>
              <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                <p className="font-medium text-red-600 dark:text-red-400">
                  This will permanently delete:
                </p>
                <ul className="list-disc list-inside mt-2 text-red-600 dark:text-red-400">
                  <li>
                    {collegeStats?.stats.totalCourses.toLocaleString()} courses
                  </li>
                  <li>
                    {collegeStats?.stats.totalClasses.toLocaleString()} classes
                  </li>
                  <li>
                    {collegeStats?.stats.totalSubscriptions.toLocaleString()}{" "}
                    subscriptions
                  </li>
                </ul>
              </div>
              <p className="font-medium">This action cannot be undone.</p>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDialogOpen(false)}
              disabled={updateLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleUpdateTerm}
              disabled={updateLoading}
            >
              {updateLoading ? "Updating..." : "Update Term Code"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
