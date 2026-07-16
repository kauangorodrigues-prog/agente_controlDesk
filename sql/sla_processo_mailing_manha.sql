/* =====================================================================================
   SLA - PROCESSO_MAILING_MANHA
   -------------------------------------------------------------------------------------
   Objetivo: consolidar, por carteira, o acompanhamento diario do processo de carga
             (CRM), atualizacao do Data Mart (DM) e importacao do mailing, calculando
             os indicadores de SLA e gravando o resultado em PROCESSO_MAILING_MANHA.

   Plataforma: SQL Server (T-SQL).

   Observacoes sobre correcoes aplicadas em relacao a versao original:
     1. Nao e permitido referenciar o ALIAS de uma coluna dentro do mesmo SELECT.
        Por isso as colunas calculadas que dependem de outras (STATUS_SLA,
        STATUS_GERAL, SCORE_PROCESSO ...) sao montadas em camadas (CTEs).
     2. O INSERT em PROCESSO_MAILING_MANHA agora insere as 17 colunas de detalhe
        (mesma cardinalidade da lista de colunas de destino), e nao um resumo com 4
        colunas, que gerava erro de contagem de colunas.
     3. Os calculos de tempo entre DM e mailing comparam apenas a parte de HORA
        (CAST ... AS TIME) dos dois lados, evitando misturar datetime x time.
   ===================================================================================== */

SET NOCOUNT ON;

/* -------------------------------------------------------------------------------------
   1) #CRM - acompanhamento das cargas (duas origens)
   ------------------------------------------------------------------------------------- */
IF OBJECT_ID('TEMPDB..#CRM') IS NOT NULL
    DROP TABLE #CRM;

/* Origem 1: EasyCollector - ultima linha por CARTEIRA + TIPO_ARQUIVO */
SELECT
      CARTEIRA
    , TIPO_ARQUIVO
    , ANALITICO_INICIO
    , ANALITICO_FIM
    , CONVERT(VARCHAR(10), TEMPO) AS TEMPO
INTO #CRM
FROM
(
    SELECT
          CARTEIRA
        , TIPO_ARQUIVO
        , ANALITICO_INICIO
        , ANALITICO_FIM
        , TEMPO
        , ROW_NUMBER() OVER
          (
              PARTITION BY CARTEIRA, TIPO_ARQUIVO
              ORDER BY ANALITICO_FIM DESC
          ) AS RN
    FROM [172.20.1.65].easycollector.dbo.TB_ACOMPANHAMENTO_CARGAS
) AS EC
WHERE RN = 1;

/* Origem 2: Cobsystems (IMPORTACAO) - ultima importacao do dia por carteira */
INSERT INTO #CRM
(
      CARTEIRA
    , TIPO_ARQUIVO
    , ANALITICO_INICIO
    , ANALITICO_FIM
    , TEMPO
)
SELECT
      CARTEIRA
    , BATIMENTO                                                                     AS TIPO_ARQUIVO
    , DATA_IMP                                                                      AS ANALITICO_INICIO
    , DATA_FIM_IMP                                                                  AS ANALITICO_FIM
    , CONVERT(VARCHAR(10), DATEADD(SECOND, DATEDIFF(SECOND, DATA_IMP, DATA_FIM_IMP), 0), 108) AS TEMPO
FROM
(
    SELECT
        CASE COD_CRED
            WHEN 1 THEN 'PRAVALER'
            WHEN 2 THEN 'CREDSYSTEM'
            WHEN 3 THEN 'CREDSYSTEM UHC'
            ELSE 'NÃO MAPEADO'
        END AS CARTEIRA,
        BATIMENTO,
        DATA_IMP,
        DATA_FIM_IMP,
        ROW_NUMBER() OVER
        (
            PARTITION BY
                CASE COD_CRED
                    WHEN 1 THEN 'PRAVALER'
                    WHEN 2 THEN 'CREDSYSTEM'
                    WHEN 3 THEN 'CREDSYSTEM UHC'
                    ELSE 'NÃO MAPEADO'
                END
            ORDER BY DATA_FIM_IMP DESC
        ) AS RN
    FROM [Vcom].[ROVERI_LS_cobsystems].[dbo].[IMPORTACAO]
    WHERE CAST(DATA_FIM_IMP AS DATE) = CAST(GETDATE() AS DATE)
) X
WHERE RN = 1;


