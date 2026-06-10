"""Envelope de erro padrão e exceções de domínio (docs/06, seção 9)."""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Exceção base para erros de domínio nomeados (ex. ITEM_SEM_PRECO).

    Subclasses definem `code`, `status_code` e `message` padrão; cada uma
    deve ter pelo menos um teste dedicado (docs/08, seção 3.1).
    """

    code: str = "ERRO_DE_DOMINIO"
    status_code: int = status.HTTP_400_BAD_REQUEST
    message: str = "Ocorreu um erro de domínio."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


def error_envelope(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


class RegistroNaoEncontradoError(DomainError):
    code = "REGISTRO_NAO_ENCONTRADO"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Registro não encontrado."


class RegistroDuplicadoError(DomainError):
    code = "REGISTRO_DUPLICADO"
    status_code = status.HTTP_409_CONFLICT
    message = "Já existe um registro com estes dados."


class ReferenciaInvalidaError(DomainError):
    code = "REFERENCIA_INVALIDA"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Referência inválida."


class RegistroEmUsoError(DomainError):
    code = "REGISTRO_EM_USO"
    status_code = status.HTTP_409_CONFLICT
    message = "Registro em uso — não pode ser removido."


class ComponenteNaoEncontradoError(DomainError):
    code = "COMPONENTE_NAO_ENCONTRADO"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Variação de componente não encontrada."


class VariacaoDuplicadaError(DomainError):
    code = "VARIACAO_DUPLICADA"
    status_code = status.HTTP_409_CONFLICT
    message = (
        "Já existe uma variação idêntica cadastrada (mesmo produto, componente, "
        "dimensão, acabamento e descritor)."
    )


class PrecoDuplicadoError(DomainError):
    code = "PRECO_DUPLICADO"
    status_code = status.HTTP_409_CONFLICT
    message = "Já existe um preço para esta variação nesta versão de tabela."


class ComponenteEmUsoError(DomainError):
    code = "COMPONENTE_EM_USO"
    status_code = status.HTTP_409_CONFLICT
    message = (
        "Esta variação está referenciada por preços de outra versão de tabela e/ou "
        "por orçamentos existentes — arquive/descontinue em vez de excluir."
    )


# ---------------------------------------------------------------------------
# Orçamentos (docs/06, seção 14.10-14.13; docs/05)
# ---------------------------------------------------------------------------


class ClienteNaoEncontradoError(DomainError):
    code = "CLIENTE_NAO_ENCONTRADO"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Cliente não encontrado."


class NenhumaTabelaVigenteError(DomainError):
    code = "NENHUMA_TABELA_VIGENTE"
    status_code = status.HTTP_409_CONFLICT
    message = "Não há nenhuma tabela de preço marcada como vigente — não é possível orçar."


class OrcamentoNaoEncontradoError(DomainError):
    code = "ORCAMENTO_NAO_ENCONTRADO"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Orçamento não encontrado."


class ItemNaoEncontradoError(DomainError):
    code = "ITEM_NAO_ENCONTRADO"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Item de orçamento não encontrado."


class VariacaoNaoEncontradaError(DomainError):
    code = "VARIACAO_NAO_ENCONTRADA"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Variação de componente não encontrada no catálogo."


class StatusInvalidoError(DomainError):
    code = "STATUS_INVALIDO"
    status_code = status.HTTP_409_CONFLICT
    message = "O orçamento não está em rascunho — não pode ser editado."


class TransicaoInvalidaError(DomainError):
    code = "TRANSICAO_INVALIDA"
    status_code = status.HTTP_409_CONFLICT
    message = "Transição de status inválida."


class ItemSemPrecoError(DomainError):
    code = "ITEM_SEM_PRECO"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = (
        "Esta variação não tem preço cadastrado na tabela vigente — lacuna conhecida do "
        "catálogo. Escolha outra variação ou contate o time responsável pelo catálogo."
    )


class ItemSemSkuError(DomainError):
    code = "ITEM_SEM_SKU"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = (
        "Este componente tem preço cadastrado, mas não tem código de fabricação associado — "
        "não pode ser incluído até que isso seja resolvido."
    )


class QuantidadeInvalidaError(DomainError):
    code = "QUANTIDADE_INVALIDA"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "A quantidade deve ser um número positivo."


class DescontoSemJustificativaError(DomainError):
    code = "DESCONTO_SEM_JUSTIFICATIVA"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Um desconto foi informado sem justificativa (discount_reason)."


class DescontoInvalidoError(DomainError):
    code = "DESCONTO_INVALIDO"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Desconto inválido."


class OrcamentoVazioError(DomainError):
    code = "ORCAMENTO_VAZIO"
    status_code = status.HTTP_409_CONFLICT
    message = "Orçamento sem nenhuma linha — não há o que totalizar/congelar."


# ---------------------------------------------------------------------------
# Importações (docs/06, seção 14.1/14.2)
# ---------------------------------------------------------------------------


class ArquivoInvalidoError(DomainError):
    code = "ARQUIVO_INVALIDO"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "O arquivo enviado não é um PDF válido."


class ArquivoMuitoGrandeError(DomainError):
    code = "ARQUIVO_MUITO_GRANDE"
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    message = "O arquivo excede o tamanho máximo permitido."


class ArquivoDuplicadoError(DomainError):
    code = "ARQUIVO_DUPLICADO"
    status_code = status.HTTP_409_CONFLICT
    message = "Já existe uma importação com o mesmo conteúdo."


class CampoObrigatorioAusenteError(DomainError):
    code = "CAMPO_OBRIGATORIO_AUSENTE"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Campo obrigatório ausente."


class ParametroInvalidoError(DomainError):
    code = "PARAMETRO_INVALIDO"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Parâmetro inválido."


class ImportacaoNaoEncontradaError(DomainError):
    code = "IMPORTACAO_NAO_ENCONTRADA"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Importação não encontrada."


class ImportacaoStatusInvalidoError(DomainError):
    code = "STATUS_INVALIDO"
    status_code = status.HTTP_409_CONFLICT
    message = (
        "Esta importação já está em processamento ou já foi concluída — "
        "reprocessar exige uma ação explícita e diferente."
    )


class EstrategiaIndisponivelError(DomainError):
    code = "ESTRATEGIA_INDISPONIVEL"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "A estratégia de extração informada não é suportada."


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, exc.details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    details = {"request_id": request_id} if request_id else {}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_envelope(
            "ERRO_INTERNO",
            "Ocorreu um erro inesperado. Informe o identificador da requisição ao suporte.",
            details,
        ),
    )
