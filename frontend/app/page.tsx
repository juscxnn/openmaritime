"use client";

import Link from "next/link";
import { WakeTable } from "@/components/wake/WakeTable";
import { Navbar } from "@/components/layout/Navbar";

export default function Home() {
  return (
    <Navbar>
      <div className="space-y-6">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900">Wake AI Dashboard</h2>
          <p className="text-gray-500 mt-1">Real-time fixture ranking with AI enrichment</p>
        </div>

        <WakeTable />
      </div>
    </Navbar>
  );
}
