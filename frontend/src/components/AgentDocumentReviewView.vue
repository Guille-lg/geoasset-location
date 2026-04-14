<template>
  <section class="agent-review-page">
    <div class="review-noise" />

    <div class="review-content">
      <header class="review-header">
        <div>
          <h2 class="review-title">Validate found documents</h2>
          <p class="review-subtitle">
            Keep the relevant files and drop anything non-usable before pipeline analysis.
          </p>
        </div>
        <div class="review-stats">
          <span>{{ selectedCount }} selected</span>
          <span>{{ droppedCount }} dropped</span>
        </div>
      </header>

      <div v-if="docs.length === 0" class="review-empty">
        No agent documents found. Continuing with available inputs.
      </div>

      <div v-else class="docs-grid">
        <article
          v-for="doc in docs"
          :key="doc.filename"
          class="doc-card"
          :class="{ 'doc-card--dropped': !doc.selected }"
          @click="openPreview(doc)"
        >
          <div class="doc-preview">
            <iframe
              v-if="doc.extension === '.pdf'"
              :src="getPreviewUrl(doc)"
              title="Document preview"
              class="doc-preview-frame"
            />
            <div v-else class="doc-preview-fallback">
              <v-icon size="34" color="#5f7299">mdi-file-document-outline</v-icon>
              <span>Preview unavailable for {{ doc.extension || 'this file type' }}</span>
            </div>
          </div>

          <div class="doc-meta">
            <div class="doc-meta-text">
              <h3>{{ doc.filename }}</h3>
              <p>
                Weight {{ formatSize(doc.size) }}
                <span class="dot">•</span>
                {{ pageLabel(doc.page_count) }}
              </p>
            </div>
            <button
              class="drop-btn"
              :class="{ 'drop-btn--dropped': !doc.selected }"
              @click.stop="toggleDocument(doc)"
            >
              {{ doc.selected ? 'Drop' : 'Keep' }}
            </button>
          </div>
        </article>
      </div>

      <div class="review-actions">
        <button class="action-btn action-btn--ghost" @click="backToSearch">Back</button>
        <button class="action-btn action-btn--primary" :disabled="selectedCount === 0" @click="continueToAnalysis">
          Continue with {{ selectedCount }} document{{ selectedCount === 1 ? '' : 's' }}
        </button>
      </div>
    </div>

    <v-dialog v-model="previewOpen" max-width="1100" content-class="review-dialog" :scrim="true">
      <div v-if="activeDoc" class="viewer-shell">
        <header class="viewer-header">
          <div>
            <h3>{{ activeDoc.filename }}</h3>
            <p>{{ pageLabel(activeDoc.page_count) }}</p>
          </div>
          <button class="viewer-close" @click="previewOpen = false">
            <v-icon size="18">mdi-close</v-icon>
          </button>
        </header>

        <div class="viewer-body">
          <div class="viewer-controls">
            <button :disabled="!isPdfActive || page <= 1" @click="page--">Prev</button>
            <span>Page {{ page }}</span>
            <button :disabled="!isPdfActive || !maxPage || page >= maxPage" @click="page++">Next</button>
            <label>
              Zoom
              <input v-model.number="zoom" type="range" min="75" max="175" step="5">
            </label>
          </div>

          <div class="viewer-frame-wrap">
            <iframe
              v-if="activeDoc.extension === '.pdf'"
              :src="viewerUrl"
              class="viewer-frame"
              title="Full document preview"
            />
            <div v-else class="viewer-fallback">
              <v-icon size="48" color="#5f7299">mdi-file-document-outline</v-icon>
              <p>Inline rendering is only available for PDF files in-browser.</p>
              <a :href="getDocumentUrl(activeDoc)" target="_blank" rel="noopener noreferrer">Open document</a>
            </div>
          </div>
        </div>
      </div>
    </v-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAppStore } from '@/stores/store';
import {
  getAgentDocumentMetadata,
  getAgentSessionDocumentUrl,
} from '@/services/backend';
import type { AgentFile } from '@/types/types';

interface ReviewAgentFile extends AgentFile {
  selected: boolean
}

const store = useAppStore();
const docs = ref<ReviewAgentFile[]>([]);
const previewOpen = ref(false);
const activeDoc = ref<ReviewAgentFile | null>(null);
const page = ref(1);
const zoom = ref(110);

const selectedCount = computed(() => docs.value.filter((d) => d.selected).length);
const droppedCount = computed(() => docs.value.length - selectedCount.value);
const maxPage = computed(() => activeDoc.value?.page_count ?? null);
const isPdfActive = computed(() => activeDoc.value?.extension === '.pdf');

const viewerUrl = computed(() => {
  if (!activeDoc.value) return '';
  const base = getDocumentUrl(activeDoc.value);
  if (!isPdfActive.value) return base;
  return `${base}#page=${page.value}&zoom=${zoom.value}&toolbar=1&navpanes=0`;
});

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const pageLabel = (pageCount?: number | null): string => {
  if (!pageCount) return 'Pages unavailable';
  return `${pageCount} page${pageCount === 1 ? '' : 's'}`;
};

const getDocumentUrl = (doc: AgentFile): string =>
  getAgentSessionDocumentUrl(doc.session_id, doc.filename);

const getPreviewUrl = (doc: AgentFile): string =>
  `${getDocumentUrl(doc)}#page=1&zoom=page-fit&toolbar=0&navpanes=0&scrollbar=0`;

const openPreview = (doc: ReviewAgentFile) => {
  activeDoc.value = doc;
  page.value = 1;
  zoom.value = 110;
  previewOpen.value = true;
};

const toggleDocument = (doc: ReviewAgentFile) => {
  doc.selected = !doc.selected;
};