/* -------------------------------------------------------------------------------------
   2) #MAILING - horario de importacao do mailing por campanha (normalizada)
   ------------------------------------------------------------------------------------- */
IF OBJECT_ID('TEMPDB..#MAILING') IS NOT NULL
    DROP TABLE #MAILING;

SELECT
       A.CampaignId,
       CASE
            -- AFINZ
            WHEN B.Description IN ('AFINZ','AFINZ_FIXA','AFINZ_VARIAVEL','414 - WAY_AFINZ_FIXA','417 - WAY_AFINZ_VARIAVEL') THEN 'AFINZ'
            -- ATIVOS CELTA-GRUPO1
            WHEN B.Description IN ('ATIVOS CELTA-GRUPO1','ATIVOS_CELTA_G1_NOVA','164 - WAY_ATIVOS_CELTA') THEN 'ATIVOS CELTA-GRUPO1'
            -- ATIVOS ROVERI-GRUPO1
            WHEN B.Description IN ('ATIVOS ROVERI-GRUPO1','ATIVOS_ROVERI_ETAPA1','347 - WAY_ATIVOS_ROVERI') THEN 'ATIVOS ROVERI-GRUPO1'
            -- BANCO BMG
            WHEN B.Description IN ('BANCO BMG','BMG_CONCIERGE','BMG_FASE_AMIGAVEL','BMG_VARIAVEL','321 - WAY_BMG_FASE_AMIGAVEL','323 - WAY_BMG_VARIAVEL','324 - WAY_BMG_CARTAO_PURO') THEN 'BANCO BMG'
            -- BMG CONSIGNADO
            WHEN B.Description IN ('BMG_CONSIGNADO','BMG_NOVO_CONSIGNADO','352 - WAY_BMG_CONSIGNADO_PF') THEN 'BMG CONSIGNADO'
            -- BANCO MERCANTIL
            WHEN B.Description IN ('BANCO MERCANTIL','PREVENTIVO MERCANTIL') THEN 'BANCO MERCANTIL'
            -- BANCO MERCANTIL - CONCIERGE PF
            WHEN B.Description IN ('BANCO MERCANTIL - CONCIERGE','BANCO MERCANTIL BIGGER','BANCO MERCANTIL CELTA') THEN 'BANCO MERCANTIL - CONCIERGE PF'
            -- BANCO MERCANTIL - PILOTO CONCIERGE ESCRITURAÇÃO
            WHEN B.Description IN ('BANCO MERCANTIL_CONSIGNADO','BANCO MERCANTIL_CONSIGNADO_VETERANO','543 - WAY_MERCANTIL_CONSIGNADO') THEN 'BANCO MERCANTIL - PILOTO CONCIERGE ESCRITURAÇÃO'
            -- BANCO PAULISTA PF
            WHEN B.Description IN ('BANCO PAULISTA') THEN 'BANCO PAULISTA PF'
            -- BANCO PAULISTA PJ
            WHEN B.Description IN ('BANCO PAULISTA_CONCIERGE','615 - WAY_BANCO PAULISTA') THEN 'BANCO PAULISTA PJ'
            -- BANCO PINE PJ
            WHEN B.Description IN ('BANCO_PINE_CONCIERGE') THEN 'BANCO PINE PJ'
            -- BMG RECONQUISTA
            WHEN B.Description IN ('BMG RECONQUISTA') THEN 'BMG RECONQUISTA'
            -- BANCOPAN
            WHEN B.Description IN ('BANCOPAN','PAN_FIXA_0A30','PAN_FIXA_MAIOR_VALOR','PAN_FPD','PAN_VARIAVEL','PAN_VARIÁVEL_MAIOR_VALOR','359 - WAY_PAN_FIXA','539 - WAY_BANCO_PAN') THEN 'BANCOPAN'
            -- BTG ARC4
            WHEN B.Description IN ('BTG ARC4','BANCO_BTG_ARC4_G1','BANCO_BTG_ARC4_G3') THEN 'BTG ARC4'
            -- BTG ARC4 SANTANDER
            WHEN B.Description IN ('BANCO_BTG_ARC_ACO','619 - WAY_BTG_ACO') THEN 'BTG ARC4 SANTANDER'
            -- BTG ROVERI
            WHEN B.Description IN ('BANCO_BTG','527 - WAY_BTG') THEN 'BTG ROVERI'
            -- BTGINVESTFLEX
            WHEN B.Description IN ('BTGINVESTFLEX','BANCO_BTG_INVESTFLEX','533 - WAY_BTG_INVESTFLEX') THEN 'BTGINVESTFLEX'
            -- BTGSWAT
            WHEN B.Description IN ('BANCO_BTG_SWAT') THEN 'BTGSWAT'
            -- BTG SPECIAL
            WHEN B.Description IN ('BANCO_BTG_IMOBILIARIO','BTG SPECIAL ADIMPLENTE') THEN 'BTG SPECIAL'
            -- CARREFOUR
            WHEN B.Description IN ('CARREFOUR','CARREFOUR_G1','PREVENTIVO_CARREFOUR_COLCHAO','PREVENTIVO_CARREFOUR_NN','137- WAY_CARREFOUR_G1') THEN 'CARREFOUR'
            -- CREDSYSTEM
            WHEN B.Description IN ('CREDSYSTEM','PREVENTIVO_CREDSYSTEM','555 - WAY_CREDSYSTEM','CREDSYSTEM UHC') THEN 'CREDSYSTEM'
            -- ITAPEVA
            WHEN B.Description IN ('ITAPEVA','ITAPEVA VEICULOS VIP','189 - WAY_ITAPEVA_VEICULOS') THEN 'ITAPEVA'
            -- ITAPEVA CONSUMER
            WHEN B.Description IN ('ITAPEVA CONSUMER VIP','214 - WAY_ITAPEVA_CONSUMER') THEN 'ITAPEVA CONSUMER'
            -- PAGBANK
            WHEN B.Description IN ('PAGSEGURO','PAGSEGURO - KGIRO','PAGSEGURO EMPRESTIMO','PAGSEGURO LIMITE ESPECIAL','129 - WAY_PAGSEGURO_EMPRESTIMO','143 - WAY_PAGSEGURO') THEN 'PAGBANK'
            -- PEFISA
            WHEN B.Description IN ('PEFISA ROVERI','PREVENTIVO_PEFISA','103 - WAY_PEFISA') THEN 'PEFISA'
            -- PRAVALER
            WHEN B.Description IN ('PRAVALER','537 - WAY_PRAVALER') THEN 'PRAVALER'
            -- VR PF
            WHEN B.Description IN ('VR PF') THEN 'VR PF'
            -- VR PJ
            WHEN B.Description IN ('VR PJ') THEN 'VR PJ'
            -- WILL BANK II
            WHEN B.Description IN ('WILL BANK II','WILL_BANK_EMPRESTIMOS','WILLBANK','PREVENTIVO_WILLBANK_FIXA','PREVENTIVO_WILLBANK_VARIAVEL','408 - WAY_WILLBANK_FIXA') THEN 'WILL BANK II'
            -- YAMAHA
            WHEN B.Description IN ('YAMAHA','YAMAHA WO','412 - WAY_YAMAHA_WO') THEN 'YAMAHA'
            ELSE B.Description
       END AS Campanha,
       A.Description,

       /* Extrai HH:MM:SS do sufixo da Description e valida como hora */
       CONVERT(VARCHAR(8), TRY_CONVERT(TIME, STUFF(STUFF(
            CASE
                -- Ex: 1006SS -> 100600
                WHEN RIGHT(A.Description, 2) = 'SS'
                    THEN RIGHT(LEFT(A.Description, LEN(A.Description) - 2) + '00', 6)
                -- Ex: 103633 -> 103633
                WHEN RIGHT(A.Description, 6) NOT LIKE '%[^0-9]%'
                    THEN RIGHT(A.Description, 6)
                -- Ex: 1006 -> 100600
                WHEN RIGHT(A.Description, 4) NOT LIKE '%[^0-9]%'
                    THEN RIGHT(A.Description, 4) + '00'
                ELSE NULL
            END
       , 5, 0, ':'), 3, 0, ':')), 108) AS HoraConvertida,

       TRY_CONVERT(DATE, SUBSTRING(A.Description, LEN(A.Description) - 14, 8), 112) AS DataConvertida
