"use client";

import { useEffect, useState } from "react";

interface ServiceWorkerRegistration {
  ready: boolean;
  cached: boolean;
  offline: boolean;
  updateAvailable: boolean;
}

export function useServiceWorker() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration>({
    ready: false,
    cached: false,
    offline: false,
    updateAvailable: false,
  });

  useEffect(() => {
    if (typeof window === "undefined" || !"serviceWorker" in navigator) {
      return;
    }

    async function registerSW() {
      try {
        const registration = await navigator.serviceWorker.register("/sw.js", {
          scope: "/",
        });

        console.log("SW registered:", registration.scope);

        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener("statechange", () => {
              if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
                setRegistration((prev) => ({ ...prev, updateAvailable: true }));
              }
            });
          }
        });

        setRegistration((prev) => ({ ...prev, ready: true }));

        if (registration.active?.state === "activated") {
          setRegistration((prev) => ({ ...prev, cached: true }));
        }
      } catch (error) {
        console.error("SW registration failed:", error);
      }
    }

    registerSW();

    const handleOnline = () => setRegistration((prev) => ({ ...prev, offline: false }));
    const handleOffline = () => setRegistration((prev) => ({ ...prev, offline: true }));

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    setRegistration((prev) => ({ ...prev, offline: !navigator.onLine }));

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return registration;
}

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<Event | null>(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    const handleAppInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    
    (deferredPrompt as any).prompt();
    const { outcome } = await (deferredPrompt as any).userChoice;
    
    if (outcome === "accepted") {
      setInstalled(true);
    }
    setDeferredPrompt(null);
  };

  if (installed || !deferredPrompt) return null;

  return (
    <button
      onClick={handleInstall}
      className="fixed bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg hover:bg-blue-700 transition-colors z-50"
    >
      Install App
    </button>
  );
}
