"use client";

import * as React from "react";
import { clsx } from "clsx";

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function Tabs({ defaultValue, value, onValueChange, className, children, ...props }: TabsProps) {
  const [activeValue, setActiveValue] = React.useState(value || defaultValue || "");
  
  const currentValue = value !== undefined ? value : activeValue;
  
  const handleValueChange = (newValue: string) => {
    setActiveValue(newValue);
    onValueChange?.(newValue);
  };

  return (
    <div className={clsx("w-full", className)} {...props} data-value={currentValue}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            value: currentValue,
            onValueChange: handleValueChange,
          });
        }
        return child;
      })}
    </div>
  );
}

export function TabsList({ className, children, value, onValueChange, ...props }: React.HTMLAttributes<HTMLDivElement> & { value?: string; onValueChange?: (value: string) => void }) {
  return (
    <div
      className={clsx(
        "inline-flex items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800 p-1 text-gray-900 dark:text-gray-100",
        className
      )}
      role="tablist"
      {...props}
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            isActive: (child as React.ReactElement<any>).props.value === value,
            onSelect: () => onValueChange?.((child as React.ReactElement<any>).props.value),
          });
        }
        return child;
      })}
    </div>
  );
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  isActive?: boolean;
  onSelect?: () => void;
}

export function TabsTrigger({ className, isActive, onSelect, children, ...props }: TabsTriggerProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      onClick={onSelect}
      className={clsx(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        isActive
          ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
          : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export function TabsContent({ className, value: contentValue, ...props }: TabsContentProps) {
  const parent = React.useContext(React.createContext<{ value: string } | null>(null));
  const isActive = parent?.value === contentValue;

  if (!isActive) return null;

  return (
    <div
      role="tabpanel"
      className={clsx("mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-950 focus-visible:ring-offset-2", className)}
      {...props}
    />
  );
}
