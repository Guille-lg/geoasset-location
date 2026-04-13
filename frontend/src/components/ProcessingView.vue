<template>
  <section class="processing-page">
    <div class="hero-noise" />

    <div class="processing-content">
      <!-- Animated orbital SVG -->
      <div class="orbital-wrapper">
        <svg class="orbital-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <!-- Outer ring -->
          <circle cx="100" cy="100" r="90" fill="none" stroke="rgba(44,111,255,0.08)" stroke-width="1" />
          <!-- Middle ring -->
          <circle cx="100" cy="100" r="65" fill="none" stroke="rgba(44,111,255,0.1)" stroke-width="1" />
          <!-- Inner ring -->
          <circle cx="100" cy="100" r="40" fill="none" stroke="rgba(44,111,255,0.12)" stroke-width="1" />

          <!-- Rotating arc 1 -->
          <circle
            cx="100" cy="100" r="90"
            fill="none" stroke="url(#grad1)" stroke-width="2.5"
            stroke-dasharray="80 486"
            stroke-linecap="round"
            class="orbit-arc orbit-arc--1"
          />
          <!-- Rotating arc 2 -->
          <circle
            cx="100" cy="100" r="65"
            fill="none" stroke="url(#grad2)" stroke-width="2"
            stroke-dasharray="55 353"
            stroke-linecap="round"
            class="orbit-arc orbit-arc--2"
          />
          <!-- Rotating arc 3 -->
          <circle
            cx="100" cy="100" r="40"
            fill="none" stroke="url(#grad3)" stroke-width="2"
            stroke-dasharray="35 216"
            stroke-linecap="round"
            class="orbit-arc orbit-arc--3"
          />

          <!-- Pulsing core -->
          <circle cx="100" cy="100" r="12" class="core-pulse" />
          <circle cx="100" cy="100" r="6" fill="#2c6fff" />

          <!-- Orbiting dots -->
          <circle r="3.5" fill="#2c6fff" class="orbit-dot orbit-dot--1">
            <animateMotion dur="6s" repeatCount="indefinite" path="M100,10 A90,90 0 1,1 99.99,10" />
          </circle>
          <circle r="2.5" fill="#10b7c8" class="orbit-dot orbit-dot--2">
            <animateMotion dur="4.5s" repeatCount="indefinite" path="M100,35 A65,65 0 1,1 99.99,35" />
          </circle>
          <circle r="2" fill="#6366f1" class="orbit-dot orbit-dot--3">
            <animateMotion dur="3s" repeatCount="indefinite" path="M100,60 A40,40 0 1,1 99.99,60" />
          </circle>

          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#2c6fff" stop-opacity="0" />
              <stop offset="100%" stop-color="#2c6fff" stop-opacity="0.7" />
            </linearGradient>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#10b7c8" stop-opacity="0" />
              <stop offset="100%" stop-color="#10b7c8" stop-opacity="0.6" />
            </linearGradient>
            <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#6366f1" stop-opacity="0" />
              <stop offset="100%" stop-color="#6366f1" stop-opacity="0.5" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <!-- Text content -->
      <h2 class="processing-title">
        Analyzing <span class="company-highlight">{{ store.selectedCompany?.name || 'company' }}</span>
      </h2>
      <p class="processing-subtitle">Scanning industrial assets across Spain</p>

      <!-- Progress percentage -->
      <div class="progress-ring-label">{{ Math.round(globalProgress) }}%</div>

      <!-- Timeline steps -->
      <div class="timeline">
        <div
          v-for="(step, i) in steps"
          :key="step.step"
          class="timeline-step"
          :class="{
            'timeline-step--complete': step.status === 'complete',
            'timeline-step--running': step.status === 'running',
            'timeline-step--error': step.status === 'error',
            'timeline-step--pending': step.status === 'pending',
          }"
        >
          <!-- Connector line -->
          <div v-if="i > 0" class="timeline-connector">
            <div class="timeline-connector-fill" :class="{ filled: step.status !== 'pending' }" />
          </div>

          <!-- Node -->
          <div class="timeline-node">
            <svg v-if="step.status === 'running'" class="node-spinner" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" fill="none" stroke="rgba(44,111,255,0.2)" stroke-width="2" />
              <circle
                cx="12" cy="12" r="10" fill="none"
                stroke="#2c6fff" stroke-width="2"
                stroke-dasharray="20 43"
                stroke-linecap="round"
                class="spinner-arc"
              />
            </svg>
            <svg v-else-if="step.status === 'complete'" class="node-check" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="11" fill="#14b86a" />
              <path d="M8 12.5l2.5 2.5 5.5-5.5" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="check-path" />
            </svg>
            <svg v-else-if="step.status === 'error'" class="node-error" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="11" fill="#ef4444" />
              <path d="M9 9l6 6M15 9l-6 6" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" />
            </svg>
            <div v-else class="node-pending">
              <span>{{ i + 1 }}</span>
            </div>
          </div>

          <!-- Label -->
          <div class="timeline-label">
            <span class="timeline-name">{{ step.name }}</span>
            <span v-if="step.found != null && step.status === 'complete'" class="timeline-meta">
              {{ step.found }} results
            </span>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-if="errorMessage" class="error-banner">
        <span>{{ errorMessage }}</span>
        <button class="retry-link" @click="retry">Retry</button>
      </div>

      <!-- Cancel -->
      <button class="cancel-link" @click="cancel">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
        Back to search
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useAppStore } from '@/stores/store';
import { startAnalysisSSE } from '@/services/backend';
import type { PipelineStep } from '@/types/types';

