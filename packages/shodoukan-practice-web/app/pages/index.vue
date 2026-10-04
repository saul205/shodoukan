<script setup lang="ts">
const auth = useAuth()

const sections = [
  {
    title: 'Diccionario',
    description: 'Busca palabras y kanji por kanji, kana, romaji o significado, e impórtalos a tu librería.',
    icon: 'i-lucide-book-open',
    to: '/dictionary',
  },
  {
    title: 'Mi librería',
    description: 'Tus palabras y kanji: oculta lo que no necesitas, añade tus propios significados y notas.',
    icon: 'i-lucide-library-big',
    to: '/library',
  },
  {
    title: 'Mis colecciones',
    description: 'Agrupa elementos de tu librería para estudiarlos juntos. Funcionan también como etiquetas.',
    icon: 'i-lucide-folders',
    to: '/collections',
  },
  {
    title: 'Ejercicios',
    description: 'Practica tus colecciones con tarjetas: elige qué se muestra y qué se pregunta.',
    icon: 'i-lucide-dumbbell',
    to: '/exercises',
  },
]
</script>

<template>
  <AppPanel title="Inicio">
    <div class="space-y-6">
      <div>
        <h1 class="text-2xl font-semibold text-highlighted">
          Hola{{ auth.username.value ? `, ${auth.username.value}` : '' }}
        </h1>
        <p class="mt-1 text-muted">¿Por dónde quieres empezar?</p>
      </div>

      <UPageGrid class="lg:grid-cols-2 xl:grid-cols-4">
        <UPageCard
          v-for="section in sections"
          :key="section.to"
          v-bind="section"
          spotlight
        />
      </UPageGrid>
    </div>
  </AppPanel>
</template>
