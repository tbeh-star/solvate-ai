"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SEED_ACTIONS } from "@/lib/seed-actions";
// TODO: Re-enable Auth0 after testing
// import { useUser } from "@auth0/nextjs-auth0";

const pendingCount = SEED_ACTIONS.length;

const navItems = [
  { href: "/queue", label: "Action Queue", badge: pendingCount },
  { href: "/products", label: "Products", badge: 0 },
  { href: "/prices", label: "Prices", badge: 0 },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  // TODO: Re-enable Auth0 after testing
  // const { user, isLoading } = useUser();

  return (
    <div className="dashboard-shell min-h-screen">
      {/* Top nav */}
      <nav className="border-b border-gray-200/60 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex h-16 items-center justify-between">
            {/* Left: brand + nav */}
            <div className="flex items-center gap-10">
              <Link href="/queue" className="flex items-baseline gap-1.5">
                <span className="text-[17px] font-semibold tracking-tight text-gray-900">
                  Solvate
                </span>
                <span className="text-[11px] font-medium tracking-wide text-gray-400">
                  AI
                </span>
              </Link>

              <div className="flex items-center gap-1">
                {navItems.map((item) => {
                  const isActive = pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
                        isActive
                          ? "bg-gray-100/80 text-gray-900"
                          : "text-gray-500 hover:text-gray-900"
                      }`}
                    >
                      {item.label}
                      {item.badge > 0 && (
                        <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-gray-900 px-1 text-[10px] font-semibold tabular-nums text-white">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Right */}
            <div className="flex items-center gap-3">
              <span className="text-[13px] text-gray-400">dev@test.com</span>
              <span className="rounded bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-500">
                DEV
              </span>
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
