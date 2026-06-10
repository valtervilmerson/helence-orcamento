import { useEffect, useState } from 'react'
import { getHealth } from './api/client'

type ApiStatus = 'loading' | 'ok' | 'error'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('loading')

  useEffect(() => {
    getHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  return (
    <main>
      <h1>Helence Orçamento</h1>
      <p>
        API:{' '}
        {apiStatus === 'loading' && 'verificando…'}
        {apiStatus === 'ok' && 'conectada ✅'}
        {apiStatus === 'error' && 'indisponível ❌'}
      </p>
    </main>
  )
}

export default App
