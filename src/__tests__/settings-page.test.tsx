import { describe, expect, it } from 'vitest'
import { SettingsPage } from '../routes/settings-page'

describe('SettingsPage', () => {
  it('component can be referenced without crash', () => {
    expect(typeof SettingsPage).toBe('function')
  })
})
