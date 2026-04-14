<template>
  <div class="sidebar d-flex flex-column" style="height: 100%">
    <!-- Company header -->
    <div class="pa-4 sidebar-header">
      <div class="d-flex align-center mb-2">
        <v-icon color="primary" class="mr-2">mdi-domain</v-icon>
        <span class="text-subtitle-1 font-weight-bold company-name">
          {{ store.metadata?.company?.name || store.selectedCompany?.name || 'Empresa' }}
        </span>
      </div>
      <div v-if="store.metadata" class="d-flex flex-wrap ga-2">
        <v-chip size="x-small" color="primary" variant="tonal"> {{ store.metadata.total_assets }} activos </v-chip>
        <v-chip v-if="store.metadata.high_confidence" size="x-small" color="green" variant="tonal">
          {{ store.metadata.high_confidence }} alta conf.
        </v-chip>
        <v-chip v-if="store.metadata.low_confidence" size="x-small" color="orange" variant="tonal">
          {{ store.metadata.low_confidence }} baja conf.
        </v-chip>
      </div>
    </div>

    <!-- Filters -->
    <div class="pa-3 sidebar-filters">
      <v-text-field
        v-model="searchText"
        density="compact"
        variant="outlined"
        placeholder="Buscar activo..."
        prepend-inner-icon="mdi-magnify"
        hide-details
        class="mb-2"
      />
      <v-select
        v-model="store.filterCategory"
        :items="categoryOptions"
        item-title="label"
        item-value="value"
        density="compact"
        variant="outlined"
        placeholder="Categoría"
        clearable
        hide-details
        class="mb-2"
      />
      <div class="d-flex align-center">
        <span class="text-caption confidence-label mr-2">Confianza mín:</span>
        <v-slider
          v-model="store.filterMinConfidence"
          :min="0"
          :max="1"
          :step="0.05"
          density="compact"
          hide-details
          thumb-label
          color="primary"
        />
      </div>
      <div v-if="Object.keys(store.sourceCounts).length > 1" class="d-flex flex-wrap ga-1 mt-2">
        <v-chip
          size="x-small"
          :variant="store.filterSource === null ? 'flat' : 'outlined'"
          color="primary"
          @click="store.filterSource = null"
        >
          All
        </v-chip>
        <v-chip
          v-if="store.sourceCounts['maps_api']"
          size="x-small"
          :variant="store.filterSource === 'maps_api' ? 'flat' : 'outlined'"
          color="blue"
          @click="store.filterSource = store.filterSource === 'maps_api' ? null : 'maps_api'"
        >
          <v-icon start size="12">mdi-google-maps</v-icon>
          Maps API ({{ store.sourceCounts['maps_api'] }})
        </v-chip>
        <v-chip
          v-if="store.sourceCounts['document_upload']"
          size="x-small"
          :variant="store.filterSource === 'document_upload' ? 'flat' : 'outlined'"
          color="teal"
          @click="store.filterSource = store.filterSource === 'document_upload' ? null : 'document_upload'"
        >
          <v-icon start size="12">mdi-file-document-outline</v-icon>
          Document ({{ store.sourceCounts['document_upload'] }})
        </v-chip>
        <v-chip
          v-if="store.sourceCounts['agent_search']"
          size="x-small"
          :variant="store.filterSource === 'agent_search' ? 'flat' : 'outlined'"
          color="deep-purple"
          @click="store.filterSource = store.filterSource === 'agent_search' ? null : 'agent_search'"
        >
          <v-icon start size="12">mdi-robot-outline</v-icon>
          Agent ({{ store.sourceCounts['agent_search'] }})
        </v-chip>
      </div>
    </div>

    <!-- Asset list -->
    <v-list class="flex-grow-1 overflow-y-auto sidebar-list" density="compact">
      <v-list-item
        v-for="asset in displayedAssets"
        :key="asset.id"
        :class="{ 'selected-asset': store.selectedAssetId === asset.id }"
        @click="onAssetClick(asset)"
      >
        <template #prepend>
          <v-icon :color="getCategoryColor(asset.category)" size="20">
            {{ getCategoryIcon(asset.category) }}
          </v-icon>
        </template>
        <v-list-item-title class="text-body-2 asset-title">{{ asset.name }}</v-list-item-title>
        <v-list-item-subtitle class="text-caption asset-subtitle">
          {{ asset.municipality || asset.address?.split(',')[0] }}
        </v-list-item-subtitle>
        <template #append>
          <div class="d-flex align-center ga-1">
            <v-chip
              v-for="src in (asset.data_sources || []).filter(s => !s.includes('inference'))"
              :key="src"
              size="x-small"
              :color="src === 'maps_api' ? 'blue' : src === 'document_upload' ? 'teal' : src === 'agent_search' ? 'deep-purple' : 'grey'"
              variant="tonal"
              class="source-chip"
            >
              <v-icon size="10">{{ src === 'maps_api' ? 'mdi-google-maps' : src === 'agent_search' ? 'mdi-robot-outline' : 'mdi-file-document-outline' }}</v-icon>
            </v-chip>
            <v-chip :color="getTierColor(asset.confidence_tier)" size="x-small" variant="tonal">
              {{ (asset.confidence_score * 100).toFixed(0) }}%
            </v-chip>
          </div>
        </template>
      </v-list-item>

      <v-list-item v-if="displayedAssets.length === 0">
        <v-list-item-title class="text-body-2 empty-list text-center"> No se encontraron activos </v-list-item-title>
      </v-list-item>
    </v-list>

    <!-- Footer actions -->
    <div class="pa-3 sidebar-footer d-flex ga-2">
      <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-download" @click="exportCSV"> CSV </v-btn>
      <v-spacer />
      <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-arrow-left" @click="backToSearch">
        Nueva búsqueda
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useAppStore } from '@/stores/store';
import type { Asset } from '@/types/types';
import { AssetCategory, CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS } from '@/types/types';

