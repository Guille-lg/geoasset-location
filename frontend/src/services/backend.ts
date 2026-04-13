import constants from '@/utils/const';
import axios from 'axios';

const getBaseUrl = (): string => {
  let url = constants.backendHost;
  if (!url) {
    url = window.location.protocol + '//' + window.location.hostname;
  }
  if (constants.backendPort) {
    url += ':' + constants.backendPort;
  } else {
    url += ':' + window.location.port;
  }
  url += constants.backendBase ?? '';
  return url;
};

export const getEndpoint = (path: string): string => getBaseUrl() + path;

export const getAssets = async (companyId: string) => {
  try {
    const resp = await axios.get(getEndpoint(`/api/v1/assets/${companyId}`));
    return resp.data;
  } catch (error) {
    console.error('Error getting assets:', error);
    return { assets: [], metadata: {} };
  }
};

export const startAnalysisSSE = (
  companyId: string,
  companyName: string,
  forceRefresh: boolean,
  onEvent: (event: string, data: any) => void,
  onError: (error: any) => void,
): AbortController => {
  const controller = new AbortController();
  const url = getEndpoint('/api/v1/assets/analyze');

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_id: companyId,
      company_name: companyName,
      force_refresh: forceRefresh,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text();
        onError(new Error(`HTTP ${response.status}: ${text}`));
        return;
      }

      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('text/event-stream')) {
        const reader = response.body?.getReader();
        if (!reader) return;
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            let eventName = 'message';
            let eventData = '';
            for (const line of part.split('\n')) {
              if (line.startsWith('event: ')) eventName = line.slice(7).trim();
              else if (line.startsWith('data: ')) eventData = line.slice(6);
            }
            if (eventData) {
              try {
                onEvent(eventName, JSON.parse(eventData));
              } catch {
                onEvent(eventName, eventData);
              }
            }
          }
        }
      } else {
        const data = await response.json();
        onEvent('complete', data);
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err);
      }
    });

  return controller;
};
