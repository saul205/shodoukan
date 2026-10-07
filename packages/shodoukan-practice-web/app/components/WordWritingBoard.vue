<script setup lang="ts">
import { KanjiStrokeDiagram, type KanjiStroke, type StrokePoint } from 'shodoukan-ui'
import FreeCell from '~/components/FreeCell.vue'
import GuidedCell from '~/components/GuidedCell.vue'
import { fitCells, type GuidedProgress } from '~/utils/writing-practice'

// A word (or a single character) written in one go, a cell per character.
// The cells are laid out as the largest grid the room allows (a row on a PC,
// two columns on a phone held upright: `fitCells`); when they'd be too small,
// one large cell at a time, with a row of small ones to move between them.
// Guided, the current cell is traced stroke by stroke and the next one takes
// over by itself; done cells show the model in ink, pending ones in grey.
// Free, any cell can be drawn in, and one Comprobar lays every drawing over
// its model. A character KanjiVG has no drawing for is shown, given. One row
// of controls serves every cell. Emits `done` once the word is written.
const props = defineProps<{ chars: string[]; strokes: (KanjiStroke[] | null)[]; guided: boolean }>()
const emit = defineEmits<{ done: [] }>()
/** Whether free cells show the model; the caller keeps it between words. */
const showModel = defineModel<boolean>('showModel', { default: true })

/** Misses on a stroke before it can be skipped. */
const MISSES_TO_SKIP = 3
const GAP = 12
/** Height of the row of small cells when one cell is drawn at a time. */
const ROW = 48

const drawable = (i: number) => Boolean(props.strokes[i]?.length)
const firstDrawable = () => props.chars.findIndex((_, i) => drawable(i))

const current = ref(Math.max(0, firstDrawable()))
const cellDone = ref<boolean[]>(props.chars.map(() => false))
const drawings = ref<StrokePoint[][][]>(props.chars.map(() => []))
const checked = ref(false)
const progress = ref<GuidedProgress | null>(null)
// The guided cell being written (only one at a time), for the controls.
type Guided = InstanceType<typeof GuidedCell>
const guidedCell = shallowRef<Guided | null>(null)
function setGuidedCell(cell: unknown) {
  guidedCell.value = (cell as Guided | null) ?? null
}

const finished = computed(() => (props.guided ? props.chars.every((_, i) => !drawable(i) || cellDone.value[i]) : checked.value))
onMounted(() => {
  // Nothing to draw (no character has a drawing): written as it is.
  if (firstDrawable() < 0) emit('done')
})

function onGuidedDone() {
  cellDone.value[current.value] = true
  const next = props.chars.findIndex((_, i) => i > current.value && drawable(i) && !cellDone.value[i])
  if (next >= 0) current.value = next
  else emit('done')
}

const anyDrawing = computed(() => drawings.value.some(d => d.length))

function check() {
  if (props.guided || checked.value || !anyDrawing.value) return
  checked.value = true
  emit('done')
}

function undo() {
  if (props.guided) return guidedCell.value?.undo()
  if (!checked.value) drawings.value[current.value] = drawings.value[current.value]!.slice(0, -1)
}

function clear() {
  if (!checked.value) drawings.value[current.value] = []
}

function move(step: number) {
  let i = current.value + step
  while (i >= 0 && i < props.chars.length && !drawable(i)) i += step
  if (i >= 0 && i < props.chars.length) current.value = i
}

const box = useTemplateRef<HTMLElement>('box')
const room = useMeasuredBox(box)
const grid = computed(() => fitCells(props.chars.length, room.value.width, room.value.height, GAP))
const singleSize = computed(() => Math.floor(Math.min(room.value.width, room.value.height - ROW - GAP)))
const shown = computed(() => (grid.value ? props.chars.map((_, i) => i) : [current.value]))
const size = computed(() => grid.value?.size ?? singleSize.value)

const status = computed(() => {
  if (!props.guided) return null
  if (finished.value) return '¡Hecho!'
  if (progress.value?.hint) return progress.value.hint
  const stroke = progress.value ? `Trazo ${progress.value.done + 1} de ${progress.value.total}` : ''
  return props.chars.length > 1 ? `${props.chars[current.value]} · ${stroke}` : stroke
})

