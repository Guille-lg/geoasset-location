<template>
  <section class="agent-page">
    <div class="agent-noise" />

    <div class="agent-content">
      <!-- Robot animation header -->
      <div class="robot-wrapper">
        <div class="robot-rings">
          <div class="ring ring--1" />
          <div class="ring ring--2" />
          <div class="ring ring--3" />
        </div>
        <div class="robot-icon-wrap" :class="{ 'robot-icon-wrap--done': isDone }">
          <v-icon size="38" :color="isDone ? '#14b86a' : '#2c6fff'">
            {{ isDone ? 'mdi-check-circle' : 'mdi-robot-outline' }}
          </v-icon>
        </div>
      </div>

      <!-- Title -->
      <h2 class="agent-title">
        <template v-if="isDone">
          Found <span class="accent-purple">{{ foundCount }}</span>
          {{ foundCount === 1 ? 'document' : 'documents' }}
        </template>
        <template v-else>
          Searching for
          <span class="accent-purple">{{ store.selectedCompany?.name || 'company' }}</span>
          documents
        </template>
      </h2>
      <p class="agent-subtitle">
        <template v-if="isDone">
          Review the found documents before analysis
        </template>
        <template v-else>
          AI agent scanning the web for reports &amp; asset listings
        </template>
      </p>

      <!-- Countdown bar -->
      <div v-if="!isDone" class="countdown-wrap">
        <div class="countdown-bar">
          <div class="countdown-fill" :style="{ width: `${timePercent}%` }" />
        </div>
        <span class="countdown-label">{{ remainingLabel }} remaining</span>
      </div>

      <!-- Event feed -->
      <div ref="feedRef" class="event-feed">
        <transition-group name="feed-item" tag="div">
          <div
            v-for="group in feedGroups"
            :key="group.key"
            class="feed-item"
            :class="`feed-item--${group.type}`"
          >
            <div class="feed-icon">
              <v-icon size="13" :color="eventIconColor(group.type)">{{ eventIcon(group.type) }}</v-icon>
            </div>
            <div class="feed-body">
              <div class="feed-heading">
                <span class="feed-label">{{ eventLabel(group.type) }}</span>
                <span v-if="group.items.length > 1" class="feed-group-count">{{ group.items.length }} calls</span>
                <button
                  v-if="group.items.length > 1"
                  class="feed-collapse-btn"
                  @click.stop="toggleGroup(group.key)"
                >
                  <v-icon
                    size="14"
                    :class="{ 'feed-chevron--collapsed': isGroupCollapsed(group.key) }"
                  >
                    mdi-chevron-down
                  </v-icon>
                </button>
              </div>

              <div v-if="group.items.length === 1" class="feed-inline">
                <span class="feed-text">{{ group.items[0].content }}</span>
                <span v-if="group.items[0].filename" class="feed-filename">{{ group.items[0].filename }}</span>
              </div>

              <template v-else>
                <transition name="feed-collapse">
                  <ul
                    v-if="!isGroupCollapsed(group.key)"
                    class="feed-group-list"
                  >
                    <li
                      v-for="item in group.items"
                      :key="`${item.timestamp}-${item.content}`"
                      class="feed-group-entry"
                    >
                      <span class="feed-text">{{ item.content }}</span>
                      <span v-if="item.filename" class="feed-filename">{{ item.filename }}</span>
                    </li>
                  </ul>
                </transition>
              </template>
            </div>
          </div>
        </transition-group>

        <div v-if="store.agentEvents.length === 0" class="feed-empty">
          <span class="feed-empty-dot" />
          <span class="feed-empty-dot feed-empty-dot--2" />
          <span class="feed-empty-dot feed-empty-dot--3" />
        </div>
      </div>

      <!-- Footer row -->
      <div class="agent-footer">
        <div class="found-badge" :class="{ 'found-badge--has': foundCount > 0 }">
          <v-icon size="14" :color="foundCount > 0 ? '#2c6fff' : '#6b7ba4'">mdi-file-check-outline</v-icon>
          <span>{{ foundCount }} document{{ foundCount === 1 ? '' : 's' }} found</span>
        </div>

        <button class="skip-btn" @click="skip">
          Skip &amp; continue
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <!-- Error -->
      <div v-if="errorMessage" class="agent-error">{{ errorMessage }}</div>

      <!-- Back -->
      <button class="back-btn" @click="cancel">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Back to search
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useAppStore } from '@/stores/store';
import { startAgentSearchSSE } from '@/services/backend';
import type { AgentFile, AgentEvent, AgentEventType } from '@/types/types';

