import React, { useEffect, useRef, useState } from 'react';
import { Spot } from '../types';
import { AppConfig } from '../config';

// Escape HTML special characters to prevent XSS when injecting
// external/AI-derived strings into Leaflet popup HTML.
const escapeHtml = (s: string) =>
    s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));

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
    const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

    // Initialize Map
    useEffect(() => {
        let cancelled = false;
        let pollId: ReturnType<typeof setInterval> | undefined;
        let timeoutId: ReturnType<typeof setTimeout> | undefined;

        const clearTimers = () => {
            if (pollId !== undefined) { clearInterval(pollId); pollId = undefined; }
            if (timeoutId !== undefined) { clearTimeout(timeoutId); timeoutId = undefined; }
        };

        const initMap = (): boolean => {
            if (cancelled || !mapRef.current || initializedRef.current) return false;

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
                setStatus('ready');
            } catch (error) {
                console.error('Failed to initialize map', error);
                setStatus('error');
            }
            // Return true to signal we're done attempting (success or hard error).
            return true;
        };

        if (window.L) {
            initMap();
        } else {
            // Leaflet CDN may not be loaded yet on mount; poll until available.
            pollId = setInterval(() => {
                if (cancelled) { clearTimers(); return; }
                if (window.L) {
                    clearTimers();
                    initMap();
                }
            }, 100);
            // Give up after 10s to avoid a permanent loading state.
            timeoutId = setTimeout(() => {
                clearTimers();
                if (!cancelled && !initializedRef.current) {
                    console.error('Leaflet (window.L) did not load in time');
                    setStatus('error');
                }
            }, 10000);
        }

        return () => {
            cancelled = true;
            clearTimers();
            if (mapInstanceRef.current) {
                mapInstanceRef.current.remove();
                mapInstanceRef.current = null;
            }
            clusterGroupRef.current = null;
            initializedRef.current = false;
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

                const descText = spot.description
                    ? `${spot.description.substring(0, 100)}${spot.description.length > 100 ? '...' : ''}`
                    : '';

                const popupContent = `
          <div class="text-center p-2" style="min-width: 200px;">
            <b class="text-lg">${escapeHtml(spot.name)}</b>
            ${spot.area ? `<br/><span class="text-xs text-gray-500">📍 ${escapeHtml(spot.area)}</span>` : ''}
            <br/><span class="text-xs text-gray-500">${escapeHtml(spot.category)}</span>
            ${spot.image ? `<br/><img src="${escapeHtml(spot.image)}" style="width:100%; height:100px; object-fit:cover; margin-top:5px; border-radius:4px;" />` : ''}
            ${spot.description ? `<br/><p class="text-xs text-gray-600 mt-1 text-left">${escapeHtml(descText)}</p>` : ''}
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

    }, [spots, status]);

    return (
        <div className="relative w-full rounded-2xl overflow-hidden shadow-inner border border-gray-200 z-0" style={{ height }}>
            <div ref={mapRef} className="w-full h-full" style={{ background: '#f0f0f0' }}></div>
            {status === 'loading' && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100/80">
                    <p>マップを読み込み中...</p>
                </div>
            )}
            {status === 'error' && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100/80">
                    <p>マップの読み込みに失敗しました。</p>
                </div>
            )}
        </div>
    );
};
