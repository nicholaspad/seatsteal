import { BookOpen, Users, Bell } from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";

function AnimatedStat({
  value,
  suffix,
  description,
  icon: Icon,
  color,
}: {
  value: number;
  suffix: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  const { count, ref } = useCountUp({
    end: value,
    duration: 2500,
    startOnInView: true,
    threshold: 0.3,
  });

  return (
    <div ref={ref} className="text-center">
      <Icon className={`h-12 w-12 mx-auto mb-3 ${color}`} />
      <p className="text-3xl font-bold">
        {count.toLocaleString()}
        {suffix}
      </p>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function AnimatedStats() {
  const stats = [
    {
      value: 5000,
      suffix: "+",
      description: "Courses monitored daily",
      icon: BookOpen,
      color: "text-green-600",
    },
    {
      value: 1000,
      suffix: "+",
      description: "Students helped",
      icon: Users,
      color: "text-purple-600",
    },
    {
      value: 70000,
      suffix: "+",
      description: "Total notifications sent",
      icon: Bell,
      color: "text-orange-600",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {stats.map((stat, index) => (
        <AnimatedStat key={index} {...stat} />
      ))}
    </div>
  );
}