const store = useAppStore();
const feedRef = ref<HTMLElement | null>(null);
const errorMessage = ref('');
const isDone = ref(false);
const foundCount = ref(0);
const collapsedGroups = ref<Record<string, boolean>>({});

let abortController: AbortController | null = null;
let countdownTimer: ReturnType<typeof setInterval> | null = null;

const MAX_SECONDS = 120;
const elapsed = ref(0);

const timePercent = computed(() =>
  Math.max(0, 100 - (elapsed.value / MAX_SECONDS) * 100),
);

const remainingLabel = computed(() => {
  const sec = Math.max(0, MAX_SECONDS - elapsed.value);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
});

interface GroupedAgentEvents {
  key: string
  type: AgentEventType
  items: AgentEvent[]
}

const feedGroups = computed<GroupedAgentEvents[]>(() => {
  const groups: GroupedAgentEvents[] = [];
  for (const ev of store.agentEvents) {
    const last = groups[groups.length - 1];
    if (ev.type !== 'thinking' && last && last.type === ev.type) {
      last.items.push(ev);
      continue;
    }
    groups.push({
      key: `${ev.timestamp}-${ev.type}`,
      type: ev.type,
      items: [ev],
    });
  }
  return groups;
});

function isGroupCollapsed(key: string): boolean {
  return collapsedGroups.value[key] !== false;
}

function toggleGroup(key: string) {
  collapsedGroups.value[key] = !collapsedGroups.value[key];
}

// Auto-scroll the feed to latest entry
watch(
  () => store.agentEvents.length,
  async () => {
    await nextTick();
    if (feedRef.value) {
      feedRef.value.scrollTop = feedRef.value.scrollHeight;
    }
  },
);

function eventIcon(type: AgentEventType): string {
  switch (type) {
    case 'thinking':    return 'mdi-thought-bubble-outline';
    case 'searching':   return 'mdi-magnify';
    case 'found_urls':  return 'mdi-link-variant';
    case 'downloading': return 'mdi-download-outline';
    case 'accepted':    return 'mdi-check-circle-outline';
    case 'rejected':    return 'mdi-close-circle-outline';
    case 'error':       return 'mdi-alert-circle-outline';
    default:            return 'mdi-circle-small';
  }
}

function eventIconColor(type: AgentEventType): string {
  switch (type) {
    case 'thinking':    return '#6366f1';
    case 'searching':   return '#60a5fa';
    case 'found_urls':  return '#6b7ba4';
    case 'downloading': return '#10b7c8';
    case 'accepted':    return '#14b86a';
    case 'rejected':    return '#ef4444';
    case 'error':       return '#ef4444';
    default:            return '#6b7ba4';
  }
}

function eventLabel(type: AgentEventType): string {
  switch (type) {
    case 'thinking':    return 'Thinking';
    case 'searching':   return 'Searching';
    case 'found_urls':  return 'Found';
    case 'downloading': return 'Downloading';
    case 'accepted':    return 'Accepted';
    case 'rejected':    return 'Rejected';
    case 'error':       return 'Error';
    default:            return '';
  }
}

function addEvent(type: AgentEventType, content: string, filename?: string, url?: string) {
  const ev: AgentEvent = { type, content, filename, url, timestamp: Date.now() };
  store.addAgentEvent(ev);
}

function handleAgentEvent(event: string, data: any) {
  switch (event) {
    case 'agent_started':
      store.setAgentSessionId(data.session_id || '');
      break;

    case 'agent_thinking':
      addEvent('thinking', data.content || '');
      break;

    case 'agent_searching':
      addEvent('searching', data.query || '');
      break;

    case 'agent_found_urls':
      addEvent('found_urls', `${data.count} result${data.count !== 1 ? 's' : ''} found`);
      break;

    case 'agent_downloading':
      addEvent('downloading', data.url || '', data.filename);
      break;

    case 'agent_accepted':
      foundCount.value++;
      addEvent('accepted', data.reason || 'Relevant document', data.filename);
      break;

    case 'agent_rejected':
      addEvent('rejected', data.reason || 'Not relevant', data.filename);
      break;

    case 'agent_error':
      errorMessage.value = data.message || 'Agent encountered an error';
      addEvent('error', data.message || 'Unknown error');
      break;

    case 'agent_complete':
    case 'agent_timeout': {
      const files: AgentFile[] = (data.found_files || []).map((f: any) => ({
        ...f,
        session_id: data.session_id || store.agentSessionId || '',
      }));
      store.setAgentFiles(files);
      if (data.session_id) store.setAgentSessionId(data.session_id);
      foundCount.value = files.length;
      finish(files);
      break;
    }
  }
}

