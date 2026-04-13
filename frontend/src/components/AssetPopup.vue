<template>
  <div v-if="asset" class="asset-popup">
    <div class="d-flex align-center mb-2">
      <v-icon :color="categoryColor" size="20" class="mr-2">{{ categoryIcon }}</v-icon>
      <span class="text-subtitle-2 font-weight-bold">{{ asset.name }}</span>
    </div>

    <v-chip :color="categoryColor" size="x-small" variant="tonal" class="mb-2">
      {{ categoryLabel }}
    </v-chip>
    <v-chip
      v-if="asset.is_headquarters"
      size="x-small"
      color="amber"
      variant="tonal"
      class="mb-2 ml-1"
    >
      HQ
    </v-chip>

    <div class="text-caption text-grey-darken-1 mb-1">
      <v-icon size="12" class="mr-1">mdi-map-marker</v-icon>{{ asset.address }}
    </div>

    <div v-if="asset.description" class="text-caption mb-2">{{ asset.description }}</div>

    <!-- Confidence bar -->
    <div class="d-flex align-center mb-2">
      <span class="text-caption mr-2">Confianza:</span>
      <v-progress-linear
        :model-value="asset.confidence_score * 100"
        :color="tierColor"
        height="6"
        rounded
        style="max-width: 120px"
      />
      <span class="text-caption ml-2 font-weight-medium">{{ (asset.confidence_score * 100).toFixed(0) }}%</span>
    </div>

    <!-- Tags -->
    <div v-if="asset.functional_tags?.length" class="mb-2">
      <v-chip
        v-for="tag in asset.functional_tags.slice(0, 4)"
        :key="tag"
        size="x-small"
        variant="outlined"
        class="mr-1 mb-1"
      >
        {{ tag }}
      </v-chip>
    </div>

    <!-- Google Maps link -->
    <a
      :href="`https://www.google.com/maps/place/?q=place_id:${asset.google_place_id}`"
      target="_blank"
      class="text-caption text-decoration-none"
    >
      <v-icon size="12" class="mr-1">mdi-open-in-new</v-icon>Ver en Google Maps
    </a>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Asset } from '@/types/types';
import { AssetCategory, CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS } from '@/types/types';

const props = defineProps<{ asset: Asset }>();

const categoryLabel = computed(() => CATEGORY_LABELS[props.asset.category as AssetCategory] || props.asset.category);
const categoryIcon = computed(() => CATEGORY_ICONS[props.asset.category as AssetCategory] || 'mdi-map-marker');
const categoryColor = computed(() => CATEGORY_COLORS[props.asset.category as AssetCategory] || '#9E9E9E');
const tierColor = computed(() => {
  if (props.asset.confidence_tier === 'HIGH') return 'green';
  if (props.asset.confidence_tier === 'MEDIUM') return 'orange';
  return 'red';
});
</script>

<style scoped>
.asset-popup {
  max-width: 280px;
  font-family: 'Montserrat', sans-serif;
}
</style>
