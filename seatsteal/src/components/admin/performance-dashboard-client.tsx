import { useState, useEffect } from "react";
import { StatsCard } from "@/components/admin/stats-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { Zap, Database, RefreshCw } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { fetchWithToasts, ServerErrorWithToast } from "@/lib/api";

interface QueryPerformanceData {
  stats: {
    totalQueries: number;
    slowQueries: number;
    avgExecutionTime: number;
    slowQueryPercentage: number;
    mostCommonQueries: [string, number][];
  };
  databaseStats: {
    total_connections: number;
    active_connections: number;
    idle_connections: number;
  } | null;
  recentSlowQueries: Array<{
    query: string;
    executionTime: number;
    timestamp: Date;
    resultCount?: number;
  }>;
  hourlyPercentiles: Array<{
    hour: string;
    p50: number;
    p90: number;
    queryCount: number;
    totalSamples: number;
  }>;
}

export function PerformanceDashboardClient() {
  const [data, setData] = useState<QueryPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchPerformanceData = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await fetchWithToasts("/api/admin/query-performance");
      const result = await response.json();

      if (response.ok && result.success) {
        setData(result.data);
      } else {
        setError(result.error || "Failed to fetch performance data");
      }
    } catch (err) {
      if (err instanceof ServerErrorWithToast) {
        return; // Toast already shown
      }
      setError("An error occurred while fetching performance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData();
  }, []);

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <Button onClick={fetchPerformanceData}>
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
            Query Performance
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Database query monitoring and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button onClick={fetchPerformanceData} disabled={loading}>
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
          {[...Array(4)].map((_, i) => (
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
          {/* Performance Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <StatsCard
              title="Total Queries"
              value={data.stats.totalQueries.toLocaleString()}
              description="Queries monitored"
              icon={Zap}
            />
            <StatsCard
              title="Active Connections"
              value={data.databaseStats?.active_connections || 0}
              description={`${data.databaseStats?.total_connections || 0} total connections`}
              icon={Database}
            />
          </div>

          {/* P50/P90 Execution Time Trends */}
          <Card>
            <CardHeader>
              <CardTitle>Query Performance Trends (Last 72 Hours)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart
                  data={data.hourlyPercentiles
                    .slice(0, 72)
                    .reverse()
                    .map((item) => ({
                      ...item,
                      time: new Date(item.hour).toLocaleString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "numeric",
                      }),
                    }))}
                >
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 11 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    className="text-gray-600 dark:text-gray-400"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{
                      value: "Execution Time (ms)",
                      angle: -90,
                      position: "insideLeft",
                    }}
                    className="text-gray-600 dark:text-gray-400"
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
                            <p className="text-sm font-medium mb-2">{label}</p>
                            <p className="text-sm text-blue-600 dark:text-blue-400">
                              P50: {data.p50}ms
                            </p>
                            <p className="text-sm text-red-600 dark:text-red-400">
                              P90: {data.p90}ms
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {data.totalSamples} samples from {data.queryCount}{" "}
                              queries
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="p50"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    name="P50 (Median)"
                    dot={{ fill: "#3b82f6", r: 3 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p90"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="P90 (90th Percentile)"
                    dot={{ fill: "#ef4444", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Most Common Queries Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Most Common Queries</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={data.stats.mostCommonQueries
                      .slice(0, 5)
                      .map(([query, count]) => ({
                        query:
                          query.length > 30
                            ? query.substring(0, 30) + "..."
                            : query,
                        count,
                        fullQuery: query,
                      }))}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      className="opacity-30"
                    />
                    <XAxis
                      dataKey="query"
                      tick={{ fontSize: 10 }}
                      className="text-gray-600 dark:text-gray-400"
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      className="text-gray-600 dark:text-gray-400"
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
                              <p className="text-sm font-medium mb-1">
                                Query: {data.fullQuery}
                              </p>
                              <p className="text-sm">Count: {data.count}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Database Connection Status */}
            <Card>
              <CardHeader>
                <CardTitle>Database Connections</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {data.databaseStats ? (
                    <>
                      <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                        <div>
                          <p className="font-medium text-sm text-green-800 dark:text-green-200">
                            Active
                          </p>
                          <p className="text-xs text-green-600 dark:text-green-400">
                            Currently in use
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-lg text-green-800 dark:text-green-200">
                            {data.databaseStats.active_connections}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <div>
                          <p className="font-medium text-sm text-blue-800 dark:text-blue-200">
                            Idle
                          </p>
                          <p className="text-xs text-blue-600 dark:text-blue-400">
                            Available for use
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-lg text-blue-800 dark:text-blue-200">
                            {data.databaseStats.idle_connections}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <div>
                          <p className="font-medium text-sm dark:text-gray-200">
                            Total
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            All connections
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-lg dark:text-gray-200">
                            {data.databaseStats.total_connections}
                          </p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <p className="text-center text-gray-500 dark:text-gray-400">
                      Connection stats not available
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Slow Queries */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Slow Queries</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.recentSlowQueries.length > 0 ? (
                  data.recentSlowQueries.slice(0, 10).map((query, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-0"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-mono text-sm text-gray-900 dark:text-gray-100 truncate">
                          {query.query}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(query.timestamp).toLocaleString()}
                          {query.resultCount !== undefined && (
                            <span> • {query.resultCount} results</span>
                          )}
                        </p>
                      </div>
                      <div className="ml-4 text-right">
                        <p className="font-semibold text-sm text-red-600 dark:text-red-400">
                          {query.executionTime.toFixed(2)}ms
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                    No slow queries recorded
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
