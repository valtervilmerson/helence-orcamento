/**
 * Wrapper de `fetch` com retentativas em caso de falha de rede.
 *
 * No primeiro carregamento da página, o Chromium às vezes recusa a
 * conexão para chamadas cross-origin disparadas durante a montagem
 * inicial dos componentes (TypeError: Failed to fetch / net::ERR_FAILED),
 * mesmo que o backend esteja disponível e o CORS esteja configurado
 * corretamente. Páginas que disparam muitas requisições simultâneas
 * (ex.: Catálogo) podem sofrer essa falha em mais de uma chamada, por
 * isso são feitas algumas retentativas com atraso crescente.
 */
const RETRY_DELAYS_MS = [200, 400, 800]

export async function fetchWithRetry(url: string, init?: RequestInit): Promise<Response> {
  for (const delay of RETRY_DELAYS_MS) {
    try {
      return await fetch(url, init)
    } catch (err) {
      if (!(err instanceof TypeError)) {
        throw err
      }
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
  }
  return await fetch(url, init)
}
