import Link from "next/link";
import { WakeTable } from "@/components/wake/WakeTable";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-8">
              <h1 className="text-xl font-bold text-gray-900">OpenMaritime</h1>
              <nav className="flex gap-6">
                <Link href="/wake" className="text-sm font-medium text-gray-900">
                  Wake AI
                </Link>
                <Link href="/dashboard" className="text-sm font-medium text-gray-500 hover:text-gray-900">
                  Dashboard
                </Link>
                <Link href="/settings" className="text-sm font-medium text-gray-500 hover:text-gray-900">
                  Settings
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <button className="text-sm text-gray-500 hover:text-gray-900">Sign In</button>
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                Get Started
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Wake AI Dashboard</h2>
          <p className="text-gray-500 mt-1">Real-time fixture ranking with AI enrichment</p>
        </div>

        <WakeTable />
      </div>
    </main>
  );
}
