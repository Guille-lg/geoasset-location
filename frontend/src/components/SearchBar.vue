<template>
  <section class="search-page">
    <div class="hero-noise" />
    <div class="search-hero mx-auto">
      <h1 class="hero-title mb-4">Discover Industrial Assets with AI-Native Search</h1>
      <p class="hero-subtitle mb-8">
        Search any Spanish company and generate a structured, map-first intelligence brief in minutes.
      </p>

      <v-form class="hero-search" @submit.prevent="startAnalysis">
        <v-text-field
          v-model="searchText"
          clearable
          variant="plain"
          rounded="xl"
          placeholder="Search a company (e.g. Inditex, Repsol, Iberdrola)"
          hide-details
          class="search-input px-3"
          @keydown.enter.prevent="startAnalysis"
        >
          <template #append>
            <v-btn icon size="small" color="primary" class="submit-icon" :disabled="!canSubmit" @click="startAnalysis">
              <v-icon size="18">mdi-arrow-up</v-icon>
            </v-btn>
          </template>
        </v-text-field>
      </v-form>

      <div class="quick-picks mt-6">
        <v-chip
          v-for="example in examples"
          :key="example"
          class="ma-1"
          color="primary"
          variant="outlined"
          @click="quickSearch(example)"
        >
          {{ example }}
        </v-chip>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useAppStore } from '@/stores/store';

const store = useAppStore();
const searchText = ref('');
const examples = ['Mercadona', 'Inditex', 'Repsol', 'Telefónica', 'Iberdrola', 'BBVA'];

const canSubmit = computed(() => searchText.value.trim().length > 1);

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

const startAnalysis = () => {
  const name = searchText.value.trim();
  if (!name) return;
  store.setCompany({
    id: slugify(name) || 'company',
    name,
  });
  store.resetAnalysis();
  store.setView('processing');
};

const quickSearch = (name: string) => {
  searchText.value = name;
  startAnalysis();
};
</script>

<style scoped>
.search-page {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0;
  border: none;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.85) 0%,
    rgba(238, 246, 255, 0.9) 45%,
    rgba(233, 242, 255, 0.82) 100%
  );
  box-shadow: none;
  overflow: hidden;
}

.hero-noise {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 18%, rgba(89, 220, 225, 0.2), rgba(89, 220, 225, 0) 36%),
    radial-gradient(circle at 82% 10%, rgba(122, 149, 255, 0.22), rgba(122, 149, 255, 0) 36%),
    radial-gradient(circle at 50% 88%, rgba(73, 111, 234, 0.14), rgba(73, 111, 234, 0) 35%);
  pointer-events: none;
}

.search-hero {
  position: relative;
  z-index: 1;
  width: min(860px, 100%);
  padding: clamp(2.5rem, 8vh, 5.5rem) 1.25rem;
  text-align: center;
}

.announce-chip {
  background: rgba(44, 111, 255, 0.11);
  border: 1px solid rgba(44, 111, 255, 0.2);
  color: #274798;
  animation: riseIn 450ms ease-out both;
}

.hero-title {
  font-size: clamp(2.05rem, 5vw, 3.75rem);
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: #0a1834;
  font-weight: 700;
  animation: riseIn 520ms ease-out both;
}

.hero-subtitle {
  max-width: 640px;
  margin-inline: auto;
  color: #54668f;
  font-size: clamp(1rem, 2.4vw, 1.14rem);
  animation: riseIn 620ms ease-out both;
}

.hero-search {
  max-width: 760px;
  margin-inline: auto;
  border: 1px solid rgba(84, 124, 196, 0.24);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 16px 35px rgba(30, 71, 147, 0.12);
  animation: riseIn 730ms ease-out both;
}

:deep(.search-input .v-field) {
  border-radius: 18px;
  background: transparent;
  box-shadow: none;
  padding-inline: 8px;
}

:deep(.search-input .v-field__input) {
  min-height: 64px;
  font-size: 1.02rem;
  color: #102247;
}

.submit-icon {
  border-radius: 12px;
  width: 34px;
  height: 34px;
}

.quick-picks {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  animation: riseIn 820ms ease-out both;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  animation: riseIn 910ms ease-out both;
}

.hero-stat {
  border: 1px solid rgba(104, 132, 186, 0.25);
  border-radius: 14px;
  padding: 0.9rem;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  flex-direction: column;
}

.hero-stat-value {
  color: #112a5b;
  font-weight: 700;
}

.hero-stat-label {
  color: #6075a0;
  font-size: 0.78rem;
}

@keyframes riseIn {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .search-hero {
    padding: clamp(2rem, 6vh, 4rem) 1rem;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .search-page {
    min-height: 100dvh;
  }

  .search-hero {
    padding: 1.75rem 0.8rem;
  }
}
</style>
