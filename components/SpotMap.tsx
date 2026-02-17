import React, { useEffect, useRef } from 'react';
import { Spot } from '../types';
import { AppConfig } from '../config';

interface SpotMapProps {
    spots: Spot[];
    onSpotClick?: (spot: Spot) => void;
    height?: string;
    initialCenter?: [number, number];
    initialZoom?: number;
}

// Ensure Leaflet is available globally via CDN
declare global {
    interface Window {
        L: any;
    }
}

export const SpotMap: React.FC<SpotMapProps> = ({
    spots,
    onSpotClick,
    height = '500px',
    initialCenter = AppConfig.MAP.DEFAULT_CENTER,
    initialZoom = AppConfig.MAP.DEFAULT_ZOOM
}) => {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<any>(null);
    const clusterGroupRef = useRef<any>(null);
    const initializedRef = useRef(false);

    // Initialize Map
    useEffect(() => {
        if (!window.L || !mapRef.current || initializedRef.current) return;

        try {
            const L = window.L;

            // Create map instance
            const map = L.map(mapRef.current).setView(initialCenter, initialZoom);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Create cluster group
            if (L.markerClusterGroup) {
                const clusterGroup = L.markerClusterGroup({
                    showCoverageOnHover: false,
                    maxClusterRadius: 50,
                    spiderfyOnMaxZoom: true,
                    disableClusteringAtZoom: 16
                });
                map.addLayer(clusterGroup);
                clusterGroupRef.current = clusterGroup;
            } else {
                console.warn('Leaflet.markercluster not found, falling back to simple layer group');
                const layerGroup = L.layerGroup().addTo(map);
                clusterGroupRef.current = layerGroup;
            }

            mapInstanceRef.current = map;
            initializedRef.current = true;

        } catch (error) {
            console.error('Failed to initialize map', error);
        }

        return () => {
            // Cleanup on unmount is tricky with React double-mount effect in dev
            // Better to rely on ref checks
            if (mapInstanceRef.current && !initializedRef.current) {
                mapInstanceRef.current.remove();
                mapInstanceRef.current = null;
            }
        };
    }, []);

    // Update Markers
    useEffect(() => {
        if (!mapInstanceRef.current || !clusterGroupRef.current || !window.L) return;

        const L = window.L;
        const clusterGroup = clusterGroupRef.current;

        // Clear existing layers
        clusterGroup.clearLayers();

        const markers: any[] = [];
        const bounds = L.latLngBounds();

        spots.forEach(spot => {
            if (spot.location) {
                const { lat, lng } = spot.location;

                // Category color mapping
                let markerColor = 'blue';
                switch (spot.category) {
                    case 'History': markerColor = 'red'; break;
                    case 'Nature': markerColor = 'green'; break;
                    case 'Food': markerColor = 'orange'; break;
                    case 'Shopping': markerColor = 'violet'; break;
                    case 'Art': markerColor = 'gold'; break;
                    case 'Relax': markerColor = 'blue'; break;
                    case 'Culture': markerColor = 'grey'; break;
                    default: markerColor = 'blue';
                }

                const icon = new L.Icon({
                    iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-${markerColor}.png`,
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                });

                const marker = L.marker([lat, lng], { icon, title: spot.name });

                const popupContent = `
          <div class="text-center p-2" style="min-width: 200px;">
            <b class="text-lg">${spot.name}</b>
            ${spot.area ? `<br/><span class="text-xs text-gray-500">📍 ${spot.area}</span>` : ''}
            <br/><span class="text-xs text-gray-500">${spot.category}</span>
            ${spot.image ? `<br/><img src="${spot.image}" style="width:100%; height:100px; object-fit:cover; margin-top:5px; border-radius:4px;" />` : ''}
            ${spot.description ? `<br/><p class="text-xs text-gray-600 mt-1 text-left">${spot.description.substring(0, 100)}${spot.description.length > 100 ? '...' : ''}</p>` : ''}
          </div>
        `;

                marker.bindPopup(popupContent);

                if (onSpotClick) {
                    marker.on('click', () => onSpotClick(spot));
                }

                markers.push(marker);
                clusterGroup.addLayer(marker);
                bounds.extend([lat, lng]);
            }
        });

        // Fit bounds if we have markers
        if (markers.length > 0 && mapInstanceRef.current) {
            try {
                mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
            } catch (e) {
                console.warn('Error fitting bounds', e);
            }
        }

    }, [spots]);

    return (
        <div className="relative w-full rounded-2xl overflow-hidden shadow-inner border border-gray-200 z-0" style={{ height }}>
            <div ref={mapRef} className="w-full h-full" style={{ background: '#f0f0f0' }}></div>
            {(!window.L) && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100/80">
                    <p>マップを読み込み中...</p>
                </div>
            )}
        </div>
    );
};
