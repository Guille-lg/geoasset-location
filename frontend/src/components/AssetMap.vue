<template>
  <div ref="mapContainer" class="map-container" style="width: 100%; height: 100%"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useAppStore } from '@/stores/store';
import type { Asset } from '@/types/types';
import { AssetCategory, CATEGORY_COLORS, CATEGORY_LABELS } from '@/types/types';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

const store = useAppStore();
const mapContainer = ref<HTMLElement | null>(null);

let map: L.Map | null = null;
let markerClusterGroup: L.MarkerClusterGroup | null = null;
let markersById: Record<string, L.Marker> = {};

const emit = defineEmits<{
  (e: 'marker-click', asset: Asset): void;
}>();

const SPAIN_CENTER: L.LatLngExpression = [40.0, -3.7];
const SPAIN_ZOOM = 6;

const TILE_LAYERS: Record<string, { url: string; attribution: string }> = {
  Callejero: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  Satélite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
  Topográfico: {
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap',
  },
};

// Source color palette — distinct from category colors so the map legend is unambiguous.
const SOURCE_COLORS: Record<string, string> = {
  maps_api: '#2c6fff',        // blue
  document_upload: '#10b7c8', // teal
  agent_search: '#8b5cf6',    // purple
};
const SOURCE_LABELS: Record<string, string> = {
  maps_api: 'Maps API',
  document_upload: 'Document',
  agent_search: 'Agent Search',
};

function resolveSourceColor(dataSources: string[]): string {
  // Priority: agent_search > document_upload > maps_api > fallback grey
  if (dataSources.includes('agent_search')) return SOURCE_COLORS.agent_search;
  if (dataSources.includes('document_upload')) return SOURCE_COLORS.document_upload;
  if (dataSources.includes('maps_api')) return SOURCE_COLORS.maps_api;
  return '#9E9E9E';
}

function createMarkerIcon(dataSources: string[], tier: string): L.DivIcon {
  const color = resolveSourceColor(dataSources);
  const opacity = tier === 'LOW' ? '0.55' : '1';
  const size = tier === 'HIGH' ? 14 : 10;
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};opacity:${opacity};
      border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [size + 4, size + 4],
    iconAnchor: [(size + 4) / 2, (size + 4) / 2],
  });
}

function buildPopupContent(asset: Asset): string {
  const catLabel = CATEGORY_LABELS[asset.category as AssetCategory] || asset.category;
  const color = CATEGORY_COLORS[asset.category as AssetCategory] || '#9E9E9E';
  const confPct = (asset.confidence_score * 100).toFixed(0);
  const tierColor =
    asset.confidence_tier === 'HIGH' ? '#4CAF50' : asset.confidence_tier === 'MEDIUM' ? '#FF9800' : '#F44336';
  const tags = (asset.functional_tags || [])
    .slice(0, 4)
    .map(
      (t) =>
        `<span style="display:inline-block;padding:2px 8px;margin:2px;border:1px solid rgba(88,114,160,0.3);border-radius:999px;font-size:10px;color:#4f648e;background:rgba(236,243,255,0.9);">${t}</span>`,
    )
    .join('');
  const hqBadge = asset.is_headquarters
    ? '<span style="display:inline-block;padding:2px 8px;margin-left:6px;background:#fef4cc;color:#8c6a00;border-radius:999px;font-size:10px;font-weight:600;">HQ</span>'
    : '';

  const sourceChipStyles: Record<string, string> = {
    maps_api:        'background:rgba(44,111,255,0.12);color:#2c6fff;',
    document_upload: 'background:rgba(16,183,200,0.12);color:#0e8e9c;',
    agent_search:    'background:rgba(139,92,246,0.12);color:#8b5cf6;',
  };
  const sourceChips = (asset.data_sources || [])
    .filter((src: string) => !src.includes('inference'))
    .map((src: string) => {
      const style = sourceChipStyles[src] || 'background:rgba(100,100,100,0.1);color:#666;';
      const label = SOURCE_LABELS[src] || src;
      return `<span style="display:inline-block;padding:2px 8px;margin:2px;${style}border-radius:999px;font-size:9px;font-weight:600;">${label}</span>`;
    })
    .join('');

  return `
    <div style="max-width:272px;font-family:'Sora',sans-serif;font-size:13px;color:#1b2e55;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;">
        <div style="font-weight:700;line-height:1.3;">${asset.name}</div>
        ${hqBadge}
      </div>
      <div style="display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin-bottom:8px;">
        <span style="display:inline-block;padding:2px 9px;background:${color};color:white;border-radius:999px;font-size:10px;font-weight:600;">${catLabel}</span>
        ${sourceChips}
      </div>
      <div style="color:#5f739f;font-size:11px;margin-bottom:6px;line-height:1.45;">${asset.address}</div>
      ${asset.description ? `<div style="font-size:11px;margin-bottom:6px;color:#42567f;line-height:1.4;">${asset.description}</div>` : ''}
      <div style="display:flex;align-items:center;margin-bottom:8px;">
        <span style="font-size:11px;margin-right:6px;color:#54668f;">Confianza:</span>
        <div style="flex:1;height:7px;background:#e7eefb;border-radius:6px;max-width:110px;">
          <div style="height:7px;border-radius:6px;background:${tierColor};width:${confPct}%;"></div>
        </div>
        <span style="font-size:11px;margin-left:6px;font-weight:700;color:#1f3460;">${confPct}%</span>
      </div>
      ${tags ? `<div style="margin-bottom:4px;">${tags}</div>` : ''}
      <a href="https://www.google.com/maps/place/?q=place_id:${asset.google_place_id}" target="_blank" style="font-size:11px;color:#2b61da;text-decoration:none;font-weight:600;">Ver en Google Maps ↗</a>
    </div>
  `;
}

