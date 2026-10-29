<script setup lang="ts">
import * as z from 'zod'
import type { Form, FormSubmitEvent } from '@nuxt/ui'
import type { Direction, Exercise, ExerciseInput, ExerciseSettings, ExerciseType, ItemKind, StudyField } from '~/models/practice'
import { listCollections } from '~/services/collections'
import { createExercise, updateExercise } from '~/services/exercises'
import { apiStatus } from '~/utils/api-error'
import {
  defaultChoiceSettings,
  defaultHandwritingSettings,
  defaultSentenceSettings,
  directionKey,
  EXERCISE_TYPE_LABELS,
  EXERCISE_TYPES,
  fieldItems,
  HANDWRITING_ANSWERS,
  ITEM_KIND_LABELS,
  SENTENCE_DIRECTION_LABELS,
  SENTENCE_DIRECTIONS,
} from '~/utils/study-fields'

// Create an exercise, or edit one when `exercise` is given (its item kind
// can't change then). Both kinds choose between a choice card and writing by
// hand, which asks for something to write (the kanji; a word's spelling or
// reading) and has no options; words can also be asked in their sentences
// (fill the gap, or the word's reading or meaning), picked as checkboxes. It saves on its own and emits `saved`; the
// rules mirror the backend's so mistakes show on their field.
const props = defineProps<{ exercise?: Exercise }>()
const emit = defineEmits<{ saved: [exercise: Exercise] }>()

const api = useApi()
const notify = useNotify()

const field = z.enum(['writing', 'reading', 'meaning', 'literal', 'onyomi', 'kunyomi'])

const schema = z.object({
  name: z.string().trim().min(1, 'Ponle un nombre.').max(100, 'Como mucho 100 caracteres.'),
  description: z.string().trim().optional(),
  item_kind: z.enum(['entries', 'kanji']),
  type: z.enum(['card.choice', 'card.handwriting', 'sentence.choice']),
  collection_ids: z.array(z.number()).min(1, 'Elige al menos una colección.'),
  directions: z
    .array(z.object({ prompt: z.array(field), answer: field }))
    .superRefine((directions, ctx) => {
      const problem = directionsProblem(directions)
      if (problem) ctx.addIssue({ code: 'custom', message: problem })
    }),
  back_fields: z.array(field),
  option_count: z.number().int().min(2, 'Al menos 2 opciones.').max(8, 'Como mucho 8 opciones.'),
  show_translation: z.boolean(),
})
type Schema = z.output<typeof schema>

function directionsProblem(directions: Direction[]): string | undefined {
  if (!directions.length) return 'Añade al menos una dirección.'
  if (directions.some(direction => !direction.prompt.length))
    return 'Cada dirección necesita al menos un campo a mostrar.'
  if (directions.some(direction => direction.prompt.includes(direction.answer)))
    return 'Una dirección no puede preguntar un campo que muestra.'
  if (new Set(directions.map(directionKey)).size !== directions.length)
    return 'Hay direcciones repetidas.'
}

function defaults(kind: ItemKind, type: ExerciseType): ExerciseSettings {
  if (type === 'sentence.choice') return defaultSentenceSettings()
  return type === 'card.handwriting' ? defaultHandwritingSettings(kind) : defaultChoiceSettings(kind)
}

const initialKind: ItemKind = props.exercise?.item_kind ?? 'entries'
const initialSettings = props.exercise?.settings ?? defaultChoiceSettings(initialKind)

const state = reactive<Schema>({
  name: props.exercise?.name ?? '',
  description: props.exercise?.description ?? '',
  item_kind: initialKind,
  type: initialSettings.type,
  collection_ids: [...(props.exercise?.collection_ids ?? [])],
  directions: initialSettings.directions.map(direction => ({ ...direction, prompt: [...direction.prompt] })),
  back_fields: [...initialSettings.back_fields],
  option_count: initialSettings.type === 'card.handwriting' ? 4 : initialSettings.option_count,
  show_translation: initialSettings.type === 'sentence.choice' ? initialSettings.show_translation : false,
})
const form = useTemplateRef<Form<Schema>>('form')
const saving = ref(false)

function resetFields(settings: ExerciseSettings) {
  state.directions = settings.directions
  state.back_fields = settings.back_fields
}

// Collections and fields belong to one item kind: switching starts them over.
watch(() => state.item_kind, (kind) => {
  state.collection_ids = []
  state.type = 'card.choice'
  resetFields(defaultChoiceSettings(kind))
})

// Directions differ by type (handwriting asks for something to write):
// switching starts them over too.
watch(() => state.type, (type, previous) => {
  if (type !== previous) resetFields(defaults(state.item_kind, type))
})

const { data: collections, status: collectionsStatus, refresh: refreshCollections } = useAsyncData(
  () => `exercise-form-collections-${state.item_kind}`,
  () => listCollections(api, state.item_kind),
  { watch: [() => state.item_kind] },
)
const collectionItems = computed(() =>
  (collections.value ?? []).map(collection => ({ label: collection.name, value: collection.id })),
)

const typeItems = computed(() =>
  EXERCISE_TYPES[state.item_kind].map(type => ({ label: EXERCISE_TYPE_LABELS[type], value: type })),
)
const handwriting = computed(() => state.type === 'card.handwriting')
const sentences = computed(() => state.type === 'sentence.choice')

// A sentence exercise's directions, as the answers they ask.
const sentenceItems = SENTENCE_DIRECTIONS.map(d => ({ label: SENTENCE_DIRECTION_LABELS[d.answer]!, value: d.answer }))
const sentenceAnswers = computed<StudyField[]>({
  get: () => state.directions.map(d => d.answer),
  set: answers => {
    state.directions = SENTENCE_DIRECTIONS
      .filter(d => answers.includes(d.answer))
      .map(d => ({ ...d, prompt: [...d.prompt] }))
  },
})

