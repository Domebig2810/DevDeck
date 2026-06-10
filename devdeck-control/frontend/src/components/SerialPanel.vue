<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { Button } from "@/components/ui/button";
import { Usb, Unplug } from "lucide-vue-next";

const connected = ref(false);
const port = ref<string | null>(null);
let pollInterval: ReturnType<typeof setInterval> | null = null;

async function checkStatus() {
  if (!window.pywebview) return;
  const res = await window.pywebview.api.serial_status();
  connected.value = res.connected;
  port.value = res.port ?? null;
}

async function disconnect() {
  if (!window.pywebview) return;
  await window.pywebview.api.serial_disconnect();
  await window.pywebview.api.serial_bridge_stop_auto();
  connected.value = false;
  port.value = null;
}

async function reconnect() {
  if (!window.pywebview) return;
  await window.pywebview.api.serial_bridge_start_auto();
}

onMounted(async () => {
  await checkStatus();
  pollInterval = setInterval(checkStatus, 2000);
});

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval);
});
</script>

<template>
  <div class="flex items-center gap-2 px-3 py-2 border-t text-xs">
    <Usb
      class="size-4 shrink-0 transition-colors"
      :class="connected ? 'text-green-500' : 'text-muted-foreground'"
    />

    <span v-if="connected" class="flex-1 text-muted-foreground truncate">
      {{ port }}
    </span>
    <span v-else class="flex-1 text-muted-foreground italic">
      Suche Gerät…
    </span>

    <Button
      v-if="connected"
      size="sm"
      variant="ghost"
      class="h-6 px-2 text-xs text-muted-foreground hover:text-destructive"
      title="Trennen"
      @click="disconnect"
    >
      <Unplug class="size-3" />
    </Button>
    <Button
      v-else
      size="sm"
      variant="ghost"
      class="h-6 px-2 text-xs"
      @click="reconnect"
    >
      Erneut suchen
    </Button>
  </div>
</template>
