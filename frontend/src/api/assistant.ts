import { request } from './client'

export interface AnswerSource {
  doc: string
  version: string
  section: string
}

export interface AssistantAnswer {
  text: string
  sources: AnswerSource[]
}

export function askAssistant(question: string) {
  return request<AssistantAnswer>('/assistant/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}
