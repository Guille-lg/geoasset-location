<template>
  <section class="search-page">
    <div class="hero-noise" />
    <div class="search-hero mx-auto">
      <h1 class="hero-title mb-4">Discover Industrial Assets with AI-Native Search</h1>
      <p class="hero-subtitle mb-8">
        Search any Spanish company and generate a structured, map-first intelligence brief in minutes.
      </p>

      <v-form class="hero-search" @submit.prevent="startAnalysis">
        <!-- File cards above the input -->
        <div v-if="store.uploadedFiles.length" class="file-cards-row">
          <div v-for="(file, idx) in store.uploadedFiles" :key="idx" class="file-card">
            <div class="file-card__info">
              <span class="file-card__name">{{ file.name }}</span>
              <span class="file-card__size">{{ formatFileSize(file.size) }}</span>
            </div>
            <button class="file-card__remove" @click.stop="store.removeUploadedFile(idx)" aria-label="Remove file">
              <v-icon size="12">mdi-close</v-icon>
            </button>
          </div>
        </div>

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
          <template #prepend-inner>
            <v-btn
              icon
              size="small"
              variant="text"
              class="upload-trigger"
              aria-label="Upload files"
              @click="openFilePicker"
            >
              <v-icon size="18">mdi-plus</v-icon>
            </v-btn>
          </template>

          <template #append>
            <div class="search-actions">
              <v-tooltip :text="store.agentMode ? 'Agentic search ON' : 'Enable agentic search'" location="top">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    v-bind="tooltipProps"
                    icon
                    size="small"
                    :variant="store.agentMode ? 'flat' : 'text'"
                    :color="store.agentMode ? 'deep-purple' : 'default'"
                    class="agent-toggle"
                    :class="{ 'agent-toggle--active': store.agentMode }"
                    aria-label="Toggle agentic search"
                    @click="store.toggleAgentMode()"
                  >
                    <v-icon size="18">mdi-robot-outline</v-icon>
                  </v-btn>
                </template>
              </v-tooltip>
              <v-btn icon size="small" color="primary" class="submit-icon" :disabled="!canSubmit" @click="startAnalysis">
                <v-icon size="18">mdi-arrow-up</v-icon>
              </v-btn>
            </div>
          </template>
        </v-text-field>

        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf,.docx,.pptx"
          multiple
          class="upload-input-hidden"
          @change="onFileInputChange"
        />

        <div v-if="uploadError" class="upload-error-inline px-4 pb-3">{{ uploadError }}</div>
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
const uploadError = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);
const examples = ['Mercadona', 'Inditex', 'Repsol', 'Telefónica', 'Iberdrola', 'BBVA'];
const MAX_UPLOAD_MB = 25;
const ALLOWED_EXTENSIONS = new Set(['pdf', 'docx', 'pptx']);

const hasText = computed(() => searchText.value.trim().length > 1);
const hasFiles = computed(() => store.uploadedFiles.length > 0);
const canSubmit = computed(() => hasText.value || hasFiles.value);

const slugify = (value: string): string =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const startAnalysis = () => {
  if (!canSubmit.value) return;

  const name = searchText.value.trim();
  const companyName = name || store.uploadedFiles[0]?.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim() || 'Uploaded Document';

  store.setCompany({
    id: slugify(companyName) || 'company',
    name: companyName,
  });

  if (hasText.value && hasFiles.value) {
    store.setAnalysisMode('combined');
  } else if (hasFiles.value) {
    store.setAnalysisMode('document');
  } else {
    store.setAnalysisMode('search');
  }

  store.pipelineSteps = [];
  store.assets = [];
  store.metadata = null;
  store.selectedAssetId = null;
  store.filterCategory = null;
  store.filterMinConfidence = 0;
  store.filterSource = null;
  store.clearAgentEvents();
  store.agentFiles = [];
  store.agentSessionId = null;

  // If agent mode is enabled, go to agent view first; pipelines start after.
  store.setView(store.agentMode ? 'agent' : 'processing');
};

const openFilePicker = () => {
  uploadError.value = '';
  fileInputRef.value?.click();
};

const validateFile = (file: File): boolean => {
  const ext = file.name.split('.').pop()?.toLowerCase() || '';
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    uploadError.value = 'Unsupported format. Please upload PDF, DOCX, or PPTX.';
    return false;
  }
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    uploadError.value = `File is too large. Max size is ${MAX_UPLOAD_MB} MB.`;
    return false;
  }
  uploadError.value = '';
  return true;
};

const onFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files) return;
  for (const file of Array.from(target.files)) {
    if (validateFile(file)) {
      store.addUploadedFile(file);
    }
  }
  target.value = '';
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

.search-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding-right: 2px;
}

.agent-toggle {
  border-radius: 999px;
  transition: box-shadow 200ms, background 200ms;
}

.agent-toggle--active {
  box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.25);
  animation: agentPulse 2s ease-in-out infinite;
}

@keyframes agentPulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.25); }
  50%       { box-shadow: 0 0 0 6px rgba(124, 58, 237, 0.1); }
}

.upload-trigger {
  border-radius: 999px;
  color: #4b5f8f;
}

.upload-input-hidden {
  display: none;
}

.upload-error-inline {
  font-size: 0.78rem;
  color: #ba1d3f;
  text-align: left;
}

.file-cards-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  padding: 0.6rem 0.75rem 0;
}

.file-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  max-width: 5vw;
  min-width: 90px;
  padding: 0.35rem 0.55rem;
  border-radius: 12px;
  border: 1px solid rgba(84, 124, 196, 0.22);
  background: rgba(236, 243, 255, 0.85);
}

.file-card__info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
  min-width: 0;
}

.file-card__name {
  font-size: 0.7rem;
  font-weight: 600;
  color: #173671;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.file-card__size {
  font-size: 0.6rem;
  color: #7b8caf;
  line-height: 1.2;
}

.file-card__remove {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: none;
  background: rgba(186, 29, 63, 0.1);
  color: #ba1d3f;
  cursor: pointer;
  transition: background 200ms;
}

.file-card__remove:hover {
  background: rgba(186, 29, 63, 0.22);
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
