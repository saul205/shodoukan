<script setup lang="ts">
// The sources page was merged into About. A page redirect, not a route rule:
// this is a static SPA, so the redirect has to happen in the browser.
definePageMeta({ redirect: '/about' })
</script>

<template>
  <div />
</template>
