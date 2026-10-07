<script setup lang="ts">
import { KanjiDrawingPad, KanjiStrokeDiagram, KANJIVG_STROKE_WIDTH, pointsToPath, type KanjiStroke, type StrokePoint } from 'shodoukan-ui'
import { MAX_STROKE_POINTS, MAX_STROKES } from '~/utils/drawing'

// Free writing: draw the whole character, over its model in grey or (with
// the model hidden) from memory. Comprobar lays the drawing over the model,
// strokes numbered, with no grade: the point is to see where it strays.
// Emits `done` when checked.
const props = defineProps<{ strokes: KanjiStroke[] }>()
const emit = defineEmits<{ done: [] }>()
/** Whether the model shows under the pad; the caller keeps it between characters. */
const showModel = defineModel<boolean>('showModel', { default: true })

const drawing = ref<StrokePoint[][]>([])
const checked = ref(false)

const drawn = computed(() => drawing.value.map(points => ({ path: pointsToPath(points), label: points[0] ?? null })))

function check() {
  if (!drawing.value.length || checked.value) return
  checked.value = true
  emit('done')
}

function undo() {
  if (!checked.value) drawing.value = drawing.value.slice(0, -1)
}

function clear() {
  if (!checked.value) drawing.value = []
}

const padBox = useTemplateRef<HTMLElement>('padBox')
const room = useMeasuredBox(padBox)
const padSize = computed(() => Math.floor(Math.min(room.value.width, room.value.height)))

defineExpose({ check, undo })
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2 sm:gap-3">
    <div ref="padBox" class="relative min-h-0 flex-1" data-testid="pad-box">
      <div class="absolute inset-0 flex items-center justify-center">
        <template v-if="padSize > 0">
          <KanjiStrokeDiagram
            v-if="checked"
            :strokes="drawn"
            :ghost="strokes"
            :size="`${padSize}px`"
            data-testid="free-result"
          />
          <KanjiDrawingPad
            v-else
            v-model="drawing"
            :size="`${padSize}px`"
            :max-strokes="MAX_STROKES"
            :max-points="MAX_STROKE_POINTS"
          >
            <template #background>
              <g
                v-if="showModel"
                fill="none"
                :stroke-width="KANJIVG_STROKE_WIDTH"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke="#52525b"
                data-model
              >
                <path v-for="(stroke, i) in strokes" :key="i" :d="stroke.path" />
              </g>
            </template>
          </KanjiDrawingPad>
        </template>
      </div>
    </div>

    <p class="min-h-5 shrink-0 text-center text-sm text-muted" data-testid="free-status">
      <template v-if="checked">
        {{ drawing.length === 1 ? '1 trazo' : `${drawing.length} trazos` }} · el modelo tiene {{ strokes.length }}
      </template>
      <USwitch v-else v-model="showModel" label="Mostrar el modelo" class="inline-flex" data-testid="show-model" />
    </p>

    <div v-if="!checked" class="flex min-h-10 shrink-0 flex-wrap items-center gap-2">
      <UButton
        icon="i-lucide-undo-2"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Deshacer el último trazo"
        :disabled="!drawing.length"
        data-testid="undo"
        @click="undo"
      />
      <UButton
        icon="i-lucide-eraser"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Borrar el dibujo"
        :disabled="!drawing.length"
        data-testid="clear"
        @click="clear"
      />
      <UButton
        label="Comprobar"
        icon="i-lucide-check"
        size="lg"
        class="ml-auto"
        :disabled="!drawing.length"
        data-testid="check"
        @click="check"
      />
    </div>
  </div>
</template>