function addMarkers() {
  if (!map) return;

  if (markerClusterGroup) {
    map.removeLayer(markerClusterGroup);
  }

  markerClusterGroup = L.markerClusterGroup({
    disableClusteringAtZoom: store.clusteringEnabled ? undefined : 1,
    maxClusterRadius: store.clusteringEnabled ? 50 : 0,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
  });

  markersById = {};
  const assets = store.filteredAssets;

  for (const asset of assets) {
    const marker = L.marker([asset.latitude, asset.longitude], {
      icon: createMarkerIcon(asset.data_sources || [], asset.confidence_tier),
    });
    marker.bindPopup(buildPopupContent(asset), { maxWidth: 280 });
    marker.on('click', () => {
      store.selectAsset(asset.id);
      emit('marker-click', asset);
    });
    markerClusterGroup.addLayer(marker);
    markersById[asset.id] = marker;
  }

  map.addLayer(markerClusterGroup);

  if (assets.length > 0) {
    const group = L.featureGroup(Object.values(markersById));
    map.fitBounds(group.getBounds().pad(0.1));
  }
}

function flyToAsset(asset: Asset) {
  if (!map) return;
  map.flyTo([asset.latitude, asset.longitude], 14, { duration: 1 });
  const marker = markersById[asset.id];
  if (marker) {
    setTimeout(() => marker.openPopup(), 500);
  }
}

defineExpose({ flyToAsset });

onMounted(() => {
  if (!mapContainer.value) return;

  map = L.map(mapContainer.value, {
    center: SPAIN_CENTER,
    zoom: SPAIN_ZOOM,
    zoomControl: true,
  });

  const baseLayers: Record<string, L.TileLayer> = {};
  let first = true;
  for (const [name, cfg] of Object.entries(TILE_LAYERS)) {
    const layer = L.tileLayer(cfg.url, { attribution: cfg.attribution });
    baseLayers[name] = layer;
    if (first) {
      layer.addTo(map);
      first = false;
    }
  }

  L.control.layers(baseLayers).addTo(map);

  // Source legend
  const legend = new (L.Control.extend({
    options: { position: 'bottomright' },
    onAdd() {
      const div = L.DomUtil.create('div', 'source-legend');
      div.innerHTML = Object.entries(SOURCE_COLORS)
        .map(
          ([key, color]) =>
            `<div class="source-legend-row">
              <span class="source-legend-dot" style="background:${color}"></span>
              <span>${SOURCE_LABELS[key]}</span>
            </div>`,
        )
        .join('');
      return div;
    },
  }))();
  legend.addTo(map);

  nextTick(() => addMarkers());
});

watch(
  () => [store.filteredAssets, store.clusteringEnabled],
  () => {
    addMarkers();
  },
  { deep: true },
);

watch(
  () => store.selectedAssetId,
  (newId) => {
    if (newId) {
      const asset = store.assets.find((a) => a.id === newId);
      if (asset) flyToAsset(asset);
    }
  },
);

onUnmounted(() => {
  if (map) {
    map.remove();
    map = null;
  }
});
</script>

<style>
.map-container {
  z-index: 0;
}

.custom-marker {
  background: transparent !important;
  border: none !important;
}

.leaflet-popup-content-wrapper,
.leaflet-popup-tip {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(116, 145, 196, 0.32);
  box-shadow: 0 16px 36px rgba(22, 57, 124, 0.16);
}

.leaflet-popup-content {
  margin: 12px 12px 10px;
}

.leaflet-container a.leaflet-popup-close-button {
  color: #4d6696;
}

.leaflet-control-zoom,
.leaflet-control-layers {
  border: 1px solid rgba(108, 141, 200, 0.28) !important;
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: 0 14px 26px rgba(19, 52, 118, 0.12);
}

.leaflet-control-zoom a,
.leaflet-control-layers-toggle,
.leaflet-control-layers-expanded {
  background: rgba(255, 255, 255, 0.94) !important;
  color: #223a69 !important;
}

.source-legend {
  background: rgba(255, 255, 255, 0.93);
  border: 1px solid rgba(108, 141, 200, 0.28);
  border-radius: 12px;
  padding: 0.55rem 0.8rem;
  box-shadow: 0 8px 20px rgba(19, 52, 118, 0.1);
  font-family: 'Sora', sans-serif;
  font-size: 11px;
  color: #223a69;
  min-width: 120px;
}

.source-legend-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 2px 0;
}

.source-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1.5px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
</style>
