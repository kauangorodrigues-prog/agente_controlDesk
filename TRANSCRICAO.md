# Transcrição de áudio → análise do robô ALO

O robô analisa **texto** (transcrição + metadados). Quando você só tem o **áudio**
das ligações, este é o passo que falta: áudio → transcrição → robô.

## Quando você precisa disto

| Situação | O que fazer |
|---|---|
| O discador (Olos) **já entrega transcrição** | Não precisa transcrever — mande o texto direto no `/alo/lote` ou use `/alo/call`. |
| Você só tem as **gravações** (.mp3/.wav) | Instale a transcrição local (abaixo) e use `/alo/audio` ou o script de pasta. |

## Instalação (opcional)

```bash
pip install -r requirements-transcricao.txt   # faster-whisper
```

O `faster-whisper` traz o decodificador de áudio embutido (via PyAV) — **não
depende do ffmpeg do sistema**. Sem esse pacote, o robô continua funcionando
normalmente; apenas as rotas de áudio respondem `501` avisando.

## Uso

**Uma gravação (API):**
```bash
curl -X POST "https://SEU_SERVIDOR/alo/audio" \
  -H "X-API-Key: SUA_CHAVE" -F "arquivo=@1115829654_..._20260724_080025.mp3"
```

**Uma pasta inteira (script):**
```bash
python scripts/transcrever_pasta.py /caminho/das/gravacoes --persistir --modo hibrido
```

O nome do arquivo no padrão Olos (`callid_..._telefone_..._data_hora.mp3`) é
lido automaticamente (call_id, telefone, DDD, data, hora). Gravação com áudio
mas **sem fala** vira `MUDO` (falha de entrega).

## Configuração

| Variável | Padrão | Descrição |
|---|---|---|
| `ALO_WHISPER_MODEL` | `small` | Modelo Whisper (`tiny`/`base`/`small`/`medium`). |
| `ALO_WHISPER_DEVICE` | `cpu` | `cpu` ou `cuda` (GPU). |
| `ALO_WHISPER_COMPUTE` | `int8` | Quantização (`int8` p/ CPU, `float16` p/ GPU). |
| `ALO_WHISPER_IDIOMA` | `pt` | Idioma da transcrição. |
| `ALO_WHISPER_MODEL_DIR` | — | Pasta local do modelo (rede sem HuggingFace). |

## Rede restrita (sem acesso ao HuggingFace)

O modelo é baixado do HuggingFace no primeiro uso. Se o servidor bloqueia esse
acesso, baixe o modelo numa máquina com internet e aponte a pasta:

```bash
# na máquina com internet:
python -c "from faster_whisper import download_model; download_model('small', output_dir='./whisper-small')"
# copie ./whisper-small para o servidor e configure:
export ALO_WHISPER_MODEL_DIR=/opt/whisper-small
```

O carregamento passa a ser 100% offline.

## Escala e custo

Transcrição é o passo mais pesado (CPU-bound). Para volume alto, use GPU
(`ALO_WHISPER_DEVICE=cuda`) ou uma API de STT. Já a análise em si (após o texto)
é instantânea. Para lotes grandes, prefira o script de pasta / fila a chamadas
`/alo/audio` síncronas.
