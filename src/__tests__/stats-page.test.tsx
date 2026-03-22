import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AbilityTrendChart } from '../routes/stats-page'

describe('AbilityTrendChart', () => {
  it('renders an empty state when ability data is missing', () => {
    expect(() => renderToStaticMarkup(<AbilityTrendChart ability={null as never} />)).not.toThrow()
    expect(renderToStaticMarkup(<AbilityTrendChart ability={null as never} />)).toContain('暂无能力数据')
  })
})
