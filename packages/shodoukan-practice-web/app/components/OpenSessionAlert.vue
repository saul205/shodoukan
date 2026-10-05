<script setup lang="ts">
// "Continuar": the user's open session, if any, to go back to it (after
// closing the tab, for instance).
const { session } = useOpenSession()
</script>

<template>
  <UAlert
    v-if="session"
    icon="i-lucide-circle-play"
    color="primary"
    variant="subtle"
    :title="`Tienes una sesión abierta de «${session.exercise_name}»`"
    :description="`${session.answered} respondidas · ${session.score} acertadas`"
    :actions="[{ label: 'Continuar', icon: 'i-lucide-arrow-right', to: `/exercise-sessions/${session.id}` }]"
    data-testid="open-session"
  />
</template>
