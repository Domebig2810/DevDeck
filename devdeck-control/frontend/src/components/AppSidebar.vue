<script setup lang="ts">
import { Plus, Trash2, Download, Upload, FolderOpen, X } from "lucide-vue-next";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarGroupAction,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuAction,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useConfigs } from "@/composables/useConfigs";
import SerialPanel from "@/components/SerialPanel.vue";
import { ref, watch } from "vue";

const { configs, selectedId, createConfig, deleteConfig, importJson } =
  useConfigs();

const fileInput = ref<HTMLInputElement | null>(null);
const pendingDeleteId = ref<number | null>(null);
const exportedPath = ref<string | null>(null);

async function exportJson() {
  if (!selectedId.value) return;
  const path = await window.pywebview!.api.export_json(selectedId.value);
  if (path) exportedPath.value = path;
}

function getFileName(path: string) {
  return path.split("/").pop() ?? path;
}

function getDirectory(path: string) {
  return path.substring(0, path.lastIndexOf("/"));
}

async function revealInFinder() {
  if (exportedPath.value) {
    await window.pywebview!.api.reveal_in_finder(exportedPath.value);
  }
}

function onImportClick() {
  fileInput.value?.click();
}

async function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) {
    console.log("no file selected");
    return;
  }
  console.log("file:", file.name);
  const text = await file.text();
  console.log("text:", text);
  const result = await importJson(file);
  console.log("result:", result);
}

function requestDelete(id: number) {
  pendingDeleteId.value = id;
}

async function confirmDelete() {
  if (pendingDeleteId.value !== null) {
    await deleteConfig(pendingDeleteId.value);
    pendingDeleteId.value = null;
  }
}

function cancelDelete() {
  pendingDeleteId.value = null;
}

// When the user switches config while serial is connected, push it to Arduino
watch(selectedId, async (id) => {
  if (id !== null && window.pywebview) {
    await window.pywebview.api.set_active_config(id);
  }
});
</script>

<template>
  <Sidebar>
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Konfigurationen</SidebarGroupLabel>
        <SidebarGroupAction @click="createConfig" title="Neue Konfiguration">
          <Plus />
        </SidebarGroupAction>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="c in configs" :key="c.id">
              <SidebarMenuButton
                :is-active="selectedId === c.id"
                @click="selectedId = c.id"
              >
                <span>{{ c.config.name }}</span>
              </SidebarMenuButton>
              <SidebarMenuAction
                show-on-hover
                @click.stop="requestDelete(c.id)"
                title="Löschen"
              >
                <Trash2 />
              </SidebarMenuAction>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <!-- Export-Hinweis -->
      <div
        v-if="exportedPath"
        class="mx-2 mb-1 rounded-lg border border-border bg-muted/50 p-3 text-xs"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col gap-1 min-w-0">
            <span class="font-medium text-foreground truncate">
              {{ getFileName(exportedPath) }}
            </span>
            <span class="text-muted-foreground truncate">
              {{ getDirectory(exportedPath) }}
            </span>
          </div>
          <button
            @click="exportedPath = null"
            class="text-muted-foreground hover:text-foreground shrink-0 mt-0.5"
          >
            <X class="size-3" />
          </button>
        </div>
        <button
          @click="revealInFinder"
          class="mt-2 flex items-center gap-1.5 text-primary hover:underline"
        >
          <FolderOpen class="size-3" />
          <span>Im Finder anzeigen</span>
        </button>
      </div>

      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton @click="exportJson">
            <Download />
            <span>Export</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton @click="onImportClick">
            <Upload />
            <span>Import</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>

    <SerialPanel />

    <input
      ref="fileInput"
      type="file"
      accept=".json"
      class="hidden"
      @change="onFileSelected"
    />
  </Sidebar>

  <AlertDialog :open="pendingDeleteId !== null">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>Konfiguration löschen?</AlertDialogTitle>
        <AlertDialogDescription>
          Diese Aktion kann nicht rückgängig gemacht werden. Die Konfiguration
          wird dauerhaft gelöscht.
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel @click="cancelDelete">Abbrechen</AlertDialogCancel>
        <AlertDialogAction @click="confirmDelete">Löschen</AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
