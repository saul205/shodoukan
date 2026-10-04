import type { Component } from 'vue'
import type { QuestionType } from '~/models/practice'
import ChoiceCardPlayer from './ChoiceCardPlayer.vue'

/**
 * The component that plays each question type. A player takes `question`
 * and `busy`, and emits `answer(answer, responseMs)`, `next` and
 * `open-item(itemId)`; the session page does the requests.
 */
export const PLAYERS: Record<QuestionType, Component> = {
  'card.choice': ChoiceCardPlayer,
}
