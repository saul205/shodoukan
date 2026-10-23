<script setup lang="ts">
definePageMeta({ layout: false })

const auth = useAuth()
const failed = ref(false)

onMounted(async () => {
  try {
    await navigateTo(await auth.completeLogin(), { replace: true })
  }
  catch {
    failed.value = true
  }
})
</script>

<template>
  <div class="flex min-h-dvh items-center justify-center p-4">
    <UCard v-if="failed" class="w-full max-w-sm">
      <div class="space-y-4 text-center">
        <p class="text-highlighted">No se ha podido iniciar sesión.</p>
        <UButton label="Volver a intentarlo" icon="i-lucide-log-in" @click="auth.login('/')" />
      </div>
    </UCard>
    <div v-else class="flex items-center gap-2 text-muted">
      <UIcon name="i-lucide-loader-circle" class="size-5 animate-spin" />
      Iniciando sesión…
    </div>
  </div>
</template>
