import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './brand/theme.css'
import './brand/components.css'
import './brand/application.css'
import { LaunchGate } from './brand/launch-gate'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LaunchGate><App /></LaunchGate>
  </StrictMode>,
)
