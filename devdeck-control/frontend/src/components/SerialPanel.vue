<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { Button } from "@/components/ui/button";
import { Usb, RefreshCw, Unplug } from "lucide-vue-next";
import { useConfigs } from "@/composables/useConfigs";

const { selectedId } = useConfigs();

const ports = ref<string[]>([]);
const selectedPort = ref("");
const connected = ref(false);
const loading = ref(false);
let pollInterval: ReturnType<typeof setInterval> | null = null;

async function refreshPorts() {
  if (!window.pywebview) return;
  ports.value = await window.pywebview.api.serial_list_ports();
  if (ports.value.length && !selectedPort.value) {
    selectedPort.value = ports.value[0];
  }
}

async function connect() {
  if (!window.pywebview || !selectedPort.value) return;
  loading.value = true;
  try {
    // Push active config before connecting
    if (selectedId.value) {
      await window.pywebview.api.set_active_config(selectedId.value);
    }
    const res = await window.pywebview.api.serial_connect(selectedPort.value);
    connected.value = res.ok;
  } finally {
    loading.value = false;
  }
}

async function disconnect() {
  if (!window.pywebview) return;
  await window.pywebview.api.serial_disconnect();
  connected.value = false;
}

async function checkStatus() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.serial_status();
  connected.value = res.connected;
}

onMounted(async () => {
  await refreshPorts();
  await checkStatus();
  pollInterval = setInterval(checkStatus, 3000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<template>
  <div class="flex items-center gap-2 px-3 py-2 border-t">
    <Usb class="size-4 shrink-0" :class="connected ? 'text-green-500' : 'text-muted-foreground'" />

    <select
      v-if="!connected"
      v-model="selectedPort"
      class="flex-1 text-xs bg-transparent border border-border rounded px-2 py-1 outline-none focus:border-primary"
    >
      <option v-if="!ports.length" value="" disabled>Kein Port gefunden</option>
      <option v-for="p in ports" :key="p" :value="p">{{ p }}</option>
    </select>

    <span v-else class="flex-1 text-xs text-muted-foreground truncate">{{ selectedPort }}</span>

    <button
      v-if="!connected"
      class="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
      title="Ports aktualisieren"
      @click="refreshPorts"
    >
      <RefreshCw class="size-3.5" />
    </button>

    <Button v-if="!connected" size="sm" class="text-xs h-7 px-3" :disabled="!selectedPort || loading" @click="connect">
      Verbinden
    </Button>
    <Button v-else size="sm" variant="outline" class="text-xs h-7 px-3" @click="disconnect">
      <Unplug class="size-3 mr-1" /> Trennen
    </Button>
  </div>
</template>
