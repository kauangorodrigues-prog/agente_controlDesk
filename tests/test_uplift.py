"""Testes da lógica pura de uplift (sem banco)."""
import importlib

mod = importlib.import_module("agente_ia_control_desk")
U = mod.UpliftService


# ── Estatística tratado × controle ──────────────────────────
def test_uplift_stats_efeito_positivo():
    s = U.uplift_stats(n_trat=1000, conv_trat=200, n_ctrl=1000, conv_ctrl=150)
    assert s["taxa_tratado"] == 0.2
    assert s["taxa_controle"] == 0.15
    assert s["uplift_abs_pp"] == 5.0
    assert s["uplift_rel_pct"] == 33.33
    assert s["significante_95"] is True  # efeito forte com n grande


def test_uplift_stats_sem_efeito_nao_significante():
    s = U.uplift_stats(n_trat=500, conv_trat=100, n_ctrl=500, conv_ctrl=100)
    assert s["uplift_abs_pp"] == 0.0
    assert s["significante_95"] is False


def test_uplift_stats_controle_zero_nao_quebra():
    s = U.uplift_stats(n_trat=100, conv_trat=10, n_ctrl=0, conv_ctrl=0)
    assert s["uplift_rel_pct"] is None      # divisão por zero evitada
    assert s["p_valor"] is None
    assert s["significante_95"] is False


def test_phi_meio_no_zero():
    assert abs(U._phi(0.0) - 0.5) < 1e-9


# ── Atribuição determinística de grupo ──────────────────────
def test_definir_grupo_estavel():
    # a mesma chave cai sempre no mesmo grupo
    g1 = U.definir_grupo("exp-A", "52998224725", 0.3)
    g2 = U.definir_grupo("exp-A", "52998224725", 0.3)
    assert g1 == g2
    assert g1 in {mod.GRUPO_TRATADO, mod.GRUPO_CONTROLE}


def test_definir_grupo_extremos():
    # pct_controle=0 -> nunca controle; pct_controle=1 -> sempre controle
    assert U.definir_grupo("e", "qualquer-cpf", 0.0) == mod.GRUPO_TRATADO
    assert U.definir_grupo("e", "qualquer-cpf", 1.0) == mod.GRUPO_CONTROLE


def test_definir_grupo_distribuicao_aproximada():
    cpfs = [str(i) for i in range(4000)]
    n_ctrl = sum(1 for c in cpfs if U.definir_grupo("exp-dist", c, 0.30) == mod.GRUPO_CONTROLE)
    frac = n_ctrl / len(cpfs)
    assert 0.26 < frac < 0.34  # ~30% dentro de tolerância razoável
