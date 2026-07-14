"""Fase 6: garante que os módulos extraídos vivem no pacote `app` e que a
fachada `agente_ia_control_desk` continua reexportando os nomes públicos."""
import importlib

mod = importlib.import_module("agente_ia_control_desk")


def test_modulos_extraidos_importam_isolados():
    from app.core import resilience
    from app.utils import validators
    assert callable(resilience.retry_call)
    assert callable(validators.validar_cpf)


def test_fachada_reexporta_do_pacote():
    # Os símbolos reexportados apontam para o pacote app (não mais definidos no monólito).
    assert mod.CircuitBreaker.__module__ == "app.core.resilience"
    assert mod.retry_call.__module__ == "app.core.resilience"
    assert mod.validar_cpf.__module__ == "app.utils.validators"


def test_api_publica_preservada():
    # Nomes usados por entrypoints/celery/scripts/testes continuam disponíveis.
    for nome in ("CFG", "app", "engine", "executar_query", "executar_comando",
                 "JOBS_REGISTRO", "_safe_run", "MailingScoreService", "PropensityModel",
                 "retry_call", "CircuitBreaker", "executar_com_timeout",
                 "validar_cpf", "validar_telefone", "_str_para_time",
                 "DDDS_VALIDOS", "DDD_SCORE_MAP"):
        assert hasattr(mod, nome), f"faltou reexportar {nome}"


def test_validar_delegado_pela_classe():
    assert mod.MailingScoreService.validar_cpf("529.982.247-25") is True
    assert mod.MailingScoreService.validar_telefone("(11) 98888-7777") == "11988887777"