defineExpose({ undo, check })
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2 sm:gap-3" data-testid="word-board">
    <div ref="box" class="relative min-h-0 flex-1">
      <div v-if="size > 0" class="absolute inset-0 flex flex-col items-center justify-center" :style="{ gap: `${GAP}px` }">
        <div v-if="!grid && chars.length > 1" class="flex max-w-full shrink-0 items-center gap-1.5 overflow-x-auto" data-testid="board-cells">
          <UButton
            v-if="!guided"
            icon="i-lucide-chevron-left"
            color="neutral"
            variant="ghost"
            aria-label="Carácter anterior"
            data-testid="board-previous"
            @click="move(-1)"
          />
          <button
            v-for="(c, i) in chars"
            :key="i"
            type="button"
            class="flex size-10 shrink-0 items-center justify-center rounded border font-japanese text-xl transition"
            :class="i === current
              ? 'border-primary bg-primary/10 text-highlighted'
              : cellDone[i] || drawings[i]!.length ? 'border-default text-highlighted' : 'border-default text-dimmed'"
            :disabled="guided || !drawable(i)"
            :aria-current="i === current ? 'step' : undefined"
            :aria-label="`Carácter ${i + 1}: ${c}`"
            data-testid="board-cell"
            @click="current = i"
          >
            {{ c }}
          </button>
          <UButton
            v-if="!guided"
            icon="i-lucide-chevron-right"
            color="neutral"
            variant="ghost"
            aria-label="Carácter siguiente"
            data-testid="board-next"
            @click="move(1)"
          />
        </div>

        <div
          class="grid justify-center"
          :style="{ gap: `${GAP}px`, gridTemplateColumns: `repeat(${grid?.columns ?? 1}, ${size}px)` }"
          :data-columns="grid?.columns ?? 0"
          data-testid="board-grid"
        >
          <div
            v-for="i in shown"
            :key="i"
            class="rounded"
            :class="{ 'ring-2 ring-primary/60': grid && chars.length > 1 && i === current && !finished }"
            data-testid="board-slot"
          >
            <div
              v-if="!drawable(i)"
              class="flex items-center justify-center rounded border border-zinc-700 bg-zinc-800/60 font-japanese text-dimmed"
              :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * 0.6}px` }"
              :title="`Sin orden de trazos para ${chars[i]}`"
              data-testid="board-given"
            >
              {{ chars[i] }}
            </div>
            <template v-else-if="guided">
              <GuidedCell
                v-if="i === current && !cellDone[i]"
                :ref="setGuidedCell"
                :key="`guided-${i}`"
                :strokes="strokes[i]!"
                :size="size"
                @progress="progress = $event"
                @done="onGuidedDone"
              />
              <KanjiStrokeDiagram
                v-else-if="cellDone[i]"
                :strokes="strokes[i]!"
                :numbers="false"
                :size="`${size}px`"
                data-testid="board-done"
              />
              <KanjiStrokeDiagram v-else :strokes="[]" :ghost="strokes[i]!" :numbers="false" :size="`${size}px`" data-testid="board-pending" />
            </template>
            <FreeCell
              v-else
              v-model="drawings[i]"
              :strokes="strokes[i]!"
              :size="size"
              :show-model="showModel"
              :checked="checked"
              @touch="current = i"
            />
          </div>
        </div>
      </div>
    </div>

    <p v-if="status" class="min-h-5 shrink-0 text-center text-sm" :class="progress?.hint && !finished ? 'text-warning' : 'text-muted'" data-testid="guided-status">
      {{ status }}
    </p>

    <div v-if="guided && !finished" class="flex min-h-10 shrink-0 flex-wrap items-center gap-2">
      <UButton
        icon="i-lucide-undo-2"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Deshacer el último trazo"
        :disabled="!progress?.done"
        data-testid="undo"
        @click="undo"
      />
      <UButton
        icon="i-lucide-rotate-ccw"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Empezar el carácter de nuevo"
        :disabled="!progress?.done"
        data-testid="restart"
        @click="guidedCell?.restart()"
      />
      <UButton
        label="Saltar trazo"
        icon="i-lucide-skip-forward"
        color="neutral"
        variant="outline"
        size="lg"
        class="ml-auto"
        :disabled="(progress?.misses ?? 0) < MISSES_TO_SKIP"
        data-testid="skip-stroke"
        @click="guidedCell?.skip()"
      />
    </div>

    <div v-else-if="!guided && !checked" class="flex min-h-10 shrink-0 flex-wrap items-center gap-2">
      <USwitch v-model="showModel" label="Modelo" class="mr-1" data-testid="show-model" />
      <UButton
        icon="i-lucide-undo-2"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Deshacer el último trazo"
        :disabled="!drawings[current]?.length"
        data-testid="undo"
        @click="undo"
      />
      <UButton
        icon="i-lucide-eraser"
        color="neutral"
        variant="outline"
        size="lg"
        aria-label="Borrar el carácter"
        :disabled="!drawings[current]?.length"
        data-testid="clear"
        @click="clear"
      />
      <UButton
        label="Comprobar"
        icon="i-lucide-check"
        size="lg"
        class="ml-auto"
        :disabled="!anyDrawing"
        data-testid="check"
        @click="check"
      >
        <template #trailing>
          <UKbd value="enter" class="hidden sm:inline-flex" />
        </template>
      </UButton>
    </div>
  </div>
</template>
