import { useNavigate, useParams } from 'react-router-dom'
import { ReviewPage } from './ReviewPage'

export function ImportReviewRoute() {
  const navigate = useNavigate(); const { id } = useParams()
  const importId = Number(id)
  if (!Number.isInteger(importId) || importId <= 0) { navigate('/importacoes', { replace: true }); return null }
  return <ReviewPage importId={importId} onBack={() => navigate('/importacoes')} />
}
