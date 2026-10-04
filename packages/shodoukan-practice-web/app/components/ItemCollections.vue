<script setup lang="ts">
import type { ItemKind } from '~/models/practice'

// The "Colecciones" section of a library item: the collections (tags) it's in,
// each removable, and an icon in the header that opens a searchable list of
// the others to add it to.
const props = defineProps<{ kind: ItemKind; itemId: number }>()

const { all, mine, busy, load, add, remove } = useItemCollections(() => props.kind, () => props.itemId)

watch(() => [props.kind, props.itemId], load, { immediate: true })

const available = computed(() => {
  const inside = new Set(mine.value.map(c => c.id))
  return (all.value ?? []).filter(c => !inside.has(c.id)).map(c => ({ label: c.name, value: c }))
})
const addTip = computed(() => (available.value.length ? 'Añadir a una colección' : 'Ya está en todas tus colecciones'))
</script>

<template>
  <section aria-labelledby="collections" class="space-y-2">
    <div class="flex items-center justify-between gap-2">
      <h2 id="collections" class="text-sm font-semibold uppercase tracking-wide text-muted">Colecciones</h2>
      <UTooltip v-if="all?.length" :text="addTip">
        <USelectMenu
          :items="available"
          value-key="value"
          :model-value="undefined"
          icon="i-lucide-folder-plus"
          trailing-icon=""
          color="neutral"
          variant="ghost"
          size="sm"
          :aria-label="addTip"
          :content="{ align: 'end' }"
          :ui="{ content: 'min-w-56' }"
          :search-input="{ placeholder: 'Buscar colección…' }"
          :disabled="busy || !available.length"
          @update:model-value="collection => collection && add(collection)"
        />
      </UTooltip>
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
    <p v-if="all && !all.length" class="text-sm text-muted">
      Aún no tienes colecciones. <ULink to="/collections" class="text-primary">Crea una</ULink>.
    </p>
  </section>
</template>
