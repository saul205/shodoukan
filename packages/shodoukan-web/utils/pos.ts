const POS_MAP: Record<string, string> = {
  // Add entries here: 'full JMDict description': 'Short label'
}

export function shortenPos(pos: string): string {
  return POS_MAP[pos] ?? pos
}
