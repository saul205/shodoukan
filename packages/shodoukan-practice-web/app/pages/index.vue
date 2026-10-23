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
    title: 'Practicar',
    description: 'Aprende a escribir tus kanji: guiado trazo a trazo, calcando el modelo o de memoria.',
    icon: 'i-lucide-pen-line',
    to: '/practice',
  },
  {
    title: 'Ejercicios',
    description: 'Practica tus colecciones con tarjetas: elige qué se muestra y qué se pregunta.',
    icon: 'i-lucide-dumbbell',
    to: '/exercises',
  },
  {
    title: 'Estadísticas',
    description: 'Cuánto practicas, cómo vas en cada ejercicio y qué palabras y kanji fallas más.',
    icon: 'i-lucide-chart-column',
    to: '/statistics',
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

      <OpenSessionAlert />

      <UPageGrid class="lg:grid-cols-3">
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