INTO #MAILING
FROM [172.20.10.246].ExportData.dbo.MailingInformation A
INNER JOIN [172.20.10.246].ExportData.dbo.ConfigCampaign B
    ON A.CampaignId = B.CampaignId
WHERE A.PlataformID = 2
  AND B.PlataformID = 2;

/* Remove campanhas que nao devem entrar no acompanhamento */
DELETE FROM #MAILING
WHERE Campanha IN
(
    'BTGSPECIALTEMP','VRPJNEW','VRPFNEW','BMG CONSIGNADO','BANCOVRPJ','BANCOVRPF',
    'BANCO MERCANTIL RETENÇÃO','BANCO MERCANTIL CHURN','BTG VR INAD','BTG VR PF','BTG VR PJ'
);


/* -------------------------------------------------------------------------------------
   3) #BASE_FINAL - consolidacao + indicadores de SLA
      As colunas calculadas sao montadas em CAMADAS (CTEs) porque no SQL Server
      um alias criado no SELECT nao pode ser reutilizado no mesmo SELECT.
   ------------------------------------------------------------------------------------- */
IF OBJECT_ID('TEMPDB..#BASE_FINAL') IS NOT NULL
    DROP TABLE #BASE_FINAL;

;WITH CRM_JOIN AS
(
    /* Camada 0: junta CRM + ultima atualizacao do DM + hora do mailing */
    SELECT
          C.CARTEIRA
        , C.TIPO_ARQUIVO
        , C.TEMPO
        , C.ANALITICO_INICIO
        , C.ANALITICO_FIM
        , D.DT_HR_ATUALIZACAO
        , M.HoraConvertida AS HORA_MAILING
    FROM #CRM C
    LEFT JOIN
    (
        SELECT
              CARTEIRA
            , MAX(DT_HR_ATUALIZACAO) AS DT_HR_ATUALIZACAO
        FROM [DB_REPORT].DM.TB_CARTEIRA
        GROUP BY CARTEIRA
    ) D
        ON C.CARTEIRA = D.CARTEIRA
    OUTER APPLY
    (
        SELECT TOP 1
               CONVERT(VARCHAR(8), X.HoraConvertida, 108) AS HoraConvertida
        FROM #MAILING X
        WHERE X.Campanha = C.CARTEIRA
          AND X.HoraConvertida > CONVERT(VARCHAR(8), D.DT_HR_ATUALIZACAO, 108)
        ORDER BY X.HoraConvertida ASC
    ) M
    WHERE C.CARTEIRA NOT IN
    (
        'BTGSPECIALTEMP','VRPJNEW','VRPFNEW','BMG CONSIGNADO','BANCOVRPJ','BANCOVRPF',
        'BANCO MERCANTIL RETENÇÃO','BANCO MERCANTIL CHURN','BTG VR INAD','BTG VR PF','BTG VR PJ'
    )
),
CALC1 AS
(
    /* Camada 1: colunas de exibicao + status independentes */
    SELECT
          ISNULL(CONVERT(VARCHAR(10), ANALITICO_INICIO, 103), '0')                        AS DATA
        , ISNULL(CARTEIRA, '0')                                                           AS CARTEIRA
        , ISNULL(CONVERT(VARCHAR(8), ANALITICO_INICIO, 108), '00:00:00')                  AS HORARIO_RECEBIMENTO
        , ISNULL(CONVERT(VARCHAR(8), ANALITICO_INICIO, 108), '00:00:00')                  AS HORARIO_INICIO_IMPORTACAO
        , ISNULL(CONVERT(VARCHAR(8), ANALITICO_FIM, 108), '00:00:00')                     AS HORARIO_FIM_IMPORTACAO
        , ISNULL(TEMPO, '00:00')                                                          AS TEMPO_IMPORTACAO
        , ISNULL(NULLIF(TIPO_ARQUIVO, '0'), 'CARGA')                                      AS STATUS_CARGA
        , ISNULL(CONVERT(VARCHAR(8), ANALITICO_FIM, 108), '00:00:00')                     AS HORARIO_INICIO_DM
        , ISNULL(CONVERT(VARCHAR(8), DT_HR_ATUALIZACAO, 108), '00:00:00')                 AS HORARIO_FIM_DM
        , ISNULL(CONVERT(VARCHAR(8),
              DATEADD(SECOND,
                  ABS(DATEDIFF(SECOND,
                      CAST(ISNULL(CONVERT(VARCHAR(8), ANALITICO_FIM, 108), '00:00:00') AS TIME),
                      CAST(ISNULL(CONVERT(VARCHAR(8), DT_HR_ATUALIZACAO, 108), '00:00:00') AS TIME))),
                  0), 108), '00:00:00')                                                   AS TEMPO_ATUALIZACAO_DM
        , CASE WHEN DT_HR_ATUALIZACAO IS NULL THEN 'NÃO ATUALIZADO' ELSE 'ATUALIZADO' END AS STATUS_DM
        , ISNULL(HORA_MAILING, '00:00:00')                                                AS HORA_MAILING_IMPORTADO
        , CASE WHEN HORA_MAILING IS NULL THEN 'NÃO IMPORTADO' ELSE 'IMPORTADO' END        AS STATUS_IMPORTACAO_MAILING
        -- SLA da importacao (tempo de carga do CRM)
        , CASE
              WHEN TRY_CONVERT(TIME, ISNULL(TEMPO, '00:00')) <= '00:15:00' THEN 'DENTRO SLA'
              WHEN TRY_CONVERT(TIME, ISNULL(TEMPO, '00:00')) <= '00:30:00' THEN 'ATENÇÃO'
              ELSE 'FORA SLA'
          END                                                                             AS SLA_IMPORTACAO
        -- Tempo (min) entre atualizacao do DM e importacao do mailing (somente parte de HORA)
        , DATEDIFF(MINUTE,
              CAST(DT_HR_ATUALIZACAO AS TIME),
              CAST(HORA_MAILING AS TIME))                                                 AS MINUTOS_DM_MAILING
        -- SLA do mailing
        , CASE
              WHEN DATEDIFF(MINUTE, CAST(DT_HR_ATUALIZACAO AS TIME), CAST(HORA_MAILING AS TIME)) <= 15 THEN 'DENTRO SLA'
              WHEN DATEDIFF(MINUTE, CAST(DT_HR_ATUALIZACAO AS TIME), CAST(HORA_MAILING AS TIME)) <= 30 THEN 'ATENÇÃO'
              ELSE 'FORA SLA'
          END                                                                             AS SLA_MAILING
        -- Frequencia esperada de atualizacao por carteira
        , CASE
              WHEN CARTEIRA IN ('BANCOPAN','BTG ARC4','BTG ARC4 SANTANDER','BTG ROVERI','BTGINVESTFLEX','BTG SPECIAL','BTGSWAT','CARREFOUR','CREDSYSTEM','CREDSYSTEM UHC','PEFISA','PRAVALER','WILL BANK II','YAMAHA','VR PF','VR PJ') THEN 'DIARIAMENTE'
              WHEN CARTEIRA IN ('ITAPEVA','ITAPEVA CONSUMER','BANCO MERCANTIL CELTA','BANCO MERCANTIL BIGGER') THEN 'DIA ANTERIOR'
              WHEN CARTEIRA IN ('AFINZ','ATIVOS CELTA-GRUPO1','ATIVOS ROVERI-GRUPO1','BANCO BMG','PAGBANK') THEN 'SEGUNDA A SEXTA'
              WHEN CARTEIRA IN ('BANCO MERCANTIL') THEN 'TERÇA A SEXTA'
              WHEN CARTEIRA IN ('BMG RECONQUISTA','BANCO SAFRA','BANCO MERCANTIL - CONCIERGE PF','BANCO MERCANTIL - PILOTO CONCIERGE ESCRITURAÇÃO') THEN 'MENSAL'
              WHEN CARTEIRA LIKE 'BANCO PAULISTA%' THEN 'ESPORÁDICO'
              ELSE 'NÃO MAPEADO'
          END                                                                             AS FREQUENCIA_ATUALIZACAO
        -- Data esperada de atualizacao por carteira
        , CASE
              WHEN CARTEIRA IN ('BANCOPAN','BTG ARC4','BTG ARC4 SANTANDER','BTG ROVERI','BTGINVESTFLEX','BTG SPECIAL','BTGSWAT','CARREFOUR','CREDSYSTEM','CREDSYSTEM UHC','PEFISA','PRAVALER','WILL BANK II','YAMAHA','VR PF','VR PJ') THEN CAST(GETDATE() AS DATE)
              WHEN CARTEIRA IN ('ITAPEVA','ITAPEVA CONSUMER','BANCO MERCANTIL CELTA','BANCO MERCANTIL BIGGER') THEN DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
              WHEN CARTEIRA IN ('AFINZ','ATIVOS CELTA-GRUPO1','ATIVOS ROVERI-GRUPO1','BANCO BMG','PAGBANK','BANCO MERCANTIL') THEN CAST(GETDATE() AS DATE)
              WHEN CARTEIRA IN ('BMG RECONQUISTA','BANCO SAFRA','BANCO MERCANTIL - CONCIERGE PF','BANCO MERCANTIL - PILOTO CONCIERGE ESCRITURAÇÃO') THEN DATEADD(DAY, -30, CAST(GETDATE() AS DATE))
              ELSE NULL
          END                                                                             AS DATA_ESPERADA
        , DATEDIFF(DAY, CAST(DT_HR_ATUALIZACAO AS DATE), CAST(GETDATE() AS DATE))          AS DIAS_ATRASO
        -- colunas auxiliares carregadas para as camadas seguintes
        , DT_HR_ATUALIZACAO
        , ANALITICO_INICIO
    FROM CRM_JOIN
),
CALC2 AS
(
    /* Camada 2: STATUS_SLA depende de FREQUENCIA_ATUALIZACAO (camada anterior) */
    SELECT
          C1.*
        , CASE
              WHEN DT_HR_ATUALIZACAO IS NULL
                  THEN 'SEM ATUALIZAÇÃO'
              WHEN FREQUENCIA_ATUALIZACAO = 'DIARIAMENTE'
                   AND CAST(DT_HR_ATUALIZACAO AS DATE) = CAST(GETDATE() AS DATE)
                  THEN 'NO PRAZO'
              WHEN FREQUENCIA_ATUALIZACAO = 'DIA ANTERIOR'
                   AND CAST(DT_HR_ATUALIZACAO AS DATE) >= DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
                  THEN 'NO PRAZO'
              WHEN FREQUENCIA_ATUALIZACAO = 'SEGUNDA A SEXTA'
                   AND DATENAME(WEEKDAY, GETDATE()) IN ('Monday','Tuesday','Wednesday','Thursday','Friday')
                  THEN 'NO PRAZO'
              ELSE 'ATRASADO'
          END AS STATUS_SLA
    FROM CALC1 C1
)
/* Camada 3: STATUS_GERAL / SCORE_PROCESSO dependem dos status das camadas anteriores */
SELECT
      DATA
    , CARTEIRA
    , HORARIO_RECEBIMENTO
    , HORARIO_INICIO_IMPORTACAO
    , HORARIO_FIM_IMPORTACAO
    , TEMPO_IMPORTACAO
    , STATUS_CARGA
    , HORARIO_INICIO_DM
    , HORARIO_FIM_DM
    , TEMPO_ATUALIZACAO_DM
    , STATUS_DM
    , HORA_MAILING_IMPORTADO
    , STATUS_IMPORTACAO_MAILING
    , SLA_IMPORTACAO
    , MINUTOS_DM_MAILING
    , SLA_MAILING
    , FREQUENCIA_ATUALIZACAO
    , DATA_ESPERADA
    , DIAS_ATRASO
    , STATUS_SLA
    , CASE
          WHEN STATUS_CARGA = 'CARGA'
           AND STATUS_DM = 'ATUALIZADO'
           AND STATUS_IMPORTACAO_MAILING = 'IMPORTADO'
           AND SLA_IMPORTACAO = 'DENTRO SLA'
           AND SLA_MAILING = 'DENTRO SLA'
           AND STATUS_SLA = 'NO PRAZO'
              THEN 'PROCESSO OK'
          ELSE 'PROCESSO COM FALHA'
      END AS STATUS_GERAL
    , (
          CASE WHEN STATUS_CARGA = 'CARGA' THEN 20 ELSE 0 END
        + CASE WHEN STATUS_DM = 'ATUALIZADO' THEN 20 ELSE 0 END
        + CASE WHEN STATUS_IMPORTACAO_MAILING = 'IMPORTADO' THEN 20 ELSE 0 END
        + CASE WHEN SLA_IMPORTACAO = 'DENTRO SLA' THEN 20 ELSE 0 END
        + CASE WHEN SLA_MAILING = 'DENTRO SLA' THEN 20 ELSE 0 END
      ) AS SCORE_PROCESSO