function finish(files: AgentFile[]) {
  isDone.value = true;
  stopCountdown();

  // Recalculate analysis mode based on what we actually have
  const hasSearch = !!store.selectedCompany?.name;
  const hasDocs = files.length > 0 || store.uploadedFiles.length > 0;
  if (hasSearch && hasDocs) {
    store.setAnalysisMode('combined');
  } else if (hasDocs) {
    store.setAnalysisMode('document');
  }
  // else keep whatever mode was set (search)

  // Transition to document review after a short delay so user sees the done state
  setTimeout(() => {
    store.setView('agent_review');
  }, 1800);
}

function skip() {
  abortController?.abort();
  abortController = null;
  finish(store.agentFiles);
}

function cancel() {
  abortController?.abort();
  stopCountdown();
  store.resetAnalysis();
  store.setView('search');
}

function stopCountdown() {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
}

onMounted(() => {
  if (!store.selectedCompany) return;

  countdownTimer = setInterval(() => {
    elapsed.value++;
  }, 1000);

  abortController = startAgentSearchSSE(
    store.selectedCompany.id,
    store.selectedCompany.name,
    handleAgentEvent,
    (err) => {
      errorMessage.value = err?.message || 'Connection error';
    },
  );
});

onUnmounted(() => {
  abortController?.abort();
  stopCountdown();
});
</script>

<style scoped>
/* ── Page ── */
.agent-page {
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

.agent-noise {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 18%, rgba(89, 220, 225, 0.2), rgba(89, 220, 225, 0) 36%),
    radial-gradient(circle at 82% 10%, rgba(122, 149, 255, 0.22), rgba(122, 149, 255, 0) 36%),
    radial-gradient(circle at 50% 88%, rgba(73, 111, 234, 0.14), rgba(73, 111, 234, 0) 35%);
  pointer-events: none;
}

/* ── Content ── */
.agent-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  width: min(740px, 100%);
  padding: 2rem 1.25rem;
}

/* ── Robot animation ── */
.robot-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.75rem;
}

.robot-rings {
  position: absolute;
  inset: 0;
}

.ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(44, 111, 255, 0.2);
  animation: ringExpand 3s ease-out infinite;
}

.ring--1 { inset: 0;   animation-delay: 0s; }
.ring--2 { inset: -14px; animation-delay: 0.9s; }
.ring--3 { inset: -28px; animation-delay: 1.8s; }

@keyframes ringExpand {
  0%   { opacity: 0.6; transform: scale(0.85); }
  70%  { opacity: 0.15; }
  100% { opacity: 0;   transform: scale(1.1); }
}

.robot-icon-wrap {
  position: relative;
  z-index: 2;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(44, 111, 255, 0.12);
  border: 1px solid rgba(44, 111, 255, 0.32);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: iconPulse 2.5s ease-in-out infinite;
  transition: background 400ms, border-color 400ms;
}

.robot-icon-wrap--done {
  background: rgba(20, 184, 106, 0.12);
  border-color: rgba(20, 184, 106, 0.35);
  animation: none;
}

@keyframes iconPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(44, 111, 255, 0.28); }
  50%       { box-shadow: 0 0 0 10px rgba(44, 111, 255, 0); }
}

/* ── Typography ── */
.agent-title {
  font-size: clamp(1.4rem, 3.5vw, 2rem);
  font-weight: 700;
  color: #0e1a37;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 0.4rem;
  animation: riseIn 500ms ease-out both;
}

.accent-purple {
  background: linear-gradient(90deg, #2c6fff, #10b7c8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.agent-subtitle {
  color: #54668f;
  font-size: 0.9rem;
  margin-bottom: 1.25rem;
  animation: riseIn 620ms ease-out both;
}

/* ── Countdown ── */
.countdown-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  max-width: 420px;
  margin-bottom: 1.25rem;
  animation: riseIn 700ms ease-out both;
}

.countdown-bar {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: rgba(44, 111, 255, 0.14);
  overflow: hidden;
}

.countdown-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #2c6fff, #10b7c8);
  transition: width 1s linear;
}

