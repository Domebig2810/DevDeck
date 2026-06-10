<script setup lang="ts">
import { computed, watch, ref } from "vue";
import { useConfigs } from "@/composables/useConfigs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  RotateCcw,
  RotateCw,
  MousePointerClick,
  Square,
} from "lucide-vue-next";

const { selected, selectedId, updateConfig } = useConfigs();

const local = ref<any>(null);

watch(
  selected,
  (val) => {
    if (val) local.value = JSON.parse(JSON.stringify(val.config));
  },
  { immediate: true, deep: true },
);

const activeEl = ref<{ type: "button" | "encoder"; index: number } | null>(
  null,
);

const activeButton = computed(() => {
  if (activeEl.value?.type === "button" && local.value)
    return local.value.buttons[activeEl.value.index];
  return null;
});

const activeEncoder = computed(() => {
  if (activeEl.value?.type === "encoder" && local.value)
    return local.value.encoders[activeEl.value.index];
  return null;
});

function select(type: "button" | "encoder", index: number) {
  activeEl.value = { type, index };
}

function isActive(type: "button" | "encoder", index: number) {
  return activeEl.value?.type === type && activeEl.value?.index === index;
}

async function save() {
  if (!selectedId.value || !local.value) return;
  await updateConfig(selectedId.value, local.value);
}

async function handleImageChange(e: Event, buttonIndex: number) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const base64 = await new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(",")[1]);
    reader.readAsDataURL(file);
  });

  const result = await window.pywebview!.api.convert_image(base64, buttonIndex);
  if (result?.path && local.value) {
    local.value.buttons[buttonIndex].image = result.path;
    local.value.buttons[buttonIndex].image_preview = result.base64;
    await save();
  }
}

