"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  SortingState,
  ColumnFiltersState,
} from "@tanstack/react-table";
import {
  Mail,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  Tag,
  Zap,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { useAppStore, EmailMessage } from "@/lib/store";

interface EmailWithThread extends EmailMessage {
  thread_count: number;
  thread_latest: string;
}

const columnHelper = createColumnHelper<EmailWithThread>();

const TAG_COLORS: Record<string, "default" | "success" | "warning" | "danger" | "info"> = {
  fixture: "success",
  charter: "info",
  market: "warning",
  operations: "danger",
  default: "default",
};

function getTagVariant(tag: string): "default" | "success" | "warning" | "danger" | "info" {
  return TAG_COLORS[tag.toLowerCase()] || "default";
}

const columns = [
  columnHelper.accessor("subject", {
    header: "Subject",
    cell: (info) => (
      <div className="flex flex-col">
        <span className={`font-medium ${!info.row.original.is_read ? "text-gray-900" : "text-gray-600"}`}>
          {info.getValue()}
        </span>
        <span className="text-xs text-gray-500 truncate max-w-md">
          {info.row.original.body.substring(0, 100)}...
        </span>
      </div>
    ),
  }),
  columnHelper.accessor("from", {
    header: "From",
    cell: (info) => (
      <div className="text-sm">
        <div className="font-medium text-gray-900">{info.getValue()}</div>
      </div>
    ),
  }),
  columnHelper.accessor("tags", {
    header: "Tags",
    cell: (info) => (
      <div className="flex flex-wrap gap-1">
        {info.getValue().map((tag) => (
          <Badge key={tag} variant={getTagVariant(tag)}>
            {tag}
          </Badge>
        ))}
      </div>
    ),
  }),
  columnHelper.accessor("received_at", {
    header: "Date",
    cell: (info) => {
      const date = new Date(info.getValue());
      const now = new Date();
      const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
      
      let displayDate: string;
      if (diffDays === 0) {
        displayDate = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      } else if (diffDays === 1) {
        displayDate = "Yesterday";
      } else if (diffDays < 7) {
        displayDate = date.toLocaleDateString("en-US", { weekday: "short" });
      } else {
        displayDate = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      }
      
      return <span className="text-sm text-gray-500">{displayDate}</span>;
    },
  }),
  columnHelper.display({
    id: "actions",
    header: "",
    cell: (info) => (
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="flex items-center gap-1"
          onClick={() => handleExtractFixture(info.row.original)}
        >
          <Zap className="w-3 h-3" />
          Extract
        </Button>
      </div>
    ),
  }),
];

function handleExtractFixture(email: EmailWithThread) {
  // This would open a modal or navigate to extract fixture
  console.log("Extract fixture from email:", email.id);
  alert(`Extracting fixture from email: ${email.subject}`);
}

export default function EmailInboxPage() {
  const [emails, setEmails] = useState<EmailWithThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [selectedTagFilter, setSelectedTagFilter] = useState("all");
  const [selectedSenderFilter, setSelectedSenderFilter] = useState("all");
  
  const { emails: storeEmails } = useAppStore();

  useEffect(() => {
    async function fetchEmails() {
      try {
        // Try to fetch from API first
        const res = await fetch("http://localhost:8000/api/v1/emails");
        if (res.ok) {
          const data = await res.json();
          // Add thread info and set defaults
          const emailsWithThread = data.map((email: EmailMessage, idx: number, arr: EmailMessage[]) => ({
            ...email,
            thread_count: 1,
            thread_latest: email.received_at,
          }));
          setEmails(emailsWithThread);
        } else {
          // Fallback to mock data
          setEmails(getMockEmails());
        }
      } catch (err) {
        console.log("Using mock email data");
        setEmails(getMockEmails());
      } finally {
        setLoading(false);
      }
    }
    fetchEmails();
  }, []);

  const uniqueTags = useMemo(() => {
    const tags = new Set<string>();
    emails.forEach((email) => email.tags.forEach((tag) => tags.add(tag)));
    return Array.from(tags);
  }, [emails]);

  const uniqueSenders = useMemo(() => {
    const senders = new Set<string>();
    emails.forEach((email) => senders.add(email.from));
    return Array.from(senders);
  }, [emails]);

  const filteredEmails = useMemo(() => {
    let result = emails;
    
    if (selectedTagFilter !== "all") {
      result = result.filter((email) => email.tags.includes(selectedTagFilter));
    }
    
    if (selectedSenderFilter !== "all") {
      result = result.filter((email) => email.from === selectedSenderFilter);
    }
    
    return result;
  }, [emails, selectedTagFilter, selectedSenderFilter]);

  const table = useReactTable({
    data: filteredEmails,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const unreadCount = emails.filter((e) => !e.is_read).length;
  const fixtureEmails = emails.filter((e) => e.tags.includes("fixture")).length;

  if (loading) {
    return (
      <Navbar>
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      </Navbar>
    );
  }

  return (
    <Navbar>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <Mail className="w-7 h-7 text-blue-600" />
              Wake Email Inbox
            </h1>
            <p className="text-gray-500 mt-1">
              Auto-tagged emails with fixture extraction
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Sync
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-900">{emails.length}</div>
              <div className="text-sm text-gray-500">Total Emails</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-blue-600">{unreadCount}</div>
              <div className="text-sm text-gray-500">Unread</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-green-600">{fixtureEmails}</div>
              <div className="text-sm text-gray-500">Fixture Tagged</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-900">{uniqueTags.length}</div>
              <div className="text-sm text-gray-500">Active Tags</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="py-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search emails..."
                    value={globalFilter}
                    onChange={(e) => setGlobalFilter(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div className="flex gap-3">
                <Select
                  options={[
                    { value: "all", label: "All Tags" },
                    ...uniqueTags.map((tag) => ({ value: tag, label: tag })),
                  ]}
                  value={selectedTagFilter}
                  onChange={(e) => setSelectedTagFilter(e.target.value)}
                  className="w-40"
                />
                <Select
                  options={[
                    { value: "all", label: "All Senders" },
                    ...uniqueSenders.map((sender) => ({ value: sender, label: sender })),
                  ]}
                  value={selectedSenderFilter}
                  onChange={(e) => setSelectedSenderFilter(e.target.value)}
                  className="w-48"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Email Table */}
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th
                        key={header.id}
                        className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-1">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {header.column.getIsSorted() && (
                            <span>
                              {header.column.getIsSorted() === "asc" ? (
                                <ChevronUp className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-6 py-12 text-center text-gray-500">
                      <Mail className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p className="text-lg font-medium">No emails found</p>
                      <p className="text-sm">Connect your email to start receiving messages</p>
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className={`hover:bg-gray-50 ${!row.original.is_read ? "bg-blue-50/50" : ""}`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-6 py-4 whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {table.getRowModel().rows.length} of {filteredEmails.length} emails
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-sm text-gray-600">Page 1</span>
            <Button variant="outline" size="sm" disabled>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </Navbar>
  );
}

function getMockEmails(): EmailWithThread[] {
  return [
    {
      id: "1",
      thread_id: "thread-1",
      subject: "Fixtures: MR Tanker - Singapore to Chiba",
      from: "broker@clarksons.com",
      to: "charterer@company.com",
      body: "Dear All, We have the following fixture to report: Vessel: MT Pacific Grace Cargo: 45,000 MT Naptha Laycan: 15-20 March Load: Singapore Discharge: Chiba Rate: WS 125 Please confirm your acceptance.",
      received_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      tags: ["fixture", "charter"],
      is_read: false,
      synced: true,
      thread_count: 1,
      thread_latest: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    },
    {
      id: "2",
      thread_id: "thread-2",
      subject: "Market Update: VLCC Rates Surge",
      from: "market@poten.com",
      to: "charterer@company.com",
      body: "VLCC rates continue to rally on strong demand. WS rates up 15 points this week...",
      received_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      tags: ["market"],
      is_read: true,
      synced: true,
      thread_count: 1,
      thread_latest: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    },
    {
      id: "3",
      thread_id: "thread-3",
      subject: "SSY - Weekly Market Report",
      from: "research@ssy.com",
      to: "charterer@company.com",
      body: "Here's your weekly market summary. Product tanker segment showing strong performance...",
      received_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      tags: ["market"],
      is_read: true,
      synced: true,
      thread_count: 1,
      thread_latest: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
    },
    {
      id: "4",
      thread_id: "thread-4",
      subject: "Operations: ETA Update - MT Ocean Pride",
      from: "operations@ vessel.com",
      to: "charterer@company.com",
      body: "Please be advised that MT Ocean Pride has revised ETA for Singapore anchorage to March 18th 0800 local time.",
      received_at: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
      tags: ["operations"],
      is_read: false,
      synced: true,
      thread_count: 1,
      thread_latest: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(),
    },
    {
      id: "5",
      thread_id: "thread-5",
      subject: "Fixture: LR2 - Ras Tanura to Rotterdam",
      from: "gibson@holm Shipping.com",
      to: "charterer@company.com",
      body: "We can offer the following: Vessel: STI Sapphire Cargo: 80,000 MT Gas Oil Laycan: 20-25 March Load: Ras Tanura Discharge: Rotterdam Rate: WS 95 We await your confirmation.",
      received_at: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
      tags: ["fixture", "charter"],
      is_read: true,
      synced: true,
      thread_count: 1,
      thread_latest: new Date(Date.now() - 1000 * 60 * 60 * 72).toISOString(),
    },
  ];
}
