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
            <div class="search-actions">
              <v-menu v-model="uploadMenuOpen" :close-on-content-click="false" location="bottom end" offset="10">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon
                    size="small"
                    variant="text"
                    class="upload-trigger"
                    aria-label="Open upload dialog"
                  >
                    <v-icon size="18">mdi-plus</v-icon>
                  </v-btn>
                </template>

                <v-card class="upload-dialog" elevation="8">
                  <div class="upload-dialog__title">Add files</div>
                  <div class="upload-dialog__subtitle">Upload a company report to extract productive assets.</div>

                  <v-text-field
                    v-model="documentCompanyName"
                    variant="outlined"
                    density="comfortable"
                    hide-details
                    class="mt-3"
                    label="Optional company name"
                  />

                  <div class="upload-dialog__meta mt-2">Accepted: PDF, DOCX, PPTX · Max {{ maxUploadLabel }}</div>

                  <input
                    ref="fileInputRef"
                    type="file"
                    accept=".pdf,.docx,.pptx"
                    class="upload-dialog__input"
                    @change="onFileInputChange"
                  />

                  <div class="upload-dialog__actions mt-4">
                    <v-btn variant="outlined" color="primary" size="small" @click="openFilePicker">
                      Choose file
                    </v-btn>
                    <span v-if="selectedFileName" class="upload-dialog__filename">{{ selectedFileName }}</span>
                  </div>

                  <div v-if="uploadError" class="upload-dialog__error mt-3">{{ uploadError }}</div>
                </v-card>
              </v-menu>

              <v-btn icon size="small" color="primary" class="submit-icon" :disabled="!canSubmit" @click="startAnalysis">
                <v-icon size="18">mdi-arrow-up</v-icon>
              </v-btn>
            </div>
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
const documentCompanyName = ref('');
const selectedFileName = ref('');
const uploadError = ref('');
const uploadMenuOpen = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const examples = ['Mercadona', 'Inditex', 'Repsol', 'Telefónica', 'Iberdrola', 'BBVA'];
const MAX_UPLOAD_MB = 25;
const ALLOWED_EXTENSIONS = new Set(['pdf', 'docx', 'pptx']);

const canSubmit = computed(() => searchText.value.trim().length > 1);
const maxUploadLabel = computed(() => `${MAX_UPLOAD_MB} MB`);

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
  store.setAnalysisMode('search');
  store.resetAnalysis();
  store.setView('processing');
};

const openFilePicker = () => {
  uploadError.value = '';
  fileInputRef.value?.click();
};

const parseFileNameToCompany = (fileName: string): string => fileName.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim();

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

const startDocumentAnalysis = (file: File) => {
  if (!validateFile(file)) return;

  selectedFileName.value = file.name;
  const companyName = documentCompanyName.value.trim() || parseFileNameToCompany(file.name) || 'Uploaded Document';

  store.setCompany({
    id: `doc_${slugify(companyName) || 'company'}`,
    name: companyName,
  });
  store.setAnalysisMode('document');
  store.resetAnalysis();
  store.setUploadedFile(file);
  uploadMenuOpen.value = false;
  store.setView('processing');
};

const onFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  startDocumentAnalysis(file);
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
}

.upload-trigger {
  border-radius: 999px;
  color: #4b5f8f;
}

.upload-dialog {
  width: min(360px, 92vw);
  border-radius: 16px;
  border: 1px solid rgba(87, 110, 156, 0.2);
  background: rgba(255, 255, 255, 0.98);
  padding: 0.95rem;
}

.upload-dialog__title {
  font-weight: 700;
  color: #152a54;
}

.upload-dialog__subtitle {
  margin-top: 0.3rem;
  font-size: 0.82rem;
  color: #63759c;
}

.upload-dialog__meta {
  font-size: 0.76rem;
  color: #7b8caf;
}

.upload-dialog__input {
  display: none;
}

.upload-dialog__actions {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.upload-dialog__filename {
  font-size: 0.8rem;
  color: #173671;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-dialog__error {
  font-size: 0.78rem;
  color: #ba1d3f;
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
