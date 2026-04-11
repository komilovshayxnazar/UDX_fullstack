import { useEffect, useRef } from 'react';
import { MapPin } from 'lucide-react';

interface MapSelectorProps {
  center: { lat: number; lng: number };
  onLocationSelect: (lat: number, lng: number) => void;
}

export function MapSelector({ center, onLocationSelect }: MapSelectorProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  useEffect(() => {
    // Dynamically import Leaflet to avoid SSR issues
    import('leaflet').then((L) => {
      if (!mapContainerRef.current || mapRef.current) return;

      // Create map
      const map = L.map(mapContainerRef.current).setView([center.lat, center.lng], 13);
      mapRef.current = map;

      // Add tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(map);

      // Create custom icon
      const customIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="color: #af47ff; font-size: 32px; margin-left: -16px; margin-top: -32px;">📍</div>',
        iconSize: [32, 32],
      });

      // Add marker at center
      const marker = L.marker([center.lat, center.lng], { 
        icon: customIcon,
        draggable: true 
      }).addTo(map);
      markerRef.current = marker;

      // Handle marker drag
      marker.on('dragend', () => {
        const position = marker.getLatLng();
        onLocationSelect(position.lat, position.lng);
      });

      // Handle map click
      map.on('click', (e: any) => {
        const { lat, lng } = e.latlng;
        marker.setLatLng([lat, lng]);
        onLocationSelect(lat, lng);
      });
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update marker position when center changes
  useEffect(() => {
    if (mapRef.current && markerRef.current) {
      mapRef.current.setView([center.lat, center.lng], 13);
      markerRef.current.setLatLng([center.lat, center.lng]);
    }
  }, [center]);

  return (
    <div className="relative h-[500px] w-[600px]">
      <div ref={mapContainerRef} className="h-full w-full" />
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-lg bg-background/90 px-4 py-2 shadow-lg backdrop-blur-sm">
        <p className="text-center">
          <MapPin className="mr-2 inline h-4 w-4 text-[#af47ff]" />
          Click or drag the marker to select location
        </p>
      </div>
      <style>{`
        .leaflet-container {
          height: 100%;
          width: 100%;
          border-radius: 8px;
        }
      `}</style>
    </div>
  );
}