const kindItems = (['entries', 'kanji'] as const).map(kind => ({ label: ITEM_KIND_LABELS[kind], value: kind }))
const backItems = computed(() => fieldItems(state.item_kind))

function settingsOf(data: Schema): ExerciseSettings {
  if (data.type === 'card.handwriting')
    return { type: 'card.handwriting', directions: data.directions, back_fields: data.back_fields }
  if (data.type === 'sentence.choice') {
    return {
      type: 'sentence.choice',
      directions: data.directions,
      back_fields: data.back_fields,
      option_count: data.option_count,
      show_translation: data.show_translation,
    }
  }
  return {
    type: 'card.choice',
    directions: data.directions,
    back_fields: data.back_fields,
    option_count: data.option_count,
    distractor_source: 'collection',
  }
}

async function onSubmit(event: FormSubmitEvent<Schema>) {
  const data = event.data
  const input: ExerciseInput = {
    name: data.name,
    description: data.description || null,
    collection_ids: data.collection_ids,
    settings: settingsOf(data),
  }
  saving.value = true
  try {
    const saved = props.exercise
      ? await updateExercise(api, props.exercise.id, input)
      : await createExercise(api, { ...input, item_kind: data.item_kind })
    emit('saved', saved)
  }
  catch (error) {
    if (apiStatus(error) === 404) {
      // A collection was deleted meanwhile (or the exercise itself).
      form.value?.setErrors([{ name: 'collection_ids', message: 'Alguna colección ya no existe; vuelve a elegirlas.' }])
      await refreshCollections()
    }
    else {
      notify.failure(error)
    }
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <UForm id="exercise-form" ref="form" :schema="schema" :state="state" class="space-y-6" @submit="onSubmit">
    <div class="grid gap-4 sm:grid-cols-2">
      <UFormField name="name" label="Nombre" required>
        <UInput v-model="state.name" class="w-full" placeholder="p. ej. Verbos: significado" />
      </UFormField>
      <UFormField
        name="item_kind"
        label="Qué estudia"
        :description="exercise ? 'No se puede cambiar.' : undefined"
      >
        <URadioGroup
          v-model="state.item_kind"
          :items="kindItems"
          orientation="horizontal"
          :disabled="!!exercise"
        />
      </UFormField>
    </div>

    <UFormField
      v-if="typeItems.length > 1"
      name="type"
      label="Ejercicio"
      description="Elegir la respuesta entre varias opciones, dibujarla, o ver cada palabra en una de sus frases."
    >
      <URadioGroup v-model="state.type" :items="typeItems" orientation="horizontal" data-testid="exercise-type" />
    </UFormField>

    <UFormField name="description" label="Descripción" hint="Opcional">
      <UTextarea v-model="state.description" class="w-full" :rows="2" autoresize />
    </UFormField>

    <UFormField
      name="collection_ids"
      label="Colecciones"
      description="Los elementos activos de estas colecciones; uno que esté en varias cuenta una vez."
      required
    >
      <USelectMenu
        v-model="state.collection_ids"
        :items="collectionItems"
        value-key="value"
        multiple
        :loading="collectionsStatus === 'pending'"
        placeholder="Elige colecciones"
        class="w-full"
      />
      <template v-if="collectionsStatus === 'success' && !collectionItems.length" #help>
        No tienes colecciones {{ state.item_kind === 'entries' ? 'de palabras' : 'de kanji' }}.
        <ULink to="/collections" class="text-primary">Crea una</ULink> primero.
      </template>
    </UFormField>

    <UFormField
      v-if="sentences"
      name="directions"
      label="Qué se pregunta"
      description="Cada pregunta muestra la palabra en una de sus frases y usa una de estas al azar. Rellenar el hueco da su significado como pista."
      required
    >
      <UCheckboxGroup v-model="sentenceAnswers" :items="sentenceItems" data-testid="sentence-directions" />
    </UFormField>

    <UFormField
      v-else
      name="directions"
      label="Direcciones"
      description="Qué se muestra → qué se pregunta. Cada tarjeta usa una de ellas al azar."
      required
    >
      <DirectionsEditor
        v-model="state.directions"
        :kind="state.item_kind"
        :answer-fields="handwriting ? HANDWRITING_ANSWERS[state.item_kind] : undefined"
      />
    </UFormField>

    <UFormField
      name="back_fields"
      label="Reverso"
      description="Qué más se muestra al dar la vuelta a la tarjeta, además de la pregunta y la respuesta."
    >
      <UCheckboxGroup v-model="state.back_fields" :items="backItems" orientation="horizontal" />
    </UFormField>

    <UFormField v-if="!handwriting" name="option_count" label="Opciones por tarjeta" description="La correcta y las incorrectas, de 2 a 8.">
      <UInputNumber v-model="state.option_count" :min="2" :max="8" class="w-32" />
    </UFormField>

    <UFormField v-if="sentences" name="show_translation">
      <USwitch
        v-model="state.show_translation"
        label="Mostrar la traducción"
        description="La de la frase en tu idioma, si la tiene."
      />
    </UFormField>

    <div class="flex justify-end gap-2">
      <UButton label="Cancelar" color="neutral" variant="outline" to="/exercises" />
      <UButton type="submit" :label="exercise ? 'Guardar' : 'Crear'" :loading="saving" />
    </div>
  </UForm>
</template>