const store = useAppStore();
const errorMessage = ref('');
let abortController: AbortController | null = null;

const TOTAL_STEPS = 5;

const steps = computed(() => {
  const defaults: PipelineStep[] = [
    { step: 0, name: 'Identificando empresa', status: 'pending' },
    { step: 1, name: 'Buscando en Google Maps', status: 'pending' },
    { step: 2, name: 'Clasificando activos con IA', status: 'pending' },
    { step: 3, name: 'Enriqueciendo datos', status: 'pending' },
    { step: 4, name: 'Calculando confianza', status: 'pending' },
  ];
  for (const s of store.pipelineSteps) {
    const idx = defaults.findIndex((d) => d.step === s.step);
    if (idx >= 0) defaults[idx] = { ...defaults[idx], ...s };
  }
  return defaults;
});

const globalProgress = computed(() => {
  const completed = steps.value.filter((s) => s.status === 'complete').length;
  const running = steps.value.filter((s) => s.status === 'running').length;
  return ((completed + running * 0.5) / TOTAL_STEPS) * 100;
});

const startAnalysis = () => {
  if (!store.selectedCompany) return;
  errorMessage.value = '';
  store.pipelineSteps = [];

  abortController = startAnalysisSSE(
    store.selectedCompany.id,
    store.selectedCompany.name,
    true,
    (event: string, data: any) => {
      if (event === 'step_start') {
        store.updateStep({
          step: data.step,
          name: data.name,
          status: 'running',
          estimated_seconds: data.estimated_seconds,
        });
      } else if (event === 'step_complete') {
        store.updateStep({ step: data.step, name: data.name, status: 'complete', found: data.found });
      } else if (event === 'complete') {
        const assets = data.assets || [];
        const metadata = data.metadata || { total_assets: assets.length };
        store.setAssets(assets, metadata);
        store.setView('results');
      } else if (event === 'error') {
        errorMessage.value = data.message || 'Error en el pipeline';
      }
    },
    (error: any) => {
      errorMessage.value = error?.message || 'Error de conexión';
    },
  );
};

const cancel = () => {
  abortController?.abort();
  store.resetAnalysis();
  store.setView('search');
};

const retry = () => {
  abortController?.abort();
  startAnalysis();
};

onMounted(() => {
  startAnalysis();
});

onUnmounted(() => {
  abortController?.abort();
});
</script>

<style scoped>
/* ── Page ── */
.processing-page {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.85) 0%,
    rgba(238, 246, 255, 0.9) 45%,
    rgba(233, 242, 255, 0.82) 100%
  );
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

.processing-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  width: min(640px, 100%);
  padding: 0 1.25rem;
}

/* ── Orbital animation ── */
.orbital-wrapper {
  width: 180px;
  height: 180px;
  margin-bottom: 1.5rem;
  animation: fadeScaleIn 600ms ease-out both;
}

.orbital-svg {
  width: 100%;
  height: 100%;
}

.orbit-arc--1 {
  transform-origin: center;
  animation: orbitSpin 8s linear infinite;
}

