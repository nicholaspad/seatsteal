import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Bell,
  Mail,
  MessageSquare,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { formatLocalDateTime } from "@/lib/date-utils";

interface NotificationData {
  id: number;
  sentAt: Date;
  notificationType: string;
  status: string;
  message: string;
  userEmail: string;
  courseCode: string | null;
  courseTitle: string | null;
  collegeName: string;
  seatsRemaining: number | null;
  enrollmentStatus: string | null;
}

interface CollegeData {
  collegeId: number;
  collegeName: string;
  shortName: string;
}

interface NotificationResponse {
  success: boolean;
  data: {
    notifications: NotificationData[];
    colleges: CollegeData[];
    pagination: {
      page: number;
      limit: number;
      totalCount: number;
      totalPages: number;
    };
  };
}

export function NotificationsClient() {
  const [data, setData] = useState<NotificationData[]>([]);
  const [colleges, setColleges] = useState<CollegeData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [collegeFilter, setCollegeFilter] = useState("all");
  const [timeframe, setTimeframe] = useState("30");
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    totalCount: 0,
    totalPages: 0,
  });

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: "10",
        timeframe,
        ...(collegeFilter !== "all" && { college: collegeFilter }),
        ...(statusFilter !== "all" && { status: statusFilter }),
        ...(typeFilter !== "all" && { type: typeFilter }),
        ...(searchTerm && { search: searchTerm }),
      });

      const response = await fetchWithToasts(
        `/api/admin/notifications?${params}`,
      );
      const result: NotificationResponse = await response.json();

      if (response.ok && result.success) {
        setData(result.data.notifications);
        setColleges(result.data.colleges);
        setPagination(result.data.pagination);
      } else {
        setError("Failed to fetch notifications");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred while fetching notifications");
    } finally {
      setLoading(false);
    }
  }, [
    currentPage,
    timeframe,
    collegeFilter,
    statusFilter,
    typeFilter,
    searchTerm,
  ]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleFilterChange = (filterType: string, value: string) => {
    switch (filterType) {
      case "college":
        setCollegeFilter(value);
        break;
      case "timeframe":
        setTimeframe(value);
        break;
      case "status":
        setStatusFilter(value);
        break;
      case "type":
        setTypeFilter(value);
        break;
    }
    setCurrentPage(1);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "sent":
        return (
          <Badge variant="default" className="bg-green-600 hover:bg-green-700">
            Sent
          </Badge>
        );
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "pending":
        return (
          <Badge
            variant="secondary"
            className="bg-yellow-600 hover:bg-yellow-700 text-white"
          >
            Pending
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "email":
        return (
          <Badge variant="outline" className="flex items-center gap-1">
            <Mail className="h-3 w-3" />
            Email
          </Badge>
        );
      case "sms":
        return (
          <Badge variant="outline" className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            SMS
          </Badge>
        );
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  const truncateMessage = (message: string, maxLength: number = 50) => {
    return message.length > maxLength
      ? `${message.substring(0, maxLength)}...`
      : message;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Notifications
        </h1>
        <div className="flex items-center gap-4">
          <Select
            value={collegeFilter}
            onValueChange={(value) => handleFilterChange("college", value)}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select College" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Colleges</SelectItem>
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
          <Select
            value={timeframe}
            onValueChange={(value) => handleFilterChange("timeframe", value)}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={fetchNotifications} disabled={loading}>
            {loading ? (
              <Spinner className="size-4 mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notification Logs
          </CardTitle>
          <div className="flex gap-4 items-center mt-2 flex-wrap">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by email or course..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={(value) => handleFilterChange("status", value)}
            >
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="sent">Sent</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
            <Select
              value={typeFilter}
              onValueChange={(value) => handleFilterChange("type", value)}
            >
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="sms">SMS</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {loading ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Loading notifications...</p>
            </div>
          ) : data.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No notifications found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Sent At</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Course</TableHead>
                      <TableHead>College</TableHead>
                      <TableHead>Message</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((notification) => (
                      <TableRow key={notification.id}>
                        <TableCell className="font-medium text-sm">
                          {formatLocalDateTime(notification.sentAt)}
                        </TableCell>
                        <TableCell>
                          {getTypeBadge(notification.notificationType)}
                        </TableCell>
                        <TableCell>
                          {getStatusBadge(notification.status)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {notification.userEmail}
                        </TableCell>
                        <TableCell className="text-sm">
                          {notification.courseCode || "N/A"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {notification.collegeName}
                        </TableCell>
                        <TableCell className="text-sm max-w-xs">
                          <span title={notification.message}>
                            {truncateMessage(notification.message)}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-gray-500">
                  Showing {(currentPage - 1) * pagination.limit + 1} to{" "}
                  {Math.min(
                    currentPage * pagination.limit,
                    pagination.totalCount,
                  )}{" "}
                  of {pagination.totalCount} notifications
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-sm">
                    Page {currentPage} of {pagination.totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage === pagination.totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
