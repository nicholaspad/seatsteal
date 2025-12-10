import { useState, useEffect } from "react";
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
  Activity,
  RefreshCw,
  Play,
  Pause,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";
import { formatLocalDateTime, formatChartDate } from "@/lib/date-utils";

interface ScrapersAnalyticsData {
  overview: {
    totalScrapers: number;
    activeScrapers: number;
    errorScrapers: number;
    successRate: number;
    avgDuration: number;
    recentErrors: number;
    totalRuns: number;
    successfulRuns: number;
  };
  scraperDetails: Array<{
    scraperId: number;
    status: string;
    collegeId: number;
    collegeName: string;
    shortName: string;
    lastRunAt: Date | null;
    lastSuccessAt: Date | null;
    nextRunAt: Date | null;
    runCount: number;
    successCount: number;
    errorCount: number;
    lastErrorMessage: string | null;
    lastRunDurationMs: number | null;
    createdAt: Date;
    updatedAt: Date;
  }>;
  successRateTrends: Array<{
    date: string;
    collegeId: number;
    collegeName: string;
    shortName: string;
    totalRuns: number;
    successfulRuns: number;
    successRate: number;
  }>;
  performanceTrends: Array<{
    date: string;
    collegeId: number;
    collegeName: string;
    shortName: string;
    avgDuration: number;
    successCount: number;
    errorCount: number;
    totalRuns: number;
  }>;
  recentActivity: Array<{
    logId: number;
    scraperId: number;
    outcome: string;
    startedAt: Date;
    completedAt: Date | null;
    durationMs: number | null;
    errorMessage: string | null;
    coursesCreated: number;
    classesCreated: number;
    enrollmentsSaved: number;
    collegeName: string;
    shortName: string;
  }>;
  recentErrorDetails: Array<{
    logId: number;
    scraperId: number;
    startedAt: Date;
    errorMessage: string | null;
    collegeName: string;
    shortName: string;
  }>;
  collegeStats: Array<{
    collegeId: number;
    collegeName: string;
    shortName: string;
    scraperCount: number;
  }>;
}