.orbit-arc--2 {
  transform-origin: center;
  animation: orbitSpin 6s linear infinite reverse;
}

.orbit-arc--3 {
  transform-origin: center;
  animation: orbitSpin 4s linear infinite;
}

.core-pulse {
  fill: rgba(44, 111, 255, 0.12);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes orbitSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { r: 12; opacity: 0.3; }
  50% { r: 18; opacity: 0.08; }
}

@keyframes fadeScaleIn {
  from { opacity: 0; transform: scale(0.85); }
  to { opacity: 1; transform: scale(1); }
}

/* ── Typography ── */
.processing-title {
  font-size: clamp(1.5rem, 3.5vw, 2.1rem);
  font-weight: 700;
  color: #0e1a37;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 0.35rem;
  animation: riseIn 500ms ease-out both;
}

.company-highlight {
  background: linear-gradient(90deg, #2c6fff, #10b7c8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.processing-subtitle {
  color: #54668f;
  font-size: 0.95rem;
  margin-bottom: 0.75rem;
  animation: riseIn 600ms ease-out both;
}

.progress-ring-label {
  font-size: 2.5rem;
  font-weight: 800;
  color: #2c6fff;
  letter-spacing: -0.03em;
  margin-bottom: 2rem;
  font-variant-numeric: tabular-nums;
  animation: riseIn 650ms ease-out both;
}

@keyframes riseIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Timeline ── */
.timeline {
  display: flex;
  align-items: flex-start;
  gap: 0;
  width: 100%;
  max-width: 560px;
  animation: riseIn 750ms ease-out both;
}

.timeline-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* Connector */
.timeline-connector {
  position: absolute;
  top: 14px;
  right: 50%;
  width: 100%;
  height: 2px;
  background: rgba(44, 111, 255, 0.12);
  z-index: 0;
}

.timeline-connector-fill {
  height: 100%;
  width: 0%;
  background: #14b86a;
  border-radius: 1px;
  transition: width 600ms ease;
}

.timeline-connector-fill.filled {
  width: 100%;
}

/* Node */
.timeline-node {
  width: 28px;
  height: 28px;
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.node-spinner,
.node-check,
.node-error {
  width: 28px;
  height: 28px;
}

.spinner-arc {
  transform-origin: center;
  animation: orbitSpin 1s linear infinite;
}

.check-path {
  stroke-dasharray: 20;
  stroke-dashoffset: 20;
  animation: drawCheck 400ms ease-out forwards;
}

@keyframes drawCheck {
  to { stroke-dashoffset: 0; }
}

.node-pending {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(44, 111, 255, 0.18);
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-pending span {
  font-size: 0.7rem;
  font-weight: 600;
  color: #8fa0bf;
}

/* Label */
.timeline-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.timeline-name {
  font-size: 0.72rem;
  font-weight: 500;
  color: #8fa0bf;
  transition: color 300ms ease;
  line-height: 1.3;
  max-width: 100px;
}

.timeline-step--complete .timeline-name {
  color: #12254d;
}

.timeline-step--running .timeline-name {
  color: #2c6fff;
  font-weight: 600;
}

.timeline-step--error .timeline-name {
  color: #ef4444;
}

.timeline-meta {
  font-size: 0.65rem;
  color: #14b86a;
  font-weight: 600;
}

/* ── Error banner ── */
.error-banner {
  margin-top: 1.5rem;
  padding: 0.6rem 1.2rem;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #b91c1c;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.retry-link {
  background: none;
  border: none;
  color: #2c6fff;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.82rem;
  white-space: nowrap;
}

.retry-link:hover {
  text-decoration: underline;
}

/* ── Cancel ── */
.cancel-link {
  margin-top: 2rem;
  background: none;
  border: none;
  color: #54668f;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 200ms;
}

.cancel-link:hover {
  color: #2c6fff;
}

/* ── Responsive ── */
@media (max-width: 600px) {
  .orbital-wrapper {
    width: 130px;
    height: 130px;
  }

  .timeline {
    flex-direction: column;
    align-items: stretch;
    max-width: 280px;
  }

  .timeline-step {
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
  }

  .timeline-connector {
    position: static;
    width: 2px;
    height: 20px;
    margin-left: 13px;
  }

  .timeline-label {
    align-items: flex-start;
    text-align: left;
  }
}
</style>
