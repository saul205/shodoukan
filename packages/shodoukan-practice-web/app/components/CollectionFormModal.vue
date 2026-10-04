<script setup lang="ts">
import * as z from 'zod'
import type { Form, FormSubmitEvent } from '@nuxt/ui'
import type { Collection, ItemKind } from '~/models/practice'
import { createCollection, updateCollection } from '~/services/collections'
import { apiStatus } from '~/utils/api-error'

// Create a collection, or edit one when `collection` is given. Opened with
// `useOverlay()`; closes with the saved collection, or null if cancelled.
const props = defineProps<{ kind: ItemKind; collection?: Collection }>()
const emit = defineEmits<{ close: [saved: Collection | null] }>()

const api = useApi()
const notify = useNotify()

const schema = z.object({
  name: z.string().trim().min(1, 'Ponle un nombre.').max(100, 'Como mucho 100 caracteres.'),
  description: z.string().trim().max(500, 'Como mucho 500 caracteres.').optional(),
})
type Schema = z.output<typeof schema>

const state = reactive<Partial<Schema>>({
  name: props.collection?.name ?? '',
  description: props.collection?.description ?? '',
})
const form = useTemplateRef<Form<Schema>>('form')
const saving = ref(false)

const kindLabel = props.kind === 'entries' ? 'de palabras' : 'de kanji'
const title = props.collection ? 'Editar colección' : `Nueva colección ${kindLabel}`

async function onSubmit(event: FormSubmitEvent<Schema>) {
  const input = { name: event.data.name, description: event.data.description || null }
  saving.value = true
  try {
    const saved = props.collection
      ? await updateCollection(api, props.kind, props.collection.id, input)
      : await createCollection(api, props.kind, input)
    emit('close', saved)
  }
  catch (error) {
    if (apiStatus(error) === 409)
      form.value?.setErrors([{ name: 'name', message: 'Ya tienes una colección con ese nombre.' }])
    else
      notify.failure(error)
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal
    :title="title"
    :close="{ onClick: () => emit('close', null) }"
    :ui="{ footer: 'justify-end' }"
  >
    <template #body>
      <UForm id="collection-form" ref="form" :schema="schema" :state="state" class="space-y-4" @submit="onSubmit">
        <UFormField name="name" label="Nombre" required>
          <UInput v-model="state.name" class="w-full" autofocus placeholder="p. ej. Verbos, JLPT N5…" />
        </UFormField>
        <UFormField name="description" label="Descripción" hint="Opcional">
          <UTextarea v-model="state.description" class="w-full" :rows="2" autoresize />
        </UFormField>
      </UForm>
    </template>

    <template #footer>
      <UButton label="Cancelar" color="neutral" variant="outline" @click="emit('close', null)" />
      <UButton type="submit" form="collection-form" :label="collection ? 'Guardar' : 'Crear'" :loading="saving" />
    </template>
  </UModal>
</template>
