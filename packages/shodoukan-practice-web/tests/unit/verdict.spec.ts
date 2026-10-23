import { describe, expect, it } from 'vitest'
import { strokeProblem, verdictOf } from '../../app/utils/verdict'
import { drawingQuestion, drawn, graded, question, wordQuestion, writtenWord } from '../fixtures-sessions'

describe('verdictOf', () => {
  it('tells right, close, wrong and skipped apart', () => {
    expect(verdictOf(graded(question(1), 0))).toBe('correct')
    expect(verdictOf(graded(question(1), 1))).toBe('wrong')
    expect(verdictOf(drawn(drawingQuestion(1), 'close'))).toBe('close')
    expect(verdictOf(drawn(drawingQuestion(1), 'wrong'))).toBe('wrong')
    expect(verdictOf(writtenWord(wordQuestion(1), 'close'))).toBe('close')
    expect(verdictOf({ ...drawingQuestion(1), answered: true, answer: { type: 'skip' }, is_correct: false })).toBe('skipped')
  })
})

describe('strokeProblem', () => {
  it('says what is wrong with a stroke, numbered from 1', () => {
    expect(strokeProblem({ drawn: 0, reference: 0, status: 'ok' })).toBeNull()
    expect(strokeProblem({ drawn: 2, reference: 1, status: 'out_of_order' })).toBe('Trazo 3: fuera de orden (es el 2.º).')
    expect(strokeProblem({ drawn: null, reference: 3, status: 'missing' })).toBe('Falta el trazo 4.')
    expect(strokeProblem({ drawn: 1, reference: 1, status: 'too_long' })).toBe('Trazo 2: demasiado largo.')
    expect(strokeProblem({ drawn: 0, reference: 0, status: 'too_short' })).toBe('Trazo 1: demasiado corto.')
  })
})
