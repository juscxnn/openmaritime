"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";


interface VesselPosition {
  lat?: number;
  lon?: number;
  name?: string;
  destination?: string;
  eta?: string;
}

interface MiniMapProps {
  position: VesselPosition | null;
  className?: string;
}

export function MiniMap({ position, className = "" }: MiniMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    mapRef.current = L.map(containerRef.current, {
      center: [20, 0],
      zoom: 2,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      {
        maxZoom: 19,
      }
    ).addTo(mapRef.current);

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current || !position?.lat || !position?.lon) return;

    if (markerRef.current) {
      markerRef.current.setLatLng([position.lat, position.lon]);
    } else {
      markerRef.current = L.marker([position.lat, position.lon], {
        icon: L.divIcon({
          className: "vessel-marker",
          html: `<div style="
            width: 12px;
            height: 12px;
            background: #3b82f6;
            border: 2px solid white;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          "></div>`,
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        }),
      }).addTo(mapRef.current);
    }

    mapRef.current.setView([position.lat, position.lon], 5);
  }, [position]);

  if (!position?.lat || !position?.lon) {
    return (
      <div
        className={`bg-gray-100 rounded flex items-center justify-center ${className}`}
        style={{ minHeight: "150px" }}
      >
        <span className="text-gray-400 text-sm">No position</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`rounded overflow-hidden ${className}`}
      style={{ minHeight: "150px", height: "150px" }}
    />
  );
}


interface MapPopupProps {
  position: VesselPosition;
}

export function MapPopup({ position }: MapPopupProps) {
  if (!position?.lat || !position?.lon) return null;

  return (
    <div className="text-xs">
      <div className="font-medium">{position.name || "Vessel"}</div>
      <div className="text-gray-500">
        {position.lat.toFixed(2)}N, {position.lon.toFixed(2)}E
      </div>
      {position.destination && (
        <div className="text-gray-400">Dest: {position.destination}</div>
      )}
      {position.eta && <div className="text-gray-400">ETA: {position.eta}</div>}
    </div>
  );
}
