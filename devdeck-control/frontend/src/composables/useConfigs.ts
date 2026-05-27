import { ref, computed } from "vue";

const configs = ref<{ id: number; config: Config }[]>([]);
const selectedId = ref<number | null>(null);

const selected = computed(
  () => configs.value.find((c) => c.id === selectedId.value) ?? null,
);

async function loadAll() {
  configs.value = await window.pywebview!.api.load_all();
  if (configs.value.length && selectedId.value === null) {
    selectedId.value = configs.value[0].id;
  }
}

async function createConfig() {
  const result = await window.pywebview!.api.create_config("New Config");
  configs.value.push(result);
  selectedId.value = result.id;
}

async function updateConfig(id: number, config: Config) {
  const idx = configs.value.findIndex((c) => c.id === id);
  if (idx !== -1) configs.value[idx].config = config;
  await window.pywebview!.api.update_config(id, config);
}

async function deleteConfig(id: number) {
  await window.pywebview!.api.delete_config(id);
  configs.value = configs.value.filter((c) => c.id !== id);
  if (selectedId.value === id) {
    selectedId.value = configs.value[0]?.id ?? null;
  }
}

async function exportJson() {
  if (!selectedId.value) return;
  return await window.pywebview!.api.export_json(selectedId.value);
}

async function importJson(file: File) {
  const previousIds = new Set(configs.value.map((c) => c.id));
  const text = await file.text();
  const result = await window.pywebview!.api.import_json(text);
  if (!result) return;
  configs.value = result;
  // Springe zur ersten neu importierten Config
  const newConfig = configs.value.find((c) => !previousIds.has(c.id));
  if (newConfig) selectedId.value = newConfig.id;
}

export function useConfigs() {
  return {
    configs,
    selectedId,
    selected,
    loadAll,
    createConfig,
    updateConfig,
    deleteConfig,
    exportJson,
    importJson,
  };
}