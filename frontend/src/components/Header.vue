<template>
  <v-app-bar class="topbar" density="comfortable" flat>
    <template #prepend>
      <span class="tool-name text-h5">GeoAssets Intelligence</span>
    </template>

    <v-spacer />

    <v-btn rounded="xl" variant="outlined" class="info-btn text-none mr-5" @click="infoDialog = true">
      Info
    </v-btn>

    <v-dialog v-model="infoDialog" max-width="480">
      <v-card class="px-3 py-3 info-card rounded-xl">
        <v-card-title class="info-title">GeoAssets Intelligence</v-card-title>
        <v-card-text class="info-text">
          Plataforma de inteligencia geoespacial empresarial que identifica, estructura y visualiza los activos
          productivos de empresas españolas sobre un mapa interactivo. Combina Google Maps, modelos de lenguaje (LLMs) y
          scoring probabilístico de confianza.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn rounded="lg" variant="tonal" color="primary" @click="infoDialog = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app-bar>
</template>

<script setup lang="ts">
import { ref } from 'vue';
const infoDialog = ref(false);
</script>

<style scoped>
.topbar {
  padding-inline: 0.75rem;
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
}

.topbar :deep(.v-toolbar__content) {
  background: transparent !important;
}

.tool-name {
  color: #0f2146;
  font-size: 1.02rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.info-btn {
  color: #3c5583;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.info-card {
  border-radius: 20px;
  border: 1px solid rgba(104, 132, 186, 0.22);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.info-title {
  color: #0e1a37;
  font-weight: 700;
}

.info-text {
  color: #4f648e;
}
</style>
