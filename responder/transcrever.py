"""Transcreve um áudio com faster-whisper (local, CPU). Uso: python transcrever.py ARQUIVO [modelo] [idioma]
Roda no ambiente .venv-voz (separado do servidor MCP). Imprime só o texto."""
import sys

from faster_whisper import WhisperModel

arquivo = sys.argv[1]
modelo = sys.argv[2] if len(sys.argv) > 2 else "small"
idioma = sys.argv[3] if len(sys.argv) > 3 else "pt"
m = WhisperModel(modelo, device="cpu", compute_type="int8")
segmentos, _ = m.transcribe(arquivo, language=None if idioma == "auto" else idioma, vad_filter=True, beam_size=5,
                                 initial_prompt="WhatsApp. Comandos: responda ok, responda sim, confirme, cancele, mostre, rode, crie, envie.")
sys.stdout.reconfigure(encoding="utf-8")
print(" ".join(s.text.strip() for s in segmentos).strip())