const continueToAnalysis = () => {
  const selected = docs.value
    .filter((d) => d.selected)
    .map((d) => ({
      filename: d.filename,
      size: d.size,
      url: d.url,
      relevance_reason: d.relevance_reason,
      session_id: d.session_id,
      extension: d.extension,
      page_count: d.page_count,
    }));

  const hasSearch = !!store.selectedCompany?.name;
  const hasDocs = selected.length > 0 || store.uploadedFiles.length > 0;
  if (hasSearch && hasDocs) {
    store.setAnalysisMode('combined');
  } else if (hasDocs) {
    store.setAnalysisMode('document');
  } else {
    store.setAnalysisMode('search');
  }

  store.setAgentFiles(selected);
  store.setView('processing');
};

const backToSearch = () => {
  store.setView('search');
};

onMounted(async () => {
  if (store.agentFiles.length === 0) {
    store.setView('processing');
    return;
  }

  docs.value = store.agentFiles.map((file) => ({ ...file, selected: true }));

  await Promise.all(
    docs.value.map(async (doc) => {
      try {
        const metadata = await getAgentDocumentMetadata(doc.session_id, doc.filename);
        doc.page_count = metadata.page_count;
        doc.extension = metadata.extension || doc.extension;
      } catch {
        const dotIndex = doc.filename.lastIndexOf('.');
        doc.extension = doc.extension || (dotIndex >= 0 ? doc.filename.slice(dotIndex).toLowerCase() : '');
      }
    }),
  );
});
</script>

<style scoped>
.agent-review-page {
  position: relative;
  min-height: 100dvh;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.85) 0%, rgba(238, 246, 255, 0.9) 45%, rgba(233, 242, 255, 0.82) 100%);
}

.review-noise {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 18%, rgba(89, 220, 225, 0.2), rgba(89, 220, 225, 0) 36%),
    radial-gradient(circle at 82% 10%, rgba(122, 149, 255, 0.22), rgba(122, 149, 255, 0) 36%),
    radial-gradient(circle at 50% 88%, rgba(73, 111, 234, 0.14), rgba(73, 111, 234, 0) 35%);
  pointer-events: none;
}

.review-content {
  position: relative;
  z-index: 1;
  width: min(1240px, 100%);
  margin: 0 auto;
  padding: 1.25rem;
}

.review-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.review-title { margin: 0; color: #0e1a37; }
.review-subtitle { margin-top: 0.35rem; color: #54668f; }
.review-stats { display: flex; gap: 0.75rem; color: #4b5f8f; font-size: 0.85rem; align-items: center; }

.docs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.9rem;
}

.doc-card {
  height: 320px;
  border: 1px solid rgba(84, 124, 196, 0.24);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 28px rgba(30, 71, 147, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.doc-card--dropped { opacity: 0.58; }

.doc-preview {
  height: 80%;
  border-bottom: 1px solid rgba(84, 124, 196, 0.2);
  background: #f4f8ff;
}

.doc-preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  pointer-events: none;
}

.doc-preview-fallback {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #5f7299;
  text-align: center;
  padding: 0.75rem;
}

.doc-meta {
  height: 20%;
  padding: 0.55rem 0.7rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
}

.doc-meta-text h3 {
  font-size: 0.82rem;
  margin: 0;
  max-width: 145px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta-text p { margin: 0.2rem 0 0; font-size: 0.7rem; color: #6d7fa3; }
.dot { margin: 0 0.2rem; }

.drop-btn {
  border: 1px solid rgba(239, 68, 68, 0.32);
  background: rgba(239, 68, 68, 0.08);
  color: #bf2444;
  border-radius: 999px;
  font-size: 0.72rem;
  padding: 0.22rem 0.6rem;
}

.drop-btn--dropped {
  border-color: rgba(20, 184, 106, 0.35);
  background: rgba(20, 184, 106, 0.1);
  color: #10804c;
}

.review-actions {
  margin-top: 1rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
}

.action-btn {
  border-radius: 12px;
  padding: 0.55rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.action-btn--ghost {
  border: 1px solid rgba(84, 124, 196, 0.28);
  background: rgba(255, 255, 255, 0.85);
  color: #4b5f8f;
}

.action-btn--primary {
  border: 1px solid rgba(44, 111, 255, 0.44);
  background: linear-gradient(90deg, #2c6fff, #10b7c8);
  color: #fff;
}

.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.review-empty {
  border-radius: 14px;
  border: 1px dashed rgba(84, 124, 196, 0.3);
  color: #4b5f8f;
  background: rgba(255, 255, 255, 0.75);
  padding: 1rem;
}

.viewer-shell {
  height: 80vh;
  background: #fff;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.viewer-header {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid rgba(84, 124, 196, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.viewer-header h3 { margin: 0; font-size: 0.95rem; }
.viewer-header p { margin: 0.2rem 0 0; color: #6d7fa3; font-size: 0.75rem; }
.viewer-close { border: none; background: transparent; cursor: pointer; }

.viewer-body {
  height: calc(80vh - 68px);
  display: grid;
  grid-template-rows: auto 1fr;
}

.viewer-controls {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 0.8rem;
  border-bottom: 1px solid rgba(84, 124, 196, 0.16);
}

.viewer-controls button {
  border: 1px solid rgba(84, 124, 196, 0.28);
  background: #fff;
  border-radius: 8px;
  padding: 0.22rem 0.5rem;
}

.viewer-frame-wrap { height: 100%; }
.viewer-frame { width: 100%; height: 100%; border: none; }

.viewer-fallback {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  color: #4b5f8f;
}

@media (max-width: 760px) {
  .review-content { padding: 0.9rem; }
  .review-header { flex-direction: column; }
  .doc-card { height: 300px; }
}
</style>
