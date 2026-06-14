export function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null
  return <p className="feedback-error">{error}</p>
}

export function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (page: number) => void
}) {
  if (totalPages <= 1) return null

  return (
    <div className="action-group catalog-pagination">
      <button type="button" className="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Anterior
      </button>
      <span>
        Página {page} de {totalPages}
      </span>
      <button type="button" className="secondary" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>
        Próxima →
      </button>
    </div>
  )
}