export function ScrapersDashboardClient() {
  const [data, setData] = useState<ScrapersAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [timeframe, setTimeframe] = useState("30");
  const [collegeFilter, setCollegeFilter] = useState("all");

  const fetchScrapersAnalytics = async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        timeframe,
        ...(collegeFilter !== "all" && { college: collegeFilter }),
      });
      const response = await fetchWithToasts(`/api/admin/scrapers?${params}`);
      const result = await response.json();

      if (response.ok && result.success) {
        setData(result.data);
      } else {
        setError(result.error || "Failed to fetch scraper analytics");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred while fetching scraper analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScrapersAnalytics();
  }, [timeframe, collegeFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Helper function to get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <Play className="h-4 w-4 text-blue-600 dark:text-blue-400" />;
      case "idle":
        return <Pause className="h-4 w-4 text-gray-600 dark:text-gray-400" />;
      case "completed":
        return (
          <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
        );
      case "error":
        return <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return (
          <Activity className="h-4 w-4 text-gray-600 dark:text-gray-400" />
        );
    }
  };

  // Prepare chart data for performance trends grouped by college
  const performanceTrendsData =
    data?.performanceTrends.reduce(
      (acc, item) => {
        const existingDate = acc.find((d) => d.date === item.date);
        if (existingDate) {
          existingDate[item.shortName] = item.avgDuration / 1000; // Convert to seconds
        } else {
          acc.push({
            date: item.date,
            [item.shortName]: item.avgDuration / 1000,
          });
        }
        return acc;
      },
      [] as Array<Record<string, string | number>>,
    ) || [];

  // Get unique colleges for line chart colors
  const uniqueColleges = [
    ...new Set(data?.performanceTrends.map((item) => item.shortName) || []),
  ];
  const collegeColors = [
    "#3b82f6",
    "#ef4444",
    "#22c55e",
    "#f59e0b",
    "#8b5cf6",
    "#06b6d4",
    "#f97316",
    "#84cc16",
  ];

  // Prepare success rate trends data grouped by college
  const successRateTrendsData =
    data?.successRateTrends.reduce(
      (acc, item) => {
        const existingDate = acc.find((d) => d.date === item.date);
        const successRate =
          typeof item.successRate === "number"
            ? item.successRate
            : parseFloat(String(item.successRate)) || 0;
        if (existingDate) {
          existingDate[item.shortName] = successRate;
          // Store counts for tooltip
          existingDate[`${item.shortName}_counts`] = {
            successful: item.successfulRuns,
            total: item.totalRuns,
          };
        } else {
          acc.push({
            date: item.date,
            [item.shortName]: successRate,
            [`${item.shortName}_counts`]: {
              successful: item.successfulRuns,
              total: item.totalRuns,
            },
          });
        }
        return acc;
      },
      [] as Array<
        Record<string, string | number | { successful: number; total: number }>
      >,
    ) || [];

  // Get unique colleges for success rate chart colors
  const uniqueSuccessRateColleges = [
    ...new Set(data?.successRateTrends.map((item) => item.shortName) || []),
  ];

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <Button onClick={fetchScrapersAnalytics}>
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
            Scrapers Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Monitoring and analytics for all course scrapers
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
          <Button onClick={fetchScrapersAnalytics} disabled={loading}>
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
          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Scraper Status List */}
            <Card>
              <CardHeader>
                <CardTitle>Scraper Status by College</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {data.scraperDetails.map((scraper) => (
                    <div
                      key={scraper.scraperId}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border"
                    >
                      <div className="flex items-center gap-3">
                        {getStatusIcon(scraper.status)}
                        <div>
                          <p className="font-medium text-sm dark:text-gray-200">
                            {scraper.shortName}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                            {scraper.status}
                          </p>
                        </div>
                      </div>
                      <div className="text-right text-xs text-gray-500 dark:text-gray-400">
                        <div className="space-y-1">
                          {scraper.lastRunAt && (
                            <p>
                              <span className="font-medium">Last Run:</span>{" "}
                              {formatLocalDateTime(scraper.lastRunAt)}
                            </p>
                          )}
                          {scraper.lastSuccessAt && (
                            <p>
                              <span className="font-medium">Last Success:</span>{" "}
                              {formatLocalDateTime(scraper.lastSuccessAt)}
                            </p>
                          )}
                          {scraper.nextRunAt && (
                            <p>
                              <span className="font-medium">Next Run:</span>{" "}
                              {formatLocalDateTime(scraper.nextRunAt)}
                            </p>
                          )}
                          <p>
                            <span className="font-medium">Success Rate:</span>{" "}
                            {scraper.runCount > 0
                              ? `${((scraper.successCount / scraper.runCount) * 100).toFixed(1)}%`
                              : "N/A"}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Performance Trends by College */}
            <Card>
              <CardHeader>
                <CardTitle>Average Runtime by College</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={performanceTrendsData}>
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
                      label={{
                        value: "Duration (seconds)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />
                    <Tooltip
                      labelFormatter={(value) => formatChartDate(value)}
                      contentStyle={{
                        backgroundColor: "var(--background)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        color: "var(--foreground)",
                      }}
                      formatter={(value: number, name: string) => [
                        `${value.toFixed(1)}s`,
                        name,
                      ]}
                    />
                    {uniqueColleges.map((college, index) => (
                      <Line
                        key={college}
                        type="monotone"
                        dataKey={college}
                        stroke={collegeColors[index % collegeColors.length]}
                        strokeWidth={2}
                        name={college}
                        connectNulls={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Success Rate Trends by College */}
          <Card>
            <CardHeader>
              <CardTitle>Success Rate Trends by College</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={successRateTrendsData}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => formatChartDate(value)}
                    className="text-gray-600 dark:text-gray-400"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    className="text-gray-600 dark:text-gray-400"
                    label={{
                      value: "Success Rate (%)",
                      angle: -90,
                      position: "insideLeft",
                    }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    labelFormatter={(value) => formatChartDate(value)}
                    contentStyle={{
                      backgroundColor: "var(--background)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      color: "var(--foreground)",
                    }}
                    formatter={(
                      value: number | string,
                      name: string,
                      props: any,
                    ) => {
                      const percentage =
                        typeof value === "number"
                          ? value.toFixed(1)
                          : parseFloat(String(value)).toFixed(1);
                      const countsKey = `${name}_counts`;
                      const counts = props.payload[countsKey];

                      if (
                        counts &&
                        typeof counts === "object" &&
                        "successful" in counts &&
                        "total" in counts
                      ) {
                        return [
                          `${percentage}% (${counts.successful}/${counts.total})`,
                          name,
                        ];
                      }

                      return [`${percentage}%`, name];
                    }}
                  />
                  {uniqueSuccessRateColleges.map((college, index) => (
                    <Line
                      key={college}
                      type="monotone"
                      dataKey={college}
                      stroke={collegeColors[index % collegeColors.length]}
                      strokeWidth={2}
                      name={college}
                      connectNulls={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Recent Activity and Errors */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Recent Scraper Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {data.recentActivity.slice(0, 15).map((activity) => (
                    <div
                      key={activity.logId}
                      className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
                    >
                      <div>
                        <p className="font-medium text-sm dark:text-gray-200">
                          {activity.shortName}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatLocalDateTime(activity.startedAt)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p
                          className={`text-sm font-medium ${
                            activity.outcome === "success"
                              ? "text-green-600 dark:text-green-400"
                              : activity.outcome === "error"
                                ? "text-red-600 dark:text-red-400"
                                : "text-yellow-600 dark:text-yellow-400"
                          }`}
                        >
                          {activity.outcome.toUpperCase()}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {activity.durationMs
                            ? `${(activity.durationMs / 1000).toFixed(1)}s`
                            : ""}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recent Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {data.recentErrorDetails.slice(0, 10).map((error) => (
                    <div
                      key={error.logId}
                      className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <p className="font-medium text-sm text-red-700 dark:text-red-300">
                          {error.shortName}
                        </p>
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {formatLocalDateTime(error.startedAt)}
                        </p>
                      </div>
                      <p className="text-xs text-red-600 dark:text-red-300 truncate">
                        {error.errorMessage || "Unknown error"}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
