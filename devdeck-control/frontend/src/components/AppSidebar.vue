<script setup lang="ts">
import { Plus, Trash2, Download, Upload } from "lucide-vue-next";
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
import { ref } from "vue";

const {
  configs,
  selectedId,
  createConfig,
  deleteConfig,
  exportJson,
  importJson,
} = useConfigs();

const fileInput = ref<HTMLInputElement | null>(null);
const pendingDeleteId = ref<number | null>(null);

function onImportClick() {
  fileInput.value?.click();
}

async function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) await importJson(file);
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
