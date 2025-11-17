import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sparkles,
  Calendar,
  Clock,
  TrendingUp,
  Loader2,
  Users,
  Bell,
  Target,
  CheckCircle,
  AlertCircle,
  XCircle,
  BarChart3,
} from "lucide-react";
import { formatCompactDateTime } from "@/lib/date-utils";
import { fetchWithToasts } from "@/lib/api";
import type { ClassWithEnrollment } from "@/types/api";

interface EnrollmentAnalysisData {
  classId: number;
  timesOpenedLast60Days: number;
  avgDaysToOpenLast60Days: number;
  mostRecentOpening: string | null;
  subscriptionsCount: number;
  notificationsSent: number;
  competitionLevel: "low" | "medium" | "high";
  generatedAt: string;
}

interface EnrollmentAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  classData: ClassWithEnrollment;
}

export function EnrollmentAnalysisModal({
  isOpen,
  onClose,
  classData,
}: EnrollmentAnalysisModalProps) {
  const [analysisData, setAnalysisData] =
    useState<EnrollmentAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysisData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchWithToasts(
        `/api/classes/${classData.classId}/enrollment-analysis`,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch enrollment analysis data");
      }

      const apiResponse = await response.json();

      const data = apiResponse.data || apiResponse;
      setAnalysisData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [classData.classId]);

  useEffect(() => {
    if (isOpen && classData.classId) {
      fetchAnalysisData();
    }
  }, [isOpen, classData.classId, fetchAnalysisData]);

  const getCompetitionColor = (level: string) => {
    switch (level) {
      case "low":
        return "text-green-600";
      case "medium":
        return "text-yellow-600";
      case "high":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const getCompetitionBadgeVariant = (level: string) => {
    switch (level) {
      case "low":
        return "default";
      case "medium":
        return "secondary";
      case "high":
        return "destructive";
      default:
        return "outline";
    }
  };

  const getCompetitionIcon = (level: string) => {
    switch (level) {
      case "low":
        return CheckCircle;
      case "medium":
        return AlertCircle;
      case "high":
        return XCircle;
      default:
        return BarChart3;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Enrollment analysis - {classData.sectionCode}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2">Loading analysis...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-red-600">
              <p>Error: {error}</p>
              <Button onClick={fetchAnalysisData} className="mt-2">
                Retry
              </Button>
            </div>
          )}

          {analysisData ? (
            <>
              {/* Statistics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {/* Times Opened */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-lg font-bold text-blue-600">
                        {analysisData.timesOpenedLast60Days}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Calendar className="h-3 w-3" />
                        Times opened (60 days)
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Average Days to Open */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-lg font-bold text-purple-600">
                        {analysisData.avgDaysToOpenLast60Days > 0
                          ? `${analysisData.avgDaysToOpenLast60Days}`
                          : "N/A"}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Clock className="h-3 w-3" />
                        Avg days to open (60 days)
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Most Recent Opening */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-lg font-bold text-green-600">
                        {analysisData.mostRecentOpening
                          ? formatCompactDateTime(
                              analysisData.mostRecentOpening,
                            )
                          : "None found"}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Target className="h-3 w-3" />
                        Most recent opening
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Subscriptions */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-lg font-bold text-orange-600">
                        {analysisData.subscriptionsCount}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Users className="h-3 w-3" /># subscriptions
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Notifications Sent */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div className="text-lg font-bold text-cyan-600">
                        {analysisData.notificationsSent}
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <Bell className="h-3 w-3" /># notifications sent
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Competition Level */}
                <Card>
                  <CardContent>
                    <div className="text-center">
                      <div
                        className={`text-2xl font-bold ${getCompetitionColor(analysisData.competitionLevel)} flex items-center justify-center gap-2`}
                      >
                        {(() => {
                          const CompetitionIcon = getCompetitionIcon(
                            analysisData.competitionLevel,
                          );
                          return <CompetitionIcon className="h-6 w-6" />;
                        })()}
                        <Badge
                          variant={getCompetitionBadgeVariant(
                            analysisData.competitionLevel,
                          )}
                        >
                          {analysisData.competitionLevel.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground flex items-center justify-center gap-1 mt-1">
                        <TrendingUp className="h-3 w-3" />
                        Competition level
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Competition Level Explanation */}
              <Card>
                <CardHeader>
                  <CardTitle>Competition Level Guide</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm italic mb-3">
                    Competition level is calculated based on number of
                    subscriptions, recent notification activity, opening
                    frequency, and how quickly classes typically open.
                  </p>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <p>
                      • <strong>Low:</strong> Few subscribers, good chance of
                      success
                    </p>
                    <p>
                      • <strong>Medium:</strong> Moderate competition, be
                      prepared
                    </p>
                    <p>
                      • <strong>High:</strong> Many watchers, very competitive
                    </p>
                  </div>
                </CardContent>
              </Card>
            </>
          ) : (
            !loading &&
            !error && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  No Analysis Available
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Analysis will become available as more enrollment data is
                  collected over time.
                </p>
              </div>
            )
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