.countdown-label {
  font-size: 0.75rem;
  color: #64748b;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* ── Event feed ── */
.event-feed {
  width: 100%;
  max-width: 640px;
  height: 260px;
  overflow-y: auto;
  border: 1px solid rgba(84, 124, 196, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 35px rgba(30, 71, 147, 0.12);
  padding: 0.75rem;
  margin-bottom: 1.25rem;
  scroll-behavior: smooth;
  animation: riseIn 800ms ease-out both;
}

.event-feed::-webkit-scrollbar { width: 4px; }
.event-feed::-webkit-scrollbar-track { background: transparent; }
.event-feed::-webkit-scrollbar-thumb { background: rgba(44, 111, 255, 0.28); border-radius: 2px; }

.feed-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.35rem;
  border-radius: 8px;
  transition: background 200ms;
}

.feed-item:last-child {
  background: rgba(44, 111, 255, 0.07);
}

.feed-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feed-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.28rem;
  min-width: 0;
  width: 100%;
}

.feed-heading {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.feed-collapse-btn {
  border: none;
  background: transparent;
  color: #5f739d;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  margin-left: auto;
}

.feed-chevron--collapsed {
  transform: rotate(-90deg);
}

.feed-group-count {
  font-size: 0.66rem;
  font-weight: 600;
  color: #6c80a8;
  background: rgba(44, 111, 255, 0.1);
  border: 1px solid rgba(44, 111, 255, 0.2);
  border-radius: 999px;
  padding: 0.08rem 0.42rem;
}

.feed-inline {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.feed-group-list {
  list-style: none;
  margin: 0;
  padding: 0;
  width: 100%;
  overflow: hidden;
}

.feed-group-entry {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.05rem 0;
  flex-wrap: wrap;
}

.feed-collapse-enter-active,
.feed-collapse-leave-active {
  transition: max-height 220ms ease, opacity 220ms ease, transform 220ms ease;
}

.feed-collapse-enter-from,
.feed-collapse-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-4px);
}

.feed-collapse-enter-to,
.feed-collapse-leave-from {
  max-height: 260px;
  opacity: 1;
  transform: translateY(0);
}

.feed-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #475569;
  white-space: nowrap;
}

.feed-item--thinking .feed-label   { color: #a78bfa; }
.feed-item--searching .feed-label  { color: #60a5fa; }
.feed-item--downloading .feed-label{ color: #10b7c8; }
.feed-item--accepted .feed-label   { color: #14b86a; }
.feed-item--rejected .feed-label   { color: #ef4444; }
.feed-item--error .feed-label      { color: #ef4444; }

.feed-text {
  font-size: 0.78rem;
  color: #42587f;
  word-break: break-word;
  line-height: 1.35;
}

.feed-filename {
  font-size: 0.72rem;
  color: #5d739b;
  font-family: monospace;
  word-break: break-all;
}

/* Transition animations */
.feed-item-enter-active {
  transition: all 300ms ease-out;
}
.feed-item-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

/* Loading dots when empty */
.feed-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.45rem;
  height: 100%;
  min-height: 80px;
}

.feed-empty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(44, 111, 255, 0.35);
  animation: dotBounce 1.4s ease-in-out infinite;
}
.feed-empty-dot--2 { animation-delay: 0.2s; }
.feed-empty-dot--3 { animation-delay: 0.4s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(1);   opacity: 0.4; }
  40%            { transform: scale(1.4); opacity: 1; }
}

/* ── Footer ── */
.agent-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 640px;
  margin-bottom: 1rem;
  animation: riseIn 900ms ease-out both;
}

.found-badge {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: #5a6f95;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  border: 1px solid rgba(84, 124, 196, 0.24);
  background: rgba(255, 255, 255, 0.85);
  transition: color 300ms, border-color 300ms;
}

.found-badge--has {
  color: #2c6fff;
  border-color: rgba(44, 111, 255, 0.35);
  background: rgba(44, 111, 255, 0.1);
}

.skip-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(84, 124, 196, 0.28);
  color: #2c6fff;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background 200ms, border-color 200ms, transform 150ms;
}

.skip-btn:hover {
  background: rgba(44, 111, 255, 0.1);
  border-color: rgba(44, 111, 255, 0.45);
  transform: translateY(-1px);
}

/* ── Error ── */
.agent-error {
  margin-bottom: 0.75rem;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #b91c1c;
  font-size: 0.8rem;
  max-width: 640px;
  width: 100%;
  text-align: left;
}

/* ── Back ── */
.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #54668f;
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 200ms;
}

.back-btn:hover { color: #2c6fff; }

@media (max-width: 680px) {
  .agent-content {
    padding: 1.5rem 1rem;
  }

  .event-feed {
    height: 220px;
  }

  .agent-footer {
    flex-direction: column;
    gap: 0.65rem;
    align-items: stretch;
  }

  .found-badge,
  .skip-btn {
    justify-content: center;
  }
}

/* ── Shared keyframes ── */
@keyframes riseIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