INTO #BASE_FINAL
FROM CALC2;


/* -------------------------------------------------------------------------------------
   4) Grava o detalhe por carteira em PROCESSO_MAILING_MANHA
   ------------------------------------------------------------------------------------- */
TRUNCATE TABLE PROCESSO_MAILING_MANHA;

INSERT INTO PROCESSO_MAILING_MANHA
(
      DATA
    , CARTEIRA
    , HORARIO_RECEBIMENTO
    , HORARIO_INICIO_IMPORTACAO
    , HORARIO_FIM_IMPORTACAO
    , TEMPO_IMPORTACAO
    , STATUS_CARGA
    , HORARIO_INICIO_DM
    , HORARIO_FIM_DM
    , TEMPO_ATUALIZACAO_DM
    , STATUS_DM
    , HORA_MAILING_IMPORTADO
    , STATUS_IMPORTACAO_MAILING
    , FREQUENCIA_ATUALIZACAO
    , DATA_ESPERADA
    , DIAS_ATRASO
    , STATUS_SLA
)
SELECT
      DATA
    , CARTEIRA
    , HORARIO_RECEBIMENTO
    , HORARIO_INICIO_IMPORTACAO
    , HORARIO_FIM_IMPORTACAO
    , TEMPO_IMPORTACAO
    , STATUS_CARGA
    , HORARIO_INICIO_DM
    , HORARIO_FIM_DM
    , TEMPO_ATUALIZACAO_DM
    , STATUS_DM
    , HORA_MAILING_IMPORTADO
    , STATUS_IMPORTACAO_MAILING
    , FREQUENCIA_ATUALIZACAO
    , DATA_ESPERADA
    , DIAS_ATRASO
    , STATUS_SLA
FROM #BASE_FINAL;


/* -------------------------------------------------------------------------------------
   5) (Opcional) Resumo consolidado do SLA geral do dia
   ------------------------------------------------------------------------------------- */
SELECT
      COUNT(*)                                                                      AS TOTAL_CARTEIRAS
    , SUM(CASE WHEN STATUS_GERAL = 'PROCESSO OK' THEN 1 ELSE 0 END)                 AS PROCESSOS_OK
    , SUM(CASE WHEN STATUS_GERAL = 'PROCESSO COM FALHA' THEN 1 ELSE 0 END)          AS PROCESSOS_COM_FALHA
    , CAST(100.0 * SUM(CASE WHEN STATUS_GERAL = 'PROCESSO OK' THEN 1 ELSE 0 END)
           / NULLIF(COUNT(*), 0) AS DECIMAL(5,2))                                   AS SLA_GERAL
FROM #BASE_FINAL;
