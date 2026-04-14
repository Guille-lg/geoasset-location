import { defineStore } from 'pinia';
import type {
  Asset,
  Company,
  PipelineStep,
  AnalysisMetadata,
  AppView,
  AnalysisMode,
  AgentFile,
  AgentEvent,
} from '@/types/types';

export interface AppState {
  currentView: AppView;
  selectedCompany: Company | null;
  assets: Asset[];
  metadata: AnalysisMetadata | null;
  pipelineSteps: PipelineStep[];
  isLoading: boolean;
  searchQuery: string;
  filterCategory: string | null;
  filterMinConfidence: number;
  clusteringEnabled: boolean;
  selectedAssetId: string | null;
  analysisMode: AnalysisMode;
  uploadedFiles: File[];
  filterSource: string | null;
  // Agent state
  agentMode: boolean;
  agentFiles: AgentFile[];
  agentEvents: AgentEvent[];
  agentSessionId: string | null;
}

export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    currentView: 'search',
    selectedCompany: null,
    assets: [],
    metadata: null,
    pipelineSteps: [],
    isLoading: false,
    searchQuery: '',
    filterCategory: null,
    filterMinConfidence: 0,
    clusteringEnabled: true,
    selectedAssetId: null,
    analysisMode: 'search',
    uploadedFiles: [],
    filterSource: null,
    agentMode: false,
    agentFiles: [],
    agentEvents: [],
    agentSessionId: null,
  }),
  getters: {
    filteredAssets(state): Asset[] {
      let result = state.assets;
      if (state.filterCategory) {
        result = result.filter((a) => a.category === state.filterCategory);
      }
      if (state.filterMinConfidence > 0) {
        result = result.filter((a) => a.confidence_score >= state.filterMinConfidence);
      }
      if (state.filterSource) {
        result = result.filter((a) => a.data_sources?.includes(state.filterSource!));
      }
      return result;
    },
    sourceCounts(state): Record<string, number> {
      const counts: Record<string, number> = {};
      for (const a of state.assets) {
        for (const src of (a.data_sources || [])) {
          counts[src] = (counts[src] || 0) + 1;
        }
      }
      return counts;
    },
    categoryCounts(state): Record<string, number> {
      const counts: Record<string, number> = {};
      for (const a of state.assets) {
        counts[a.category] = (counts[a.category] || 0) + 1;
      }
      return counts;
    },
    selectedAsset(state): Asset | null {
      if (!state.selectedAssetId) return null;
      return state.assets.find((a) => a.id === state.selectedAssetId) || null;
    },
  },
  actions: {
    setView(view: AppView) {
      this.currentView = view;
    },
    setCompany(company: Company) {
      this.selectedCompany = company;
    },
    setAnalysisMode(mode: AnalysisMode) {
      this.analysisMode = mode;
    },
    toggleAgentMode() {
      this.agentMode = !this.agentMode;
    },
    setAgentMode(val: boolean) {
      this.agentMode = val;
    },
    addUploadedFile(file: File) {
      this.uploadedFiles.push(file);
    },
    removeUploadedFile(index: number) {
      this.uploadedFiles.splice(index, 1);
    },
    setAssets(assets: Asset[], metadata: AnalysisMetadata) {
      this.assets = assets;
      this.metadata = metadata;
    },
    appendAssets(newAssets: Asset[], newMetadata: AnalysisMetadata) {
      const existingIds = new Set(this.assets.map((a) => a.id));
      const unique = newAssets.filter((a) => !existingIds.has(a.id));
      this.assets = [...this.assets, ...unique];
      this.metadata = {
        ...(this.metadata || {}),
        total_assets: this.assets.length,
        high_confidence: this.assets.filter((a) => a.confidence_tier === 'HIGH').length,
        medium_confidence: this.assets.filter((a) => a.confidence_tier === 'MEDIUM').length,
        low_confidence: this.assets.filter((a) => a.confidence_tier === 'LOW').length,
        company: newMetadata.company || this.metadata?.company,
      };
    },
    resetAnalysis() {
      this.assets = [];
      this.metadata = null;
      this.pipelineSteps = [];
      this.selectedAssetId = null;
      this.filterCategory = null;
      this.filterMinConfidence = 0;
      this.filterSource = null;
      this.uploadedFiles = [];
      this.agentFiles = [];
      this.agentEvents = [];
      this.agentSessionId = null;
    },
    updateStep(step: PipelineStep) {
      const idx = this.pipelineSteps.findIndex((s) => s.step === step.step);
      if (idx >= 0) {
        this.pipelineSteps[idx] = step;
      } else {
        this.pipelineSteps.push(step);
      }
    },
    selectAsset(id: string | null) {
      this.selectedAssetId = id;
    },
    setAgentFiles(files: AgentFile[]) {
      this.agentFiles = files;
    },
    setAgentSessionId(id: string) {
      this.agentSessionId = id;
    },
    addAgentEvent(event: AgentEvent) {
      this.agentEvents.push(event);
      // Keep last 200 events to avoid memory bloat
      if (this.agentEvents.length > 200) {
        this.agentEvents.shift();
      }
    },
    clearAgentEvents() {
      this.agentEvents = [];
    },
  },
});
