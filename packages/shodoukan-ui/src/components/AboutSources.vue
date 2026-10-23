<script setup lang="ts">
import { computed } from 'vue'

// What shodoukan is, the data it's built on (with each licence) and what
// inspired it. Every app links to it once instead of crediting sources next to
// the data: a new source goes here.

const props = withDefaults(defineProps<{ lang?: 'en' | 'es' }>(), { lang: 'en' })

type Text = Record<'en' | 'es', string>

interface Source {
  name: string
  use: Text
  author: string
  url: string
  license: string
  licenseUrl: string
}

const CC_BY_SA_4 = 'https://creativecommons.org/licenses/by-sa/4.0/'

const SOURCES: Source[] = [
  {
    name: 'JMdict',
    use: {
      en: 'Words: spellings, readings, meanings in several languages and cross-references.',
      es: 'Palabras: escrituras, lecturas, significados en varios idiomas y referencias cruzadas.',
    },
    author: 'Electronic Dictionary Research and Development Group (EDRDG)',
    url: 'https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project',
    license: 'CC BY-SA 4.0',
    licenseUrl: CC_BY_SA_4,
  },
  {
    name: 'KANJIDIC2',
    use: {
      en: 'Kanji: on and kun readings, meanings, school grade, stroke count and frequency.',
      es: 'Kanji: lecturas on y kun, significados, curso escolar, número de trazos y frecuencia.',
    },
    author: 'Electronic Dictionary Research and Development Group (EDRDG)',
    url: 'https://www.edrdg.org/wiki/index.php/KANJIDIC_Project',
    license: 'CC BY-SA 4.0',
    licenseUrl: CC_BY_SA_4,
  },
  {
    name: 'RADKFILE / KRADFILE',
    use: {
      en: 'The radicals each kanji is made of.',
      es: 'Los radicales de los que se compone cada kanji.',
    },
    author: 'Electronic Dictionary Research and Development Group (EDRDG)',
    url: 'https://www.edrdg.org/krad/kradinf.html',
    license: 'CC BY-SA 4.0 (EDRDG licence)',
    licenseUrl: 'https://www.edrdg.org/edrdg/licence.html',
  },
  {
    name: 'KanjiVG',
    use: {
      en: 'Stroke order of kanji and kana, in Japanese order: diagrams, animations and step-by-step frames.',
      es: 'Orden de trazos de kanji y kana, en orden japonés: diagramas, animaciones y paso a paso.',
    },
    author: 'Ulrich Apel',
    url: 'https://kanjivg.tagaini.net/',
    license: 'CC BY-SA 3.0',
    licenseUrl: 'https://creativecommons.org/licenses/by-sa/3.0/',
  },
  {
    name: 'Tatoeba / Tanaka Corpus',
    use: {
      en: 'Example sentences (the Tanaka Corpus, included in JMdict) and their translations.',
      es: 'Frases de ejemplo (el Tanaka Corpus, incluido en JMdict) y sus traducciones.',
    },
    author: 'Tatoeba contributors',
    url: 'https://tatoeba.org/',
    license: 'CC BY 2.0 FR',
    licenseUrl: 'https://creativecommons.org/licenses/by/2.0/fr/',
  },
  {
    name: 'JLPT lists',
    use: {
      en: 'JLPT levels (N5–N1) of words and kanji, by Jonathan Waller (tanos.co.uk), converted by Bluskyo/JLPT_Vocabulary (MIT).',
      es: 'Niveles JLPT (N5–N1) de palabras y kanji, de Jonathan Waller (tanos.co.uk), convertidos por Bluskyo/JLPT_Vocabulary (MIT).',
    },
    author: 'Jonathan Waller',
    url: 'https://www.tanos.co.uk/jlpt/',
    license: 'CC BY',
    licenseUrl: 'https://creativecommons.org/licenses/by/4.0/',
  },
]

const TEXT = {
  en: {
    whatTitle: 'What it is',
    what: 'Shodoukan is an open-source Japanese dictionary: look up words and kanji by kanji, kana, romaji or meaning, in several languages, and practise them in your own library.',
    sourcesTitle: 'Data sources',
    sourcesIntro: 'Shodoukan is built on freely available data maintained by the Japanese language community.',
    website: 'Website',
    inspirationTitle: 'Inspiration',
    inspiration: 'The dictionary is inspired by',
  },
  es: {
    whatTitle: 'Qué es',
    what: 'Shodoukan es un diccionario de japonés de código abierto: busca palabras y kanji por kanji, kana, romaji o significado, en varios idiomas, y practícalos en tu propia librería.',
    sourcesTitle: 'Fuentes de datos',
    sourcesIntro: 'Shodoukan se basa en datos libres mantenidos por la comunidad del japonés.',
    website: 'Web',
    inspirationTitle: 'Inspiración',
    inspiration: 'El diccionario se inspira en',
  },
} satisfies Record<'en' | 'es', Record<string, string>>

const t = computed(() => TEXT[props.lang])
</script>

<template>
  <div class="flex flex-col gap-10">
    <section>
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {{ t.whatTitle }}
      </h2>
      <p class="text-zinc-300">
        {{ t.what }}
      </p>
    </section>

    <section>
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {{ t.sourcesTitle }}
      </h2>
      <p class="mb-4 text-zinc-400">
        {{ t.sourcesIntro }}
      </p>
      <div class="flex flex-col gap-4">
        <article
          v-for="source in SOURCES"
          :key="source.name"
          class="rounded-lg border border-zinc-800 bg-zinc-800/50 px-5 py-4"
          data-testid="source"
        >
          <h3 class="mb-1 font-semibold text-zinc-100">
            {{ source.name }}
          </h3>
          <p class="mb-2 text-sm text-zinc-300">
            {{ source.use[lang] }}
          </p>
          <div class="flex flex-wrap gap-x-6 gap-y-1 text-xs text-zinc-500">
            <span>{{ source.author }}</span>
            <a :href="source.url" target="_blank" rel="noopener" class="text-indigo-400 hover:text-indigo-300">{{ t.website }}</a>
            <a :href="source.licenseUrl" target="_blank" rel="noopener" class="text-indigo-400 hover:text-indigo-300">{{ source.license }}</a>
          </div>
        </article>
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        {{ t.inspirationTitle }}
      </h2>
      <p class="text-zinc-300">
        {{ t.inspiration }}
        <a href="https://jisho.org/" target="_blank" rel="noopener" class="text-indigo-400 hover:text-indigo-300">Jisho</a>.
      </p>
    </section>
  </div>
</template>
