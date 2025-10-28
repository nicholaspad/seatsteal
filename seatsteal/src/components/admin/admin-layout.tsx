import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Users, Home, Shield, LogOut, Bell, Activity, Zap } from "lucide-react";

interface AdminLayoutProps {
  children: React.ReactNode;
}

const navigation = [
  {
    name: "Dashboard",
    href: "/admin",
    icon: Home,
  },
  {
    name: "Users",
    href: "/admin/users",
    icon: Users,
  },
  {
    name: "Scrapers",
    href: "/admin/scrapers",
    icon: Activity,
  },
  {
    name: "Performance",
    href: "/admin/performance",
    icon: Zap,
  },
  {
    name: "Notifications",
    href: "/admin/notifications",
    icon: Bell,
  },
];

export function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = useLocation().pathname;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white dark:bg-gray-800 shadow-sm border-r border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-8">
            <Shield className="h-8 w-8 text-red-600 dark:text-red-400" />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Admin Panel
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                SeatSteal
              </p>
            </div>
          </div>

          <nav className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800"
                      : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <Button
              asChild
              variant="outline"
              size="sm"
              className="w-full justify-start"
            >
              <Link to="/dashboard">
                <LogOut className="h-4 w-4 mr-2" />
                Back to App
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <div className="p-6">
          <div className="max-w-7xl mx-auto">{children}</div>
        </div>
      </div>
    </div>
  );
}
