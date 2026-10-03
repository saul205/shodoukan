<script setup lang="ts">
import type { Collection, ItemKind } from '~/models/practice'
import { addToCollection, listCollections, removeFromCollection } from '~/services/collections'
import { getEntryCollections, getKanjiCollections } from '~/services/library'

// The collections (tags) a library item is in, with adding and removing.
const props = defineProps<{ kind: ItemKind; itemId: number }>()

const api = useApi()
const notify = useNotify()

const { data, refresh } = useAsyncData(
  () => `item-collections-${props.kind}-${props.itemId}`,
  async () => {
    const [mine, all] = await Promise.all([
      props.kind === 'entries' ? getEntryCollections(api, props.itemId) : getKanjiCollections(api, props.itemId),
      listCollections(api, props.kind),
    ])
    return { mine, all }
  },
)

const available = computed(() => {
  const inside = new Set(data.value?.mine.map(c => c.id))
  return (data.value?.all ?? []).filter(c => !inside.has(c.id)).map(c => ({ label: c.name, value: c.id }))
})

const busy = ref(false)

async function add(collectionId: number | undefined) {
  if (collectionId === undefined) return
  await run(() => addToCollection(api, props.kind, collectionId, props.itemId))
}

async function remove(collection: Collection) {
  await run(() => removeFromCollection(api, props.kind, collection.id, props.itemId))
}

async function run(action: () => Promise<void>) {
  busy.value = true
  try {
    await action()
    await refresh()
  }
  catch (error) {
    notify.failure(error)
  }
  finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="space-y-3">
    <div v-if="data?.mine.length" class="flex flex-wrap gap-2">
      <UBadge
        v-for="collection in data.mine"
        :key="collection.id"
        color="primary"
        variant="soft"
        class="gap-1"
      >
        <NuxtLink :to="`/collections/${kind}/${collection.id}`" class="hover:underline">{{ collection.name }}</NuxtLink>
        <UButton
          icon="i-lucide-x"
          color="primary"
          variant="link"
          size="xs"
          class="p-0"
          :aria-label="`Quitar de ${collection.name}`"
          :disabled="busy"
          @click="remove(collection)"
        />
      </UBadge>
    </div>
    <p v-else class="text-sm text-muted">No está en ninguna colección.</p>

    <USelectMenu
      v-if="available.length"
      :items="available"
      value-key="value"
      :model-value="undefined"
      placeholder="Añadir a una colección…"
      icon="i-lucide-folder-plus"
      class="w-full"
      :disabled="busy"
      @update:model-value="add"
    />
    <p v-else-if="data && !data.all.length" class="text-sm text-muted">
      Aún no tienes colecciones. <ULink to="/collections" class="text-primary">Crea una</ULink>.
    </p>
  </div>
</template>
