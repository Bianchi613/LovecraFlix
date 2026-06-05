"""
Converte em lote todos os arquivos incompatíveis com o browser.
- Não deleta os originais
- Converte cada arquivo único apenas uma vez
- Atualiza o banco para apontar para o arquivo convertido
- Salva ao lado do original com sufixo _conv.mp4
"""
import json, sqlite3, subprocess, sys
from pathlib import Path

DB       = Path(r"E:\Filmes\_organizer\acervo.db")
FFMPEG   = Path(r"C:\ffmpeg\bin\bin\ffmpeg.exe")
FFPROBE  = Path(r"C:\ffmpeg\bin\bin\ffprobe.exe")

BROWSER_VIDEO = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO = {"aac", "mp3", "vorbis", "opus", "flac", "pcm_s16le", "pcm_s24le"}


def probe(path: str):
    try:
        out = subprocess.check_output(
            [str(FFPROBE), "-v", "quiet",
             "-show_entries", "stream=codec_name,codec_type",
             "-of", "json", path],
            timeout=10
        )
        streams = json.loads(out).get("streams", [])
        vc = next((s["codec_name"] for s in streams if s.get("codec_type") == "video"), "")
        ac = next((s["codec_name"] for s in streams if s.get("codec_type") == "audio"), "")
        return vc, ac
    except Exception:
        return "", ""


def precisa(vc, ac):
    return vc not in BROWSER_VIDEO or ac not in BROWSER_AUDIO


def converter(src: Path, vc: str, ac: str) -> Path:
    dest = src.with_stem(src.stem + "_conv").with_suffix(".mp4")
    if dest.exists():
        print(f"  [cache] já existe: {dest.name}")
        return dest

    video_flags = ["-c:v", "copy"] if vc in BROWSER_VIDEO else \
                  ["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-profile:v", "main", "-pix_fmt", "yuv420p"]
    audio_flags = ["-c:a", "copy"] if ac in BROWSER_AUDIO else \
                  ["-c:a", "aac", "-b:a", "192k"]

    cmd = [str(FFMPEG), "-i", str(src), *video_flags, *audio_flags,
           "-movflags", "+faststart", "-y", str(dest)]

    print(f"  Convertendo: {src.name}")
    print(f"    video: {'copy' if vc in BROWSER_VIDEO else f'{vc}->h264'}  "
          f"audio: {'copy' if ac in BROWSER_AUDIO else f'{ac}->aac'}")

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"  ERRO: {result.stderr.decode(errors='replace')[-300:]}")
        if dest.exists():
            dest.unlink()
        return None
    return dest


def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, titulo_pt, arquivo_novo FROM filmes WHERE arquivo_novo IS NOT NULL"
    ).fetchall()

    # Agrupa por arquivo único
    por_arquivo: dict[str, list] = {}
    for id_, titulo, arq in rows:
        por_arquivo.setdefault(arq, []).append((id_, titulo))

    arquivos_unicos = list(por_arquivo.keys())
    print(f"Total de arquivos únicos: {len(arquivos_unicos)}")

    precisam = []
    print("Verificando codecs...")
    for arq in arquivos_unicos:
        p = Path(arq)
        if not p.exists():
            continue
        vc, ac = probe(arq)
        if precisa(vc, ac):
            precisam.append((arq, vc, ac))

    print(f"\nArquivos que precisam converter: {len(precisam)}\n")
    if not precisam:
        print("Nada a fazer!")
        conn.close()
        return

    convertidos = 0
    erros = 0
    for i, (arq, vc, ac) in enumerate(precisam, 1):
        print(f"[{i}/{len(precisam)}] {Path(arq).parent.name}")
        dest = converter(Path(arq), vc, ac)
        if dest:
            # Atualiza todos os registros que apontam para este arquivo
            conn.execute(
                "UPDATE filmes SET arquivo_novo = ? WHERE arquivo_novo = ?",
                (str(dest), arq)
            )
            conn.commit()
            convertidos += 1
            print(f"  OK: banco atualizado -> {dest.name}\n")
        else:
            erros += 1
            print(f"  FALHOU\n")

    conn.close()
    print(f"\nConcluído: {convertidos} convertidos, {erros} erros.")


if __name__ == "__main__":
    main()
