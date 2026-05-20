<script setup lang="ts">
import { onMounted } from "vue";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import AppSidebar from "@/components/AppSidebar.vue";
//import ConfigEditor from "@/components/ConfigEditor.vue";
import { useConfigs } from "@/composables/useConfigs";

const { loadAll } = useConfigs();

onMounted(async () => {
  if (window.pywebview) {
    await loadAll();
  } else {
    window.addEventListener("pywebviewready", loadAll);
  }
});
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <main>
      <SidebarTrigger />
      <slot />
    </main>
  </SidebarProvider>
</template>
