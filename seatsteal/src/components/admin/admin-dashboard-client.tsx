import { useState, useEffect } from "react";
import { StatsCard } from "@/components/admin/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Users,
  BookOpen,
  Bell,
  TrendingUp,
  Activity,
  School,
  RefreshCw,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { formatChartDate } from "@/lib/date-utils";

interface AnalyticsData {
  overview: {
    totalUsers: number;
    adminUsers: number;
    totalSubscriptions: number;
    activeSubscriptions: number;
    recentSubscriptions: number;
    totalNotifications: number;
    recentNotifications: number;
    successfulNotifications: number;
    failedNotifications: number;
    totalCourses: number;
    totalColleges: number;
    notificationSuccessRate: number;
  };
  notificationTrends: Array<{
    date: string;
    count: number;
  }>;
  collegeStats: Array<{
    collegeId: number;
    collegeName: string;
    shortName: string;
    userCount: number;
  }>;
  popularCourses: Array<{
    courseId: number;
    courseCode: string;
    title: string;
    collegeName: string;
    subscriptionCount: number;
  }>;
  recentEnrollmentChanges: Array<{
    classId: number;
    courseCode: string | null;
    title: string | null;
    collegeName: string | null;
    enrollmentStatus: string;
    scrapedAt: Date;
  }>;
}

export function AdminDashboardClient() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [timeframe, setTimeframe] = useState("30");
  const [collegeFilter, setCollegeFilter] = useState("all");

  const fetchAnalytics = async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        timeframe,
        ...(collegeFilter !== "all" && { college: collegeFilter }),
      });
      const response = await fetchWithToasts(`/api/admin/analytics?${params}`);
      const result = await response.json();

      if (response.ok && result.success) {
        setData(result.data);
      } else {
        setError(result.error || "Failed to fetch analytics");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred while fetching analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [timeframe, collegeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <Button onClick={fetchAnalytics}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Admin Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Complete system analytics and user management
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={collegeFilter} onValueChange={setCollegeFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select College" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Colleges</SelectItem>
              {data?.collegeStats.map((college) => (
                <SelectItem
                  key={college.collegeId}
                  value={college.collegeId.toString()}
                >
                  {college.shortName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={fetchAnalytics} disabled={loading}>
            {loading ? (
              <Spinner className="size-4 mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : data ? (
        <>
          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatsCard
              title="Total Users"
              value={data.overview.totalUsers.toLocaleString()}
              description="Registered users"
              icon={Users}
            />
            <StatsCard
              title="Active Subscriptions"
              value={data.overview.activeSubscriptions.toLocaleString()}
              description="Course monitoring subscriptions"
              icon={Bell}
            />
            <StatsCard
              title="Success Rate"
              value={`${data.overview.notificationSuccessRate.toFixed(1)}%`}
              description="Notification delivery rate"
              icon={TrendingUp}
            />
            <StatsCard
              title="Recent Activity"
              value={data.overview.recentNotifications.toLocaleString()}
              description={`Notifications last ${timeframe} days`}
              icon={Activity}
            />
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Notification Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Notification Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data.notificationTrends}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="opacity-30"
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => formatChartDate(value)}
                      className="text-gray-600 dark:text-gray-400"
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      className="text-gray-600 dark:text-gray-400"
                    />
                    <Tooltip
                      labelFormatter={(value) => formatChartDate(value)}
                      contentStyle={{
                        backgroundColor: "var(--background)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        color: "var(--foreground)",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={{ fill: "#2563eb" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* College Stats Table */}
            <Card>
              <CardHeader>
                <CardTitle>College Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.collegeStats.slice(0, 8).map((college) => (
                    <div
                      key={college.collegeId}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-sm dark:text-gray-200">
                          {college.shortName}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {college.collegeName}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-lg dark:text-gray-200">
                          {college.userCount}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          users
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Popular Courses */}
          {data.popularCourses?.filter((course) => course.subscriptionCount > 0)
            .length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Popular Courses</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.popularCourses
                    ?.filter((course) => course.subscriptionCount > 0)
                    .slice(0, 8)
                    .map(
                      (
                        course: {
                          courseId: number;
                          courseCode: string;
                          title: string;
                          collegeName: string | null;
                          subscriptionCount: number;
                        },
                        index: number,
                      ) => (
                        <div
                          key={index}
                          className="flex items-center justify-between"
                        >
                          <div>
                            <p className="font-medium text-sm dark:text-gray-200">
                              {course.courseCode}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              {course.collegeName || "Unknown College"}
                            </p>
                          </div>
                          <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                            {course.subscriptionCount} watching
                          </span>
                        </div>
                      ),
                    )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Additional Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatsCard
              title="Total Courses"
              value={data.overview.totalCourses.toLocaleString()}
              description="Courses in database"
              icon={BookOpen}
            />
            <StatsCard
              title="Universities"
              value={data.overview.totalColleges.toLocaleString()}
              description="Supported institutions"
              icon={School}
            />
            <StatsCard
              title="All-Time Notifications"
              value={data.overview.totalNotifications.toLocaleString()}
              description="Total notifications sent"
              icon={Bell}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
