# Sentences

[← Functional documentation](../README.md)

Sentences are part of the library, like words and kanji. Each one is linked to the
words of the library it uses: every linked word is underlined and is a **gap** the
exercises can ask about (fill it in, read it, say what it means). A sentence can use
several of the user's words, and a word has as many sentences as the user gives it.

## Where sentences come from

- **With the words.** Importing a word from the dictionary brings its example
  sentences, already linked to it and analyzed. A sentence the user already has from
  another word isn't added twice: it gets this word as one more of its words.
- **The user's own.** On a word's page, each meaning group has **Añadir una frase
  propia**: a sentence in Japanese and, optionally, its translation in the language
  chosen in the side menu. The word is found in it even when the sentence inflects it
  (食べた for 食べる).
- **In bulk.** **Frases → Añadir frases**: paste the sentences one per line, with a
  translation after a tab if wanted, and press **Analizar**. Each sentence comes back
  with the words of the library it uses underlined, and a summary per row: how many
  are linked, how many are doubtful (found only in kana, like はし, which may be 橋 or
  箸: shown in another colour and left out until confirmed) and a warning when it uses
  none. Opening a row shows its words: confirm one, pick the right word when several
  fit, or mark another word by clicking it. **Guardar todas** stores them all at once;
  nothing is stored before.
- **With a collection.** Importing a shared collection brings the sentences the owner
  gave its words (see [sharing collections](../collections/share.md)).

## The sentences section

**Frases** in the side menu lists every sentence of the library, newest first, with a
search (in the sentence or its translation) and a filter: all, those with no linked
word, hidden ones. Each opens in the **sentence editor**:

- The sentence, with its words underlined; the user's own can be rewritten (its words
  keep their gap where their text still is).
- **Marcar una palabra**: click a word of the sentence to make it a gap.
- **Palabras de tu librería en esta frase**: the words of the library it uses that
  aren't linked yet, to link with one click.
- **Sus palabras**: each gap, what the analyzer says it is (its dictionary form and
  reading in context, which can be corrected: 今日 may be read きょう or こんにち) and
  the word of the library it's linked to, which can be changed or removed. A linked
  word without a gap ("Sin hueco") isn't asked until it's marked.
- A switch to hide it from the exercises, a note, and deleting it (only the user's own:
  a dictionary sentence can only be hidden).

On a word's page, its sentences show under the meaning group they're linked to, with
the word underlined, and open in the editor.
