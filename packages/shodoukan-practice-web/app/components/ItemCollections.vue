<script setup lang="ts">
import type { ItemKind } from '~/models/practice'

// The "Colecciones" section of a library item: the collections (tags) it's in,
// each removable, and a `CollectionPicker` in the header to add it to another
// one or to a new one.
const props = defineProps<{ kind: ItemKind; itemId: number }>()

const { all, mine, busy, load, add, remove, create } = useItemCollections(() => props.kind, () => props.itemId)

watch(() => [props.kind, props.itemId], load, { immediate: true })

async function createAndAdd(name: string) {
  const created = await create(name)
  if (created) await add(created)
}
</script>

<template>
  <section aria-labelledby="collections" class="space-y-2">
    <div class="flex items-center justify-between gap-2">
      <h2 id="collections" class="text-sm font-semibold uppercase tracking-wide text-muted">Colecciones</h2>
      <CollectionPicker
        :collections="all"
        :selected="mine"
        :disabled="busy"
        @add="add"
        @create="createAndAdd"
      />
    </div>

    <div v-if="mine.length" class="flex flex-wrap gap-2">
      <UBadge
        v-for="collection in mine"
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
    <p v-else-if="all?.length" class="text-sm text-muted">No está en ninguna colección.</p>
    <p v-else-if="all" class="text-sm text-muted">Aún no tienes colecciones.</p>
  </section>
</template>
