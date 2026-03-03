"use client";

import { clsx } from "clsx";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  id?: string;
}

export function Toggle({ checked, onChange, disabled, label, id }: ToggleProps) {
  const toggleId = id || label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <label htmlFor={toggleId} className="flex items-center gap-3 cursor-pointer">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        id={toggleId}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={clsx(
          "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
          checked ? "bg-blue-600" : "bg-gray-200",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <span
          aria-hidden="true"
          className={clsx(
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
            checked ? "translate-x-5" : "translate-x-0"
          )}
        />
      </button>
      {label && <span className="text-sm text-gray-700">{label}</span>}
    </label>
  );
}
