// Aavkar Educational Motion Studio (AEM): one plugin, its features composed here.
// Each feature registers its own hooks; all of them call the aem CLI for decisions.
import type { Register } from 'claude-code'

import { context } from './context'

export const register: Register = (on, options) => {
  context(on, options)
}
