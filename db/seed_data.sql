-- ============================================================
-- Seed de exemplo — Agente IA Control Desk
-- ============================================================
-- Dados ilustrativos, seguros para editar/remover.
-- Aplicar após o schema:  psql "$DATABASE_URL" -f db/seed_data.sql
--
-- Para criar o usuário administrador da API use o script
-- (senha com hash bcrypt não pode ser gerada em SQL puro):
--     python scripts/create_user.py --username admin --role admin
-- ============================================================

-- Configuração de campanha de exemplo (ajuste os IDs para os
-- IDs reais das suas campanhas no discador).
INSERT INTO campaign_config
    (campanha_id, campanha_nome, ativo, hora_inicio, hora_fim,
     hora_fim_sabado, permitir_domingo, pacing_min, pacing_max, pausar_feriados)
VALUES
    ('EXEMPLO-001', 'Campanha Exemplo', TRUE, '08:00', '21:00',
     '16:00', FALSE, 1.0, 8.0, TRUE)
ON CONFLICT (campanha_id) DO NOTHING;

-- Feriado de exemplo (empresa).
INSERT INTO feriados
    (data, nome, tipo, pausar_mailing, pausar_discagem, criado_por)
VALUES
    ('2026-12-25', 'Natal', 'NACIONAL', TRUE, TRUE, 'SEED')
ON CONFLICT (data, tipo, COALESCE(uf, ''), COALESCE(municipio, '')) DO NOTHING;