const store = useAppStore();
const searchText = ref('');

const emit = defineEmits<{
  (e: 'select-asset', asset: Asset): void;
}>();

const categoryOptions = computed(() => {
  const cats = Object.values(AssetCategory);
  return cats
    .filter((c) => store.categoryCounts[c])
    .map((c) => ({
      value: c,
      label: `${CATEGORY_LABELS[c]} (${store.categoryCounts[c] || 0})`,
    }));
});

const displayedAssets = computed(() => {
  let result = store.filteredAssets;
  if (searchText.value) {
    const q = searchText.value.toLowerCase();
    result = result.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.address.toLowerCase().includes(q) ||
        a.municipality?.toLowerCase().includes(q),
    );
  }
  return result;
});

const getCategoryColor = (cat: string) => CATEGORY_COLORS[cat as AssetCategory] || '#9E9E9E';
const getCategoryIcon = (cat: string) => CATEGORY_ICONS[cat as AssetCategory] || 'mdi-map-marker';
const getTierColor = (tier: string) => {
  if (tier === 'HIGH') return 'green';
  if (tier === 'MEDIUM') return 'orange';
  return 'red';
};

const onAssetClick = (asset: Asset) => {
  store.selectAsset(asset.id);
  emit('select-asset', asset);
};

const exportCSV = () => {
  const rows = [['Nombre', 'Categoría', 'Dirección', 'Municipio', 'Provincia', 'Confianza', 'Lat', 'Lon']];
  for (const a of store.filteredAssets) {
    rows.push([
      a.name,
      a.category,
      a.address,
      a.municipality,
      a.province,
      String(a.confidence_score),
      String(a.latitude),
      String(a.longitude),
    ]);
  }
  const csv = rows.map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${store.selectedCompany?.name || 'assets'}_geoassets.csv`;
  a.click();
  URL.revokeObjectURL(url);
};

const backToSearch = () => {
  store.resetAnalysis();
  store.setView('search');
};
</script>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
}

.sidebar-header {
  border-bottom: 1px solid rgba(118, 148, 203, 0.2);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(244, 250, 255, 0.92));
}

.company-name {
  color: #112146;
}

.sidebar-filters {
  border-bottom: 1px solid rgba(118, 148, 203, 0.2);
  background: rgba(248, 251, 255, 0.95);
}

.confidence-label {
  color: #58709d;
}

.sidebar-list {
  background: transparent;
}

:deep(.sidebar-list .v-list-item) {
  margin: 0.2rem 0.45rem;
  border-radius: 12px;
  border: 1px solid rgba(112, 145, 203, 0.16);
  background: rgba(255, 255, 255, 0.75);
}

.selected-asset {
  background: rgba(44, 111, 255, 0.1) !important;
  border-color: rgba(44, 111, 255, 0.32) !important;
}

.asset-title {
  color: #12254d;
  font-weight: 600;
}

.asset-subtitle {
  color: #6a7fa7;
}

.empty-list {
  color: #788db1;
}

.source-chip {
  min-width: 0;
  padding: 0 4px !important;
}

.sidebar-footer {
  border-top: 1px solid rgba(118, 148, 203, 0.2);
  background: rgba(249, 252, 255, 0.94);
}
</style>
