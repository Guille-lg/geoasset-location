<template>
  <v-app>
    <v-layout class="app-shell">
      <Header />
      <v-main :class="['app-main', { 'app-main--fullbleed': store.currentView === 'search' || store.currentView === 'processing' }]">
        <SearchBar v-if="store.currentView === 'search'" />
        <ProcessingView v-else-if="store.currentView === 'processing'" />
        <section v-else-if="store.currentView === 'results'" class="results-view">
          <div class="results-grid">
            <div class="results-sidebar">
              <AssetSidebar @select-asset="onSelectAsset" />
            </div>
            <div class="results-map">
              <AssetMap ref="assetMapRef" />
            </div>
          </div>
        </section>
      </v-main>
    </v-layout>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useAppStore } from '@/stores/store';
import Header from '@/components/Header.vue';
import SearchBar from '@/components/SearchBar.vue';
import ProcessingView from '@/components/ProcessingView.vue';
import AssetSidebar from '@/components/AssetSidebar.vue';
import AssetMap from '@/components/AssetMap.vue';
import type { Asset } from '@/types/types';

const store = useAppStore();
const assetMapRef = ref<InstanceType<typeof AssetMap> | null>(null);

const onSelectAsset = (asset: Asset) => {
  assetMapRef.value?.flyToAsset(asset);
};
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap');

html,
body {
  font-family: 'Sora', sans-serif;
  color: #0e1a37;
  background:
    radial-gradient(circle at 15% 10%, #e4fbff 0%, rgba(228, 251, 255, 0) 40%),
    radial-gradient(circle at 85% 0%, #e2e9ff 0%, rgba(226, 233, 255, 0) 45%),
    linear-gradient(180deg, #f7faff 0%, #edf3ff 100%);
}

html {
  overflow-y: auto;
}

#app {
  min-height: 100vh;
}

.app-shell {
  --topbar-height: 64px;
  min-height: 100vh;
}

.app-main {
  min-height: 100vh;
  padding: 1.25rem;
  padding-top: 1rem;
  background: transparent;
}

.app-main--fullbleed {
  padding: 0;
  margin-top: calc(var(--topbar-height) * -1);
}

.app-main--fullbleed .search-page,
.app-main--fullbleed .processing-page {
  box-sizing: border-box;
  padding-top: var(--topbar-height);
}

.results-view {
  height: calc(100vh - 88px);
}

.results-grid {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 1rem;
  height: 100%;
}

.results-sidebar,
.results-map {
  border: 1px solid rgba(78, 112, 177, 0.2);
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 20px 48px rgba(20, 53, 117, 0.08);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
}

@media (max-width: 1100px) {
  .results-view {
    height: auto;
  }

  .results-grid {
    grid-template-columns: 1fr;
    grid-auto-rows: minmax(420px, auto);
  }

  .results-sidebar {
    min-height: 420px;
  }

  .results-map {
    min-height: 540px;
  }
}
</style>