const editingName = ref(false);
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center gap-2 px-4 py-3 border-b">
      <SidebarTrigger />
      <template v-if="local">
        <div class="w-px h-5 bg-border mx-1" />
        <input
          v-if="editingName"
          v-model="local.name"
          class="text-lg font-semibold bg-transparent border-b border-primary outline-none"
          @blur="
            editingName = false;
            save();
          "
          @keydown.enter="
            editingName = false;
            save();
          "
          autofocus
        />
        <h2
          v-else
          class="text-lg font-semibold cursor-pointer hover:text-primary transition-colors"
          @click="editingName = true"
        >
          {{ local.name }}
        </h2>
      </template>
    </div>

    <!-- Kein Config -->
    <div
      v-if="!local"
      class="flex-1 flex items-center justify-center text-muted-foreground text-sm"
    >
      Keine Konfiguration ausgewählt
    </div>

    <!-- Main -->
    <div v-else class="flex flex-1 overflow-hidden">
      <!-- Hardware-Visualisierung -->
      <div class="flex items-center justify-center flex-1 p-8">
        <div class="grid grid-cols-3 gap-3">
          <template v-for="i in 3" :key="i">
            <!-- Encoder (linke Spalte) -->
            <button
              @click="select('encoder', i - 1)"
              :class="[
                'w-24 h-24 rounded-full border-2 flex flex-col items-center justify-center gap-0.5 transition-all text-xs font-medium',
                isActive('encoder', i - 1)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-card hover:border-primary/50 hover:bg-accent text-muted-foreground',
              ]"
            >
              <RotateCw class="size-4 opacity-40" />
              <span>Enc {{ i }}</span>
            </button>

            <!-- Button 1 (mittlere Spalte) -->
            <button
              @click="select('button', (i - 1) * 2)"
              :class="[
                'w-24 h-24 rounded-xl border-2 flex flex-col items-center justify-center gap-1 transition-all text-xs font-medium overflow-hidden relative',
                isActive('button', (i - 1) * 2)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-card hover:border-primary/50 hover:bg-accent text-muted-foreground',
              ]"
            >
              <template
                v-if="
                  local.buttons[(i - 1) * 2].display_mode === 'image' &&
                  local.buttons[(i - 1) * 2].image
                "
              >
                <img
                  :src="
                    local.buttons[(i - 1) * 2].image_preview ||
                    local.buttons[(i - 1) * 2].image
                  "
                  class="w-full h-full object-cover absolute inset-0"
                />
              </template>
              <template v-else>
                <Square class="size-5 opacity-40" />
                <span class="truncate w-full text-center px-1">
                  {{
                    local.buttons[(i - 1) * 2].label || `Btn ${(i - 1) * 2 + 1}`
                  }}
                </span>
              </template>
            </button>

            <!-- Button 2 (rechte Spalte) -->
            <button
              @click="select('button', (i - 1) * 2 + 1)"
              :class="[
                'w-24 h-24 rounded-xl border-2 flex flex-col items-center justify-center gap-1 transition-all text-xs font-medium overflow-hidden relative',
                isActive('button', (i - 1) * 2 + 1)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-card hover:border-primary/50 hover:bg-accent text-muted-foreground',
              ]"
            >
              <template
                v-if="
                  local.buttons[(i - 1) * 2 + 1].display_mode === 'image' &&
                  local.buttons[(i - 1) * 2 + 1].image
                "
              >
                <img
                  :src="`file://${local.buttons[(i - 1) * 2 + 1].image}`"
                  class="w-full h-full object-cover absolute inset-0"
                />
              </template>
              <template v-else>
                <Square class="size-5 opacity-40" />
                <span class="truncate w-full text-center px-1">
                  {{
                    local.buttons[(i - 1) * 2 + 1].label ||
                    `Btn ${(i - 1) * 2 + 2}`
                  }}
                </span>
              </template>
            </button>
          </template>
        </div>
      </div>

      <!-- Detail-Panel -->
      <div class="w-80 border-l flex flex-col overflow-y-auto">
        <div v-if="activeButton" class="p-5 flex flex-col gap-5">
          <h3
            class="font-semibold text-sm text-muted-foreground uppercase tracking-wide"
          >
            Button {{ activeEl!.index + 1 }}
          </h3>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium">Label</label>
            <Input
              v-model="activeButton.label"
              placeholder="Button-Beschriftung"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium">Befehl</label>
            <Input
              v-model="activeButton.command"
              placeholder="z.B. open -a Safari"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium">Darstellung</label>
            <div class="flex gap-2">
              <Button
                size="sm"
                :variant="
                  activeButton.display_mode === 'label' ? 'default' : 'outline'
                "
                @click="
                  activeButton.display_mode = 'label';
                  save();
                "
              >
                Label
              </Button>
              <Button
                size="sm"
                :variant="
                  activeButton.display_mode === 'image' ? 'default' : 'outline'
                "
                @click="
                  activeButton.display_mode = 'image';
                  save();
                "
              >
                Bild
              </Button>
            </div>
          </div>

          <div
            v-if="activeButton.display_mode === 'image'"
            class="flex flex-col gap-1.5"
          >
            <label class="text-xs font-medium">Bild</label>
            <input
              type="file"
              accept="image/*"
              class="text-xs text-muted-foreground file:mr-2 file:text-xs file:border-0 file:bg-muted file:rounded file:px-2 file:py-1 file:cursor-pointer cursor-pointer"
              @change="(e) => handleImageChange(e, activeEl!.index)"
            />
            <span
              v-if="activeButton.image"
              class="text-xs text-muted-foreground truncate"
            >
              {{ activeButton.image }}
            </span>
          </div>
        </div>

        <div v-else-if="activeEncoder" class="p-5 flex flex-col gap-5">
          <h3
            class="font-semibold text-sm text-muted-foreground uppercase tracking-wide"
          >
            Encoder {{ activeEl!.index + 1 }}
          </h3>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium">Label (OLED-Anzeige)</label>
            <Input
              v-model="activeEncoder.label"
              placeholder="z.B. VOL"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium flex items-center gap-1.5">
              <RotateCw class="size-3" /> Rechts-Befehl
            </label>
            <Input
              v-model="activeEncoder.clockwise_command"
              placeholder="Befehl (nutze {step})"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium flex items-center gap-1.5">
              <RotateCcw class="size-3" /> Links-Befehl
            </label>
            <Input
              v-model="activeEncoder.counter_command"
              placeholder="Befehl (nutze {step})"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium flex items-center gap-1.5">
              <MousePointerClick class="size-3" /> Klick-Befehl
            </label>
            <Input
              v-model="activeEncoder.click_command"
              placeholder="Befehl bei Klick"
              @change="save"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs font-medium">Schrittweite</label>
            <Input
              type="number"
              :model-value="activeEncoder.step"
              @update:model-value="
                activeEncoder.step = parseFloat($event as string) || 1
              "
              @change="save"
              step="0.1"
              min="0.1"
            />
          </div>
        </div>

        <div
          v-else
          class="flex-1 flex items-center justify-center text-muted-foreground text-sm p-8 text-center"
        >
          Button oder Encoder auswählen um zu bearbeiten
        </div>
      </div>
    </div>
  </div>
</template>
