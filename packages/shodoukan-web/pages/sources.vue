<script setup lang="ts">
const sources = [
  {
    name: 'JMDict',
    description:
      'Japanese-Multilingual Dictionary. ~400k entries with words, readings, multilingual glosses, and example sentences.',
    maintainer: 'Electronic Dictionary Research and Development Group (EDRDG)',
    url: 'https://www.edrdg.org/jmdict/j_jmdict.html',
    license: 'CC BY-SA 4.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/',
  },
  {
    name: 'KANJIDIC2',
    description:
      'Kanji dictionary with ~13k characters. Includes on/kun readings, meanings in multiple languages, school grade, frequency rank, and JLPT level.',
    maintainer: 'Electronic Dictionary Research and Development Group (EDRDG)',
    url: 'https://www.edrdg.org/wiki/index.php/KANJIDIC_Project',
    license: 'CC BY-SA 4.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/4.0/',
  },
  {
    name: 'KanjiVG',
    description:
      'Stroke order SVG data for kanji characters, used to show stroke order diagrams on kanji detail pages.',
    maintainer: 'Ulrich Apel',
    url: 'https://kanjivg.tagaini.net/',
    license: 'CC BY-SA 3.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/3.0/',
  },
]
</script>

<template>
  <main class="mx-auto max-w-2xl px-6 py-16">
    <h1 class="mb-2 text-3xl font-bold text-zinc-100">
      Data Sources
    </h1>
    <p class="mb-10 text-zinc-400">
      Shodoukan is built on freely available datasets maintained by the Japanese language community.
    </p>

    <div class="flex flex-col gap-8">
      <article
        v-for="src in sources"
        :key="src.name"
        class="rounded-lg border border-zinc-800 bg-zinc-800/50 px-6 py-5"
      >
        <h2 class="mb-1 text-lg font-semibold text-zinc-100">
          {{ src.name }}
        </h2>
        <p class="mb-3 text-sm text-zinc-300">
          {{ src.description }}
        </p>
        <div class="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500">
          <span>{{ src.maintainer }}</span>
          <a
            :href="src.url"
            target="_blank"
            rel="noopener"
            class="text-indigo-400 hover:text-indigo-300"
          >Website</a>
          <a
            :href="src.licenseUrl"
            target="_blank"
            rel="noopener"
            class="text-indigo-400 hover:text-indigo-300"
          >{{ src.license }}</a>
        </div>
      </article>
    </div>
  </main>
</template>
