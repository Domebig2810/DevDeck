<script setup lang="ts">
import { ref, computed, onUnmounted } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { X } from "lucide-vue-next";

const emit = defineEmits<{ close: [] }>();

// Schritte: 0 = Screens, 1 = Buttons, 2 = Encoder, 3 = fertig
const step = ref(0);
const error = ref("");

// Schritt 1: welche Ziffer zeigt jede Position (zeilenweise, links oben -> rechts unten)
const digits = ref<string[]>(["", "", "", "", "", ""]);

// Schritt 2/3: aufgezeichnete Hardware-Indizes in Drück-/Dreh-Reihenfolge
const buttonOrder = ref<number[]>([]);
const encoderOrder = ref<number[]>([]);

let poll: ReturnType<typeof setInterval> | null = null;
let seenCount = 0;

async function start() {
  error.value = "";
  const res = await window.pywebview!.api.hw_test_start();
  if (!res.ok) {
    error.value = "Kein Gerät verbunden.";
    return;
  }
  step.value = 0;
}

function startEventPolling() {
  seenCount = 0;
  poll = setInterval(async () => {
    const events: { type: string; index: number }[] =
      await window.pywebview!.api.hw_test_events();
    for (const e of events.slice(seenCount)) {
      if (step.value === 1 && e.type === "button") {
        if (!buttonOrder.value.includes(e.index) && buttonOrder.value.length < 6)
          buttonOrder.value.push(e.index);
      }
      if (step.value === 2 && e.type === "encoder") {
        if (!encoderOrder.value.includes(e.index) && encoderOrder.value.length < 3)
          encoderOrder.value.push(e.index);
      }
    }
    seenCount = events.length;
  }, 300);
}

function stopEventPolling() {
  if (poll) clearInterval(poll);
  poll = null;
}

const digitsValid = computed(() => {
  const vals = digits.value.map((d) => parseInt(d, 10));
  return (
    vals.every((v) => v >= 0 && v <= 5) && new Set(vals).size === 6
  );
});

function nextFromDigits() {
  if (!digitsValid.value) {
    error.value = "Jede Ziffer 0-5 muss genau einmal vorkommen.";
    return;
  }
  error.value = "";
  step.value = 1;
  buttonOrder.value = [];
  startEventPolling();
}

function nextFromButtons() {
  step.value = 2;
  encoderOrder.value = [];
}

async function finish() {
  stopEventPolling();

  // slots: logische Position -> angezeigte Ziffer (= TCA-Kanal)
  const slots: Record<number, number> = {};
  digits.value.forEach((d, pos) => (slots[pos] = parseInt(d, 10)));

  // buttons: hw-Index -> logische Position (Reihenfolge des Drückens)
  const buttons: Record<number, number> = {};
  buttonOrder.value.forEach((hwIdx, pos) => (buttons[hwIdx] = pos));

  // encoders: hw-Index -> Reihe (Reihenfolge des Drehens)
  const encoders: Record<number, number> = {};
  encoderOrder.value.forEach((hwIdx, row) => (encoders[hwIdx] = row));

  await window.pywebview!.api.save_hw_mapping(buttons, slots, encoders);
  step.value = 3;
}

async function cancel() {
  stopEventPolling();
  await window.pywebview!.api.hw_test_stop();
  emit("close");
}

onUnmounted(stopEventPolling);

start();
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
    <div class="bg-background border rounded-xl shadow-lg w-[420px] p-6 flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold">Hardware kalibrieren</h2>
        <button class="text-muted-foreground hover:text-foreground" @click="cancel">
          <X class="size-4" />
        </button>
      </div>

      <p v-if="error" class="text-xs text-destructive">{{ error }}</p>

      <!-- Schritt 1: Screens -->
      <template v-if="step === 0">
        <p class="text-sm text-muted-foreground">
          Auf jedem Display wird jetzt eine <b>Ziffer</b> angezeigt. Trage für
          jede Position ein, welche Ziffer dort steht (Reihenfolge: oben links →
          unten rechts, Encoder zählen nicht).
        </p>
        <div class="grid grid-cols-2 gap-2">
          <div v-for="(d, i) in digits" :key="i" class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground w-24"
              >Reihe {{ Math.floor(i / 2) + 1 }},
              {{ i % 2 === 0 ? "links" : "rechts" }}</span
            >
            <Input v-model="digits[i]" maxlength="1" class="w-12 text-center" />
          </div>
        </div>
        <Button @click="nextFromDigits">Weiter</Button>
      </template>

      <!-- Schritt 2: Buttons -->
      <template v-else-if="step === 1">
        <p class="text-sm text-muted-foreground">
          Drücke jetzt die <b>6 Buttons</b> nacheinander: oben links → oben
          rechts → Mitte links → … → unten rechts.
        </p>
        <div class="text-2xl font-mono text-center py-2">
          {{ buttonOrder.length }} / 6
        </div>
        <p v-if="buttonOrder.length" class="text-xs text-muted-foreground text-center">
          Erkannt: {{ buttonOrder.join(", ") }}
        </p>
        <p class="text-xs text-muted-foreground">
          Reagiert ein Button nicht, ist er vermutlich nicht (richtig)
          verkabelt — das ist dann ein Hardware-Problem.
        </p>
        <Button :disabled="buttonOrder.length < 6" @click="nextFromButtons">
          Weiter
        </Button>
      </template>

      <!-- Schritt 3: Encoder -->
      <template v-else-if="step === 2">
        <p class="text-sm text-muted-foreground">
          Drehe jetzt die <b>3 Encoder</b> nacheinander kurz: oben → Mitte →
          unten.
        </p>
        <div class="text-2xl font-mono text-center py-2">
          {{ encoderOrder.length }} / 3
        </div>
        <Button :disabled="encoderOrder.length < 3" @click="finish">
          Speichern
        </Button>
      </template>

      <!-- Fertig -->
      <template v-else>
        <p class="text-sm">
          Kalibrierung gespeichert. Die Displays zeigen jetzt wieder die aktive
          Konfiguration — Buttons, Labels und Encoder sollten passen.
        </p>
        <Button @click="emit('close')">Schließen</Button>
      </template>
    </div>
  </div>
</template>
