const WIKI_LINK_RE = /\[\[(.+?)\]\]/g

export function extractConceptRefs(body: string): string[] {
  if (!body) {
    return []
  }

  const matches = body.matchAll(WIKI_LINK_RE)
  return [...new Set([...matches].map((match) => match[1]))]
}
